"""轻传 LiteDrop — HTTP 传输服务(纯标准库,IPv4/IPv6 双栈)。

供 main.py 调用,也可直接 `python server.py` 独立运行做接口测试。
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import socket
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_TEXT_LEN = 100_000          # 单条文本上限
MAX_CHUNK_SIZE = 32 * 1024 * 1024   # 单分片上限 32MB
HISTORY_LIMIT = 50              # PC→手机 文本保留条数
STALE_UPLOAD_HOURS = 24
UPLOAD_ID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")

BAD_TOKEN_PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>口令无效 · 轻传 LiteDrop</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:#0a0f1c;color:#e8eef9;text-align:center;
  font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.box{padding:32px 26px;border-radius:18px;background:#121a2b;
  border:1px solid rgba(255,255,255,.08);max-width:320px}
h1{font-size:20px;margin:0 0 12px}
p{font-size:14px;line-height:1.7;color:#8ca0c0;margin:6px 0}
</style></head>
<body><div class="box"><h1>&#128274; 口令无效</h1>
<p>链接中的访问口令不正确。</p>
<p>请在电脑端打开「轻传 LiteDrop」,用手机重新扫描当前二维码。</p>
</div></body></html>"""


def sanitize_filename(name: str) -> str:
    """只保留文件名本身,剔除 Windows 非法字符。"""
    name = os.path.basename(name.replace("\\", "/")).strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ")
    if len(name) > 150:
        stem, ext = os.path.splitext(name)
        name = stem[: 150 - len(ext)] + ext
    return name or "未命名文件"


def unique_path(directory: str, name: str) -> str:
    """目录内重名自动追加序号:name.txt -> name (2).txt"""
    target = os.path.join(directory, name)
    if not os.path.exists(target):
        return target
    stem, ext = os.path.splitext(name)
    n = 2
    while True:
        candidate = os.path.join(directory, f"{stem} ({n}){ext}")
        if not os.path.exists(candidate):
            return candidate
        n += 1


class TransferState:
    """GUI 线程与 HTTP 线程之间的共享状态,全部经 lock 保护。"""

    def __init__(self, receive_dir: str, token: str | None = None):
        self.lock = threading.RLock()
        self.receive_dir = receive_dir
        self.token = token or secrets.token_urlsafe(6)   # 8 个 URL 安全字符
        self.require_token = True
        self.bad_tokens = 0
        self.inbox: list[dict] = []    # 手机→PC 文本,由 GUI 消费
        self.outbox: list[dict] = []   # PC→手机 文本,带自增 id 供轮询
        self.files: dict[int, dict] = {}  # 共享文件白名单: id -> entry
        self.next_id = 1

    # ---------- GUI 调用 ----------
    def push_text(self, text: str) -> dict:
        with self.lock:
            item = {"id": self.next_id, "text": text,
                    "time": time.strftime("%H:%M:%S")}
            self.next_id += 1
            self.outbox.append(item)
            del self.outbox[:-HISTORY_LIMIT]
            return item

    def add_file(self, path: str) -> dict:
        with self.lock:
            fid = self.next_id
            self.next_id += 1
            entry = {"id": fid, "name": os.path.basename(path),
                     "size": os.path.getsize(path), "path": path}
            self.files[fid] = entry
            return entry

    def remove_file(self, fid: int) -> None:
        with self.lock:
            self.files.pop(fid, None)

    # ---------- HTTP 线程调用 ----------
    def add_inbox_text(self, text: str) -> dict:
        with self.lock:
            item = {"id": self.next_id, "text": text,
                    "time": time.strftime("%H:%M:%S")}
            self.next_id += 1
            self.inbox.append(item)
            return item

    def updates_since(self, cursor: int) -> tuple[list[dict], list[dict], int]:
        with self.lock:
            texts = [t for t in self.outbox if t["id"] > cursor]
            files = [{"id": f["id"], "name": f["name"], "size": f["size"]}
                     for f in self.files.values()]
            newest = max((t["id"] for t in self.outbox), default=cursor)
            return texts, files, max(newest, cursor)

    def cleanup_stale_uploads(self) -> None:
        tmp_root = os.path.join(self.receive_dir, ".uploads")
        if not os.path.isdir(tmp_root):
            return
        deadline = time.time() - STALE_UPLOAD_HOURS * 3600
        for name in os.listdir(tmp_root):
            path = os.path.join(tmp_root, name)
            try:
                if os.path.getmtime(path) < deadline:
                    shutil.rmtree(path, ignore_errors=True)
            except OSError:
                pass


def make_handler_class(state: TransferState, events, page_html: str) -> type:
    """生成绑定 state/events/页面的 Handler 类。events 方法均允许缺失。"""

    class LiteDropHandler(BaseHTTPRequestHandler):
        server_version = "LiteDrop/1.0"
        protocol_version = "HTTP/1.1"

        # ---------- 基础 ----------
        def log_message(self, fmt, *args):  # 静默默认日志
            pass

        def _notify(self, method: str, *args) -> None:
            fn = getattr(events, method, None)
            if fn:
                try:
                    fn(*args)
                except Exception:
                    pass

        def _send_bytes(self, data: bytes, code: int = 200,
                        ctype: str = "application/json; charset=utf-8",
                        extra: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-LiteDrop", "1")   # 供隧道自检识别回环可达
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _send_json(self, obj, code: int = 200) -> None:
            self._send_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                             code=code)

        def _fail(self, code: int, msg: str) -> None:
            self._send_json({"ok": False, "error": msg}, code=code)

        def _query(self) -> dict[str, list[str]]:
            return urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query)

        # ---------- 鉴权 ----------
        def _authed(self) -> bool:
            if not state.require_token:
                return True
            q = self._query().get("k", [""])[0]
            h = self.headers.get("X-Auth", "")
            if (q and secrets.compare_digest(q, state.token)) or \
               (h and secrets.compare_digest(h, state.token)):
                return True
            with state.lock:
                state.bad_tokens += 1
                n = state.bad_tokens
            time.sleep(min(1.0, 0.05 * n))  # 简单限速,防止爆破
            return False

        # ---------- GET ----------
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/":
                if not self._authed():
                    return self._send_bytes(
                        BAD_TOKEN_PAGE.encode("utf-8"), code=403,
                        ctype="text/html; charset=utf-8")
                self._notify("on_page_opened")
                return self._send_bytes(
                    page_html.encode("utf-8"), ctype="text/html; charset=utf-8")
            if path == "/favicon.ico":
                return self._send_bytes(b"", ctype="image/x-icon")
            if path == "/api/updates":
                if not self._authed():
                    return self._fail(403, "访问口令无效")
                try:
                    cursor = int(self._query().get("cursor", ["0"])[0])
                except ValueError:
                    cursor = 0
                texts, files, nxt = state.updates_since(cursor)
                return self._send_json({
                    "ok": True, "pc": socket.gethostname(),
                    "texts": texts, "files": files, "cursor": nxt})
            if path == "/api/download":
                if not self._authed():
                    return self._fail(403, "访问口令无效")
                return self._serve_download()
            return self._fail(404, "接口不存在")

        def _serve_download(self):
            try:
                fid = int(self._query().get("id", ["0"])[0])
            except ValueError:
                return self._fail(404, "文件不存在")
            entry = state.files.get(fid)
            if not entry or not os.path.isfile(entry["path"]):
                return self._fail(404, "文件不存在或已被移除")
            size = os.path.getsize(entry["path"])
            quoted = urllib.parse.quote(entry["name"])
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("X-LiteDrop", "1")
            self.send_header("Content-Disposition",
                             f"attachment; filename=\"download\"; "
                             f"filename*=UTF-8''{quoted}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                with open(entry["path"], "rb") as f:
                    while True:
                        block = f.read(1024 * 1024)
                        if not block:
                            break
                        self.wfile.write(block)
            except (BrokenPipeError, ConnectionResetError):
                pass  # 手机端取消下载属正常情况

        # ---------- POST ----------
        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/text":
                if not self._authed():
                    return self._fail(403, "访问口令无效")
                return self._handle_text()
            if path == "/api/upload/chunk":
                if not self._authed():
                    return self._fail(403, "访问口令无效")
                return self._handle_chunk()
            if path == "/api/upload/finish":
                if not self._authed():
                    return self._fail(403, "访问口令无效")
                return self._handle_finish()
            return self._fail(404, "接口不存在")

        def _read_json(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            if length <= 0 or length > MAX_TEXT_LEN:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return {}

        def _handle_text(self):
            body = self._read_json()
            text = str(body.get("text", "")).strip()
            if not text:
                return self._fail(400, "文本为空")
            if len(text) > MAX_TEXT_LEN:
                return self._fail(400, "文本过长")
            state.add_inbox_text(text)
            self._notify("on_text_received", {"text": text})
            self._send_json({"ok": True})

        def _upload_dir(self, upload_id: str) -> str:
            return os.path.join(state.receive_dir, ".uploads", upload_id)

        def _handle_chunk(self):
            q = self._query()
            upload_id = q.get("uploadId", [""])[0]
            if not UPLOAD_ID_RE.match(upload_id):
                return self._fail(400, "非法上传标识")
            try:
                index = int(q.get("index", ["-1"])[0])
                total = int(q.get("total", ["0"])[0])
            except ValueError:
                return self._fail(400, "分片参数无效")
            if total < 1 or not 0 <= index < total:
                return self._fail(400, "分片参数无效")
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            if length <= 0 or length > MAX_CHUNK_SIZE:
                return self._fail(413, "分片过大")
            if index == 0:
                self._notify("on_receiving",
                             sanitize_filename(q.get("name", [""])[0]))

            udir = self._upload_dir(upload_id)
            os.makedirs(udir, exist_ok=True)
            remaining = length
            with open(os.path.join(udir, f"{index:06d}.part"), "wb") as f:
                while remaining > 0:
                    block = self.rfile.read(min(1024 * 1024, remaining))
                    if not block:
                        return self._fail(400, "传输中断")
                    f.write(block)
                    remaining -= len(block)
            return self._send_json({"ok": True, "received": index + 1,
                                    "total": total})

        def _handle_finish(self):
            body = self._read_json()
            upload_id = str(body.get("uploadId", ""))
            if not UPLOAD_ID_RE.match(upload_id):
                return self._fail(400, "非法上传标识")
            name = sanitize_filename(str(body.get("name", "")))
            udir = self._upload_dir(upload_id)
            if not os.path.isdir(udir):
                return self._fail(410, "上传会话不存在或已完成")
            parts = sorted(p for p in os.listdir(udir) if p.endswith(".part"))
            if not parts:
                shutil.rmtree(udir, ignore_errors=True)
                return self._fail(400, "没有收到任何分片")
            target = unique_path(state.receive_dir, name)
            try:
                with open(target, "wb") as out:
                    for part in parts:
                        with open(os.path.join(udir, part), "rb") as f:
                            shutil.copyfileobj(f, out, 1024 * 1024)
            finally:
                shutil.rmtree(udir, ignore_errors=True)
            entry = {"name": os.path.basename(target),
                     "size": os.path.getsize(target),
                     "path": target, "time": time.strftime("%H:%M:%S")}
            self._notify("on_file_received", entry)
            self._send_json({"ok": True, "name": entry["name"],
                             "size": entry["size"]})

    return LiteDropHandler


class DualStackServer(ThreadingHTTPServer):
    """IPv6 通时以 v6 双栈监听(同时接受 v4 映射连接),否则回退 v4。"""
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # 探活/客户端主动断开属正常情况,静默处理
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError,
                            TimeoutError, socket.timeout)):
            return
        super().handle_error(request, client_address)

    def __init__(self, port: int, handler: type):
        try:
            self.address_family = socket.AF_INET6
            super().__init__(("::", port), handler)
        except OSError:
            self.address_family = socket.AF_INET
            super().__init__("0.0.0.0", handler)  # type: ignore[assignment]

    def server_bind(self):
        if self.address_family == socket.AF_INET6:
            try:
                self.socket.setsockopt(socket.IPPROTO_IPV6,
                                       socket.IPV6_V6ONLY, 0)
            except OSError:
                pass
        super().server_bind()


class LiteDropServer:
    """对外封装:启动/停止 + 事件回调对象由调用方提供。"""

    def __init__(self, port: int, state: TransferState, events,
                 page_html: str):
        self.port = port
        self.state = state
        self.events = events
        handler = make_handler_class(state, events, page_html)
        self.httpd = DualStackServer(port, handler)
        self.port = self.httpd.server_address[1]  # 端口为 0 时取实际值
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.state.cleanup_stale_uploads()
        self._thread = threading.Thread(
            target=self.httpd.serve_forever,
            kwargs={"poll_interval": 0.2}, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None


if __name__ == "__main__":  # 独立运行,便于接口测试
    import sys

    recv = os.path.join(os.getcwd(), "received")
    os.makedirs(recv, exist_ok=True)
    st = TransferState(recv)

    class _Ev:
        def on_text_received(self, item):
            print(f"[文本] {item['text'][:50]}")

        def on_file_received(self, entry):
            print(f"[文件] {entry['name']} ({entry['size']} 字节)")

        def on_log(self, msg):
            print(f"[日志] {msg}")

        on_receiving = on_page_opened = on_log

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    from mobile_page import PAGE_HTML

    srv = LiteDropServer(port, st, _Ev(), PAGE_HTML)
    srv.start()
    host = socket.gethostname()
    print(f"LiteDrop 服务已启动 http://127.0.0.1:{srv.port}/?k={st.token}")
    print(f"主机名: {host}  接收目录: {recv}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.stop()
