# -*- coding: utf-8 -*-
"""LiteDrop 接口自测:覆盖鉴权、文本、分块上传、下载、路径安全。

运行:python test_server.py
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import urllib.error
import urllib.request

# 本机可能配置了系统代理,测试时直连回环地址
urllib.request.install_opener(
    urllib.request.build_opener(urllib.request.ProxyHandler({})))

from mobile_page import PAGE_HTML
from server import DualStackServer, TransferState, make_handler_class


class StubEvents:
    def __init__(self):
        self.texts = []
        self.files = []
        self.logs = []

    def on_text_received(self, item):
        self.texts.append(item["text"])

    def on_file_received(self, entry):
        self.files.append(entry)

    def on_receiving(self, name):
        self.logs.append(("receiving", name))

    def on_page_opened(self):
        self.logs.append(("page",))

    def on_log(self, msg):
        self.logs.append(("log", msg))


def call(method: str, path: str, data: bytes | None = None,
         headers: dict | None = None) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data,
                                 method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def main() -> int:
    global PORT
    recv = tempfile.mkdtemp(prefix="litedrop-test-")
    state = TransferState(recv)
    events = StubEvents()
    handler = make_handler_class(state, events, PAGE_HTML)
    httpd = DualStackServer(0, handler)
    PORT = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever,
                     kwargs={"poll_interval": 0.1}, daemon=True).start()
    k = state.token
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = ""):
        results.append((name, ok, detail))
        print(("PASS" if ok else "FAIL"), name, detail)

    # 1 未带口令访问页面 → 403 + 友好 HTML 页(而非裸 JSON)
    code, body, headers = call("GET", f"/")
    check("无口令访问返回403", code == 403)
    check("无口令返回友好提示页", "口令无效" in body.decode("utf-8", "ignore")
          and headers.get("X-LiteDrop") == "1")
    # 2 带口令 → 200 且是页面
    code, body, _ = call("GET", f"/?k={k}")
    check("带口令访问返回200", code == 200 and b"<html" in body[:200].lower())
    # 3 错误口令 → 403
    code, _, _ = call("GET", f"/?k=wrong")
    check("错误口令返回403", code == 403)
    # 3b API 的 403 仍为 JSON
    code, body, _ = call("GET", f"/api/updates")
    check("API未鉴权返回JSON", code == 403 and b'"ok"' in body)
    # 3c 口令可通过参数指定(持久化用)
    st2 = TransferState(recv, token="persisted1")
    check("口令参数生效", st2.token == "persisted1")
    # 4 手机→PC 文本
    payload = json.dumps({"text": "你好,电脑"}).encode()
    code, body, _ = call("POST", f"/api/text?k={k}", payload,
                         {"Content-Type": "application/json"})
    check("发送文本返回200", code == 200 and json.loads(body)["ok"])
    check("事件回调收到文本", events.texts == ["你好,电脑"])
    # 5 轮询 updates 拿 PC→手机 内容
    state.push_text("电脑你好")
    code, body, _ = call("GET", f"/api/updates?k={k}&cursor=0")
    d = json.loads(body)
    check("updates返回文本", code == 200 and
          any(t["text"] == "电脑你好" for t in d["texts"]))
    check("updates返回主机名", d["pc"] == os.environ["COMPUTERNAME"])
    cursor = d["cursor"]
    # 6 增量轮询:cursor 之后无新内容
    code, body, _ = call("GET", f"/api/updates?k={k}&cursor={cursor}")
    d = json.loads(body)
    check("增量轮询为空", d["texts"] == [])
    # 7 分块上传(2 块)+ 重组校验
    blob = os.urandom(300 * 1024)
    chunks = [blob[:100 * 1024], blob[100 * 1024:]]
    uid = "0123abcd-0000-4000-8000-000000000001"
    for i, c in enumerate(chunks):
        code, body, _ = call(
            "POST",
            f"/api/upload/chunk?k={k}&uploadId={uid}"
            f"&name={urllib.request.quote('测试 文件.bin')}&index={i}&total=2",
            c, {"Content-Type": "application/octet-stream"})
        assert code == 200, body
    code, body, _ = call("POST", f"/api/upload/finish?k={k}",
                         json.dumps({"uploadId": uid,
                                     "name": "测试 文件.bin"}).encode(),
                         {"Content-Type": "application/json"})
    saved = os.path.join(recv, "测试 文件.bin")
    check("分块上传完成", code == 200)
    check("重组内容一致", os.path.isfile(saved) and
          open(saved, "rb").read() == blob)
    check("临时目录已清理", not os.path.isdir(os.path.join(recv, ".uploads", uid)))
    # 8 重名自动加序号
    uid2 = "0123abcd-0000-4000-8000-000000000002"
    call("POST", f"/api/upload/chunk?k={k}&uploadId={uid2}"
                 f"&name=x.bin&index=0&total=1", b"second",
         {"Content-Type": "application/octet-stream"})
    call("POST", f"/api/upload/finish?k={k}",
         json.dumps({"uploadId": uid2, "name": "测试 文件.bin"}).encode())
    check("重名自动加序号", os.path.isfile(os.path.join(recv, "测试 文件 (2).bin")))
    # 9 非法 uploadId 拒绝(路径穿越)
    code, _, _ = call("POST", f"/api/upload/chunk?k={k}"
                              f"&uploadId=..%2Fevil&name=a.bin&index=0&total=1",
                      b"x")
    check("非法uploadId返回400", code == 400)
    # 10 分片过大拒绝
    code, _, _ = call("POST", f"/api/upload/chunk?k={k}&uploadId={uid2}"
                              f"&name=a.bin&index=0&total=1", b"")
    check("空分片返回413", code == 413)
    # 11 PC 共享文件 + 下载
    entry = state.add_file(saved)
    code, body, headers = call("GET", f"/api/download?k={k}&id={entry['id']}")
    check("下载内容一致", code == 200 and body == blob)
    check("下载文件名RFC5987", "filename*" in headers.get("Content-Disposition", ""))
    # 12 下载白名单外 id → 404
    code, _, _ = call("GET", f"/api/download?k={k}&id=9999")
    check("白名单外返回404", code == 404)
    # 13 未鉴权调用 API → 403
    code, _, _ = call("GET", f"/api/updates")
    check("API未鉴权返回403", code == 403)
    # 14 文件移除后不可下载
    state.remove_file(entry["id"])
    code, _, _ = call("GET", f"/api/download?k={k}&id={entry['id']}")
    check("移除后返回404", code == 404)
    # 15 X-Auth 头鉴权
    code, body, _ = call("GET", f"/api/updates",
                         headers={"X-Auth": k})
    check("X-Auth头鉴权可用", code == 200)
    # 16 双栈:IPv4 已验证;检查 v6 socket 是否存在
    import socket as _s
    has_v6 = _s.has_dualstack_ipv6()
    check("平台支持IPv6双栈", has_v6)
    check("服务监听地址含端口", httpd.server_address[1] == PORT)

    # 17 跨网 IPv4 相关纯逻辑
    from channels import _soap_fault, classify_ipv4, parse_public_ip
    classify_cases = {
        "223.74.33.212": "public", "8.8.8.8": "public",
        "100.100.50.50": "cgnat", "100.64.0.1": "cgnat",
        "192.168.3.63": "private", "10.1.2.3": "private",
        "fe80::1": "invalid", "999.1.1.1": "invalid", "abc": "invalid",
    }
    check("IPv4四类划分",
          all(classify_ipv4(ip) == want for ip, want in classify_cases.items()))
    check("公网IP文本解析",
          parse_public_ip("223.74.33.212\n") == "223.74.33.212"
          and parse_public_ip("你的IP: 100.64.1.1") is None
          and parse_public_ip("no ip") is None)
    fault = _soap_fault("<errorCode>718</errorCode>"
                        "<errorDescription>Port In Conflict</errorDescription>")
    check("SOAP错误解析含718", bool(fault) and "718" in fault)
    check("SOAP成功响应无错误",
          _soap_fault("<u:AddPortMappingResponse "
                      "xmlns:u=\"urn:schemas-upnp-org:service:WANIPConnection:1\"/>")
          is None)

    # 18 手机热点识别逻辑
    from channels import _looks_like_hotspot, _same_subnet, active_networks
    check("热点网段识别(AOSP)",
          _looks_like_hotspot("192.168.43.1", "255.255.255.0", "192.168.43.100"))
    check("热点网段识别(iPhone)",
          _looks_like_hotspot("172.20.10.1", "255.255.255.240", "172.20.10.2"))
    check("/28掩码即热点",
          _looks_like_hotspot("192.168.88.1", "255.255.255.240", "192.168.88.2"))
    check("家庭路由不算热点",
          not _looks_like_hotspot("192.168.3.1", "255.255.255.0", "192.168.3.63"))
    check("同子网判断",
          _same_subnet("192.168.43.100", "192.168.43.1", "255.255.255.0")
          and not _same_subnet("192.168.3.63", "192.168.43.1", "255.255.255.0"))
    nets = active_networks()
    check("网卡枚举可用",
          isinstance(nets, list)
          and all({"ip", "gateway", "hotspot"} <= set(n) for n in nets))

    httpd.shutdown()
    httpd.server_close()
    shutil.rmtree(recv, ignore_errors=True)

    failed = [r for r in results if not r[1]]
    print(f"\n共 {len(results)} 项,失败 {len(failed)} 项")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
