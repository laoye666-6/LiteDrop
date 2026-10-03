"""轻传 LiteDrop — 连接通道检测与管理。

包含:局域网 IPv4 / 公网 IPv4 / 公网 IPv6 / Tailscale 地址检测、
UPnP 端口映射(跨网 IPv4 直连)、cloudflared 免注册隧道的
下载·启动·停止、Windows 防火墙放行。
"""
from __future__ import annotations

import ipaddress
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import urllib.parse

CLOUDFLARED_URL = ("https://github.com/cloudflare/cloudflared/releases/"
                   "latest/download/cloudflared-windows-amd64.exe")
TUNNEL_URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
TS_IP_RE = re.compile(r"\b(100\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")
CREATE_NO_WINDOW = 0x08000000


def _is_global_unicast_v6(addr: str) -> bool:
    a = addr.lower()
    return (a.startswith(("2", "3")) and not a.startswith("fe80")
            and "::" != a)


def lan_ipv4() -> str | None:
    """UDP connect 探测默认路由出口的局域网地址(不发包)。"""
    for probe in ("223.5.5.5", "192.168.3.1", "8.8.8.8"):
        try:
            s = socket.socket()
            s.settimeout(0.5)
            s.connect((probe, 53))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            continue
    nets = active_networks()
    return nets[0]["ip"] if nets else None


# ---------------- 网卡枚举与手机热点识别 ----------------
# 常见手机热点/USB共享 的网关网段(AOSP、iPhone、部分国产 ROM)
HOTSPOT_GATEWAY_PREFIXES = ("192.168.43.", "192.168.42.", "192.168.23.",
                            "192.168.107.", "192.168.150.", "192.168.241.",
                            "172.20.10.")
IF_TYPE_WIFI = 71


def _dec(b: bytes) -> str:
    return b.split(b"\x00")[0].decode("utf-8", "replace").strip()


def _adapters_info() -> list[dict]:
    """GetAdaptersInfo:枚举启用 IPv4 的适配器(IP/掩码/网关/类型/描述)。"""
    import ctypes

    class IP_ADDR_STRING(ctypes.Structure):
        pass

    IP_ADDR_STRING._fields_ = [
        ("Next", ctypes.POINTER(IP_ADDR_STRING)),
        ("IpAddress", ctypes.c_char * 16),
        ("IpMask", ctypes.c_char * 16),
        ("Context", ctypes.c_ulong),
    ]

    class IP_ADAPTER_INFO(ctypes.Structure):
        pass

    IP_ADAPTER_INFO._fields_ = [
        ("Next", ctypes.POINTER(IP_ADAPTER_INFO)),
        ("ComboIndex", ctypes.c_ulong),
        ("AdapterName", ctypes.c_char * 260),
        ("Description", ctypes.c_char * 132),
        ("AddressLength", ctypes.c_uint),
        ("Address", ctypes.c_ubyte * 8),
        ("Index", ctypes.c_ulong),
        ("Type", ctypes.c_uint),
        ("DhcpEnabled", ctypes.c_uint),
        ("CurrentIpAddress", ctypes.POINTER(IP_ADDR_STRING)),
        ("IpAddressList", IP_ADDR_STRING),
        ("GatewayList", IP_ADDR_STRING),
        ("DhcpServer", IP_ADDR_STRING),
        ("HaveWins", ctypes.c_int),
        ("PrimaryWinsServer", IP_ADDR_STRING),
        ("SecondaryWinsServer", IP_ADDR_STRING),
        ("LeaseObtained", ctypes.c_ulong),
        ("LeaseExpires", ctypes.c_ulong),
    ]

    def all_of(lst) -> list[tuple[str, str]]:
        """遍历 IP_ADDR_STRING 链表(首节点为内嵌结构),返回 (地址, 掩码)。"""
        items = [(_dec(lst.IpAddress), _dec(lst.IpMask))]
        nxt = lst.Next
        while nxt:
            cur = nxt.contents
            items.append((_dec(cur.IpAddress), _dec(cur.IpMask)))
            nxt = cur.Next
        return [(a, m) for a, m in items if a and a != "0.0.0.0"]

    iphlpapi = ctypes.WinDLL("iphlpapi")
    size = ctypes.c_ulong(0)
    if iphlpapi.GetAdaptersInfo(None, ctypes.byref(size)) != 111 \
            and size.value == 0:
        return []
    buf = (ctypes.c_ubyte * size.value)()
    if iphlpapi.GetAdaptersInfo(buf, ctypes.byref(size)) != 0:
        return []
    out = []
    node = ctypes.cast(buf, ctypes.POINTER(IP_ADAPTER_INFO))
    while node:
        a = node.contents
        desc = _dec(a.Description)
        addrs = all_of(a.IpAddressList)
        gws = all_of(a.GatewayList)
        if addrs:
            ip, mask = addrs[0]
            out.append({
                "desc": desc,
                "type": a.Type,
                "ip": ip,
                "mask": mask,
                "gateway": gws[0][0] if gws else "",
                "is_wifi": a.Type == IF_TYPE_WIFI or bool(
                    re.search(r"(?i)wi-?fi|wlan|802\.11|wireless", desc)),
            })
        node = a.Next
    return out


def _same_subnet(ip: str, other: str, mask: str) -> bool:
    try:
        net = ipaddress.ip_network(f"{ip}/{mask or '255.255.255.0'}",
                                   strict=False)
        return ipaddress.ip_address(other) in net
    except ValueError:
        return ip.rsplit(".", 1)[0] == other.rsplit(".", 1)[0]


def _has_internet_via(local_ip: str, timeout: float = 1.2) -> bool:
    """从指定本机地址发起真实 TCP 连接,判断该网络是否有互联网出口。"""
    for host, port in (("223.5.5.5", 443), ("119.29.29.29", 53)):
        try:
            s = socket.socket()
            s.bind((local_ip, 0))
            s.settimeout(timeout)
            s.connect((host, port))
            s.close()
            return True
        except OSError:
            continue
    return False


def _looks_like_hotspot(gateway: str, mask: str, ip: str) -> bool:
    """热点判定(满足其一):常见热点网段、/28 掩码(iPhone 特有)、无互联网出口。"""
    if gateway.startswith(HOTSPOT_GATEWAY_PREFIXES):
        return True
    if mask == "255.255.255.240":
        return True
    return not _has_internet_via(ip)


def active_networks() -> list[dict]:
    """枚举可用的 IPv4 网络,并识别手机热点(或 USB 共享)网络。"""
    out = []
    for a in _adapters_info():
        ip, gw, mask = a["ip"], a["gateway"], a["mask"]
        if not ip or not gw:
            continue
        if classify_ipv4(ip) != "private":
            continue
        if not _same_subnet(ip, gw, mask):
            continue
        out.append({"ip": ip, "gateway": gw, "mask": mask,
                    "desc": a["desc"], "is_wifi": a["is_wifi"],
                    "hotspot": _looks_like_hotspot(gw, mask, ip)})
    return out


def global_ipv6() -> str | None:
    """返回本机公网 IPv6(优先默认路由源地址)。"""
    for probe in ("2400:3200::1", "240c::6666", "2606:4700:4700::1111"):
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((probe, 53))
            addr = s.getsockname()[0]
            s.close()
            if _is_global_unicast_v6(addr):
                return addr.split("%")[0]
        except OSError:
            continue
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None,
                                   socket.AF_INET6)
        for info in infos:
            addr = info[4][0]
            if _is_global_unicast_v6(addr):
                return addr.split("%")[0]
    except OSError:
        pass
    return None


def tailscale_ip() -> str | None:
    """检测已安装且在线的 Tailscale,返回其 100.x IPv4。"""
    candidates = [shutil.which("tailscale"),
                  r"C:\Program Files\Tailscale\tailscale.exe",
                  r"C:\Program Files (x86)\Tailscale\tailscale.exe"]
    for exe in candidates:
        if not exe or not os.path.isfile(exe):
            continue
        try:
            out = subprocess.run(
                [exe, "ip", "-4"], capture_output=True, text=True,
                timeout=5, creationflags=CREATE_NO_WINDOW).stdout
            m = TS_IP_RE.search(out)
            if m:
                return m.group(1)
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


# ---------------- 公网 IPv4 探测(跨网 IPv4 直连) ----------------
PUBLIC_IP_SERVICES = ("https://ip.3322.net", "https://api.ipify.org",
                      "https://4.ipw.cn")
_V4_LOCK = threading.Lock()
V4_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


class _ForceIPv4:
    """临时把 socket.getaddrinfo 过滤为仅 A 记录,防止本机 v6 抢先导致返回 v6 地址。"""

    def __enter__(self):
        _V4_LOCK.acquire()
        self._orig = socket.getaddrinfo

        def _filtered(*args, **kwargs):
            return [r for r in self._orig(*args, **kwargs)
                    if r[0] == socket.AF_INET]

        socket.getaddrinfo = _filtered
        return self

    def __exit__(self, *exc):
        socket.getaddrinfo = self._orig
        _V4_LOCK.release()
        return False


def parse_public_ip(text: str) -> str | None:
    """从回显服务响应文本中提取 IPv4。"""
    m = V4_RE.search(text or "")
    if not m:
        return None
    kind = classify_ipv4(m.group(1))
    return m.group(1) if kind == "public" else None


def classify_ipv4(ip: str) -> str:
    """返回 public / cgnat / private / invalid。"""
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return "invalid"
    if addr.version != 4:
        return "invalid"
    if addr in ipaddress.ip_network("100.64.0.0/10"):
        return "cgnat"
    if addr.is_private or addr.is_loopback or addr.is_link_local \
            or addr.is_reserved or addr.is_multicast:
        return "private"
    return "public"


def public_ipv4(timeout: float = 3.0) -> str | None:
    """查询运营商出口公网 IPv4;全部源失败返回 None。"""
    with _ForceIPv4():
        for url in PUBLIC_IP_SERVICES:
            try:
                with urllib.request.urlopen(url, timeout=timeout) as r:
                    ip = parse_public_ip(r.read(256).decode("ascii", "ignore"))
                if ip:
                    return ip
            except OSError:
                continue
    return None


# ---------------- UPnP IGD 端口映射 ----------------
SSDP_ADDR = ("239.255.255.250", 1900)
_UPNP_LOCK = threading.Lock()
_upnp_cache: dict | None = None   # {"control_url":…, "service_type":…}


def _soap_post(control_url: str, service_type: str, action: str,
               args_xml: str) -> tuple[int, str]:
    body = (f'<?xml version="1.0"?>'
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            f's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="{service_type}">{args_xml}'
            f'</u:{action}></s:Body></s:Envelope>')
    req = urllib.request.Request(
        control_url, data=body.encode("utf-8"), method="POST")
    req.add_header("Content-Type", 'text/xml; charset="utf-8"')
    req.add_header("SOAPACTION", f'"{service_type}#{action}"')
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read(8192).decode("utf-8", "replace")


def _soap_fault(xml: str) -> str | None:
    """从 SOAP 响应提取 fault 错误描述;无 fault 返回 None。"""
    lower = xml.lower()
    if "<fault>" not in lower and "faultcode" not in lower \
            and "<errorcode>" not in lower:
        return None
    m = re.search(r"<errorCode>\s*(\d+)\s*</errorCode>", xml)
    d = re.search(r"<errorDescription>\s*(.*?)\s*</errorDescription>", xml)
    code = m.group(1) if m else "?"
    desc = d.group(1) if d else "未知错误"
    hints = {"713": "指定的映射已存在",
             "714": "映射不存在",
             "715": "参数不支持",
             "716": "内部端口与外部端口不一致,被路由器拒绝",
             "718": "端口冲突,换一个端口重试",
             "725": "路由器仅允许永不过期的映射"}
    return f"UPnP 错误 {code}({hints.get(code, '被路由器拒绝')}):{desc}"


def upnp_discover(force: bool = False) -> dict | None:
    """SSDP 发现网关 IGD,返回 {"control_url", "service_type"} 或 None(带缓存)。"""
    global _upnp_cache
    with _UPNP_LOCK:
        if _upnp_cache is not None and not force:
            return _upnp_cache or None
        _upnp_cache = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.6)
            msg = (b"M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
                   b'ST: upnp:rootdevice\r\nMAN: "ssdp:discover"\r\n'
                   b"MX: 2\r\n\r\n")
            for _ in range(3):
                s.sendto(msg, SSDP_ADDR)
            locations = []
            try:
                while len(locations) < 8:
                    data, _ = s.recvfrom(2048)
                    text = data.decode("utf-8", "replace")
                    m = re.search(r"(?i)location:\s*(\S+)", text)
                    if m and m.group(1) not in locations:
                        locations.append(m.group(1))
            except socket.timeout:
                pass
            finally:
                s.close()
        except OSError:
            return None
        for loc in locations:
            info = _parse_device_description(loc)
            if info:
                _upnp_cache = info
                return info
    return None


def _parse_device_description(location: str) -> dict | None:
    """解析 IGD 设备描述 XML,找 WANIPConnection/WANPPPConnection 的 controlURL。"""
    try:
        with urllib.request.urlopen(location, timeout=4) as r:
            xml = r.read(65536).decode("utf-8", "replace")
    except OSError:
        return None
    base_m = re.search(r"(?is)<URLBase>\s*(.*?)\s*</URLBase>", xml)
    base = base_m.group(1).strip() if base_m else location
    for svc in re.finditer(
            r"(?is)<service>(.*?)</service>", xml):
        block = svc.group(1)
        st_m = re.search(
            r"(?is)<serviceType>\s*([^<]*(?:WANIPConnection|WANPPPConnection)[^<]*)\s*</serviceType>",
            block)
        cu_m = re.search(r"(?is)<controlURL>\s*([^<\s]+)\s*</controlURL>",
                         block)
        if st_m and cu_m:
            control = urllib.parse.urljoin(base, cu_m.group(1))
            return {"control_url": control,
                    "service_type": st_m.group(1).strip()}
    return None


def upnp_add_mapping(port: int, lan_ip: str,
                     lease: int = 0) -> tuple[bool, str]:
    """向网关添加 TCP 端口映射;返回 (成功?, 错误描述)。"""
    info = upnp_discover()
    if not info:
        return False, "未发现支持 UPnP 的路由器设备"
    args = ("<NewRemoteHost></NewRemoteHost>"
            f"<NewExternalPort>{port}</NewExternalPort>"
            "<NewProtocol>TCP</NewProtocol>"
            f"<NewInternalPort>{port}</NewInternalPort>"
            f"<NewInternalClient>{lan_ip}</NewInternalClient>"
            "<NewEnabled>1</NewEnabled>"
            "<NewPortMappingDescription>LiteDrop</NewPortMappingDescription>"
            f"<NewLeaseDuration>{lease}</NewLeaseDuration>")
    try:
        code, resp = _soap_post(info["control_url"], info["service_type"],
                                "AddPortMapping", args)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", "replace")
        return False, _soap_fault(detail) or f"路由器返回 HTTP {exc.code}"
    except OSError as exc:
        return False, f"无法连接路由器:{exc}"
    if 200 <= code < 300:
        return True, ""
    return False, _soap_fault(resp) or f"路由器返回 HTTP {code}"


def upnp_delete_mapping(port: int) -> None:
    """尽力删除映射(失败静默,不影响退出流程)。"""
    try:
        info = upnp_discover()
        if not info:
            return
        args = ("<NewRemoteHost></NewRemoteHost>"
                f"<NewExternalPort>{port}</NewExternalPort>"
                "<NewProtocol>TCP</NewProtocol>")
        _soap_post(info["control_url"], info["service_type"],
                   "DeletePortMapping", args)
    except OSError:
        pass


def upnp_map_auto(port: int) -> tuple[bool, str, str]:
    """跨网 IPv4 直连准备:返回 (成功?, 公网IP, 错误描述)。"""
    wan = public_ipv4()
    if not wan:
        return False, "", "未能获取公网 IPv4(探测服务不可达)"
    kind = classify_ipv4(wan)
    if kind == "cgnat":
        return False, wan, "宽带是运营商级 NAT(无公网 IPv4),无法 IPv4 直连"
    if kind != "public":
        return False, wan, f"出口地址 {wan} 不是公网 IPv4"
    lan = lan_ipv4()
    if not lan:
        return False, wan, "未获取到局域网 IP"
    ok, err = upnp_add_mapping(port, lan)
    if not ok and "725" not in err:   # 725 之外的重试:部分路由器拒绝永久映射,改用 2 小时租期
        ok, err = upnp_add_mapping(port, lan, lease=7200)
    return ok, wan, err



def cloudflared_path() -> str | None:
    """按优先级查找 cloudflared.exe:程序目录 → ~/.litedrop → PATH。"""
    here = os.path.dirname(os.path.abspath(__file__))
    frozen = getattr(os, "_MEIPASS2", None) or ""
    local = os.path.join(os.path.expanduser("~"), ".litedrop",
                         "cloudflared.exe")
    for path in (os.path.join(here, "cloudflared.exe"),
                 os.path.join(frozen, "cloudflared.exe") if frozen else None,
                 local, shutil.which("cloudflared")):
        if path and os.path.isfile(path):
            return path
    return None


class TunnelManager:
    """管理一个 cloudflared 快速隧道子进程。

    回调(在后台线程触发):
      on_log(str) / on_url(str) / on_state(str)  # starting|running|stopped|error
    """

    def __init__(self, on_log, on_url, on_state):
        self.on_log = on_log
        self.on_url = on_url
        self.on_state = on_state
        self.proc: subprocess.Popen | None = None
        self.url: str | None = None
        self._want_stop = False
        self._restarts = 0
        self._last_exe: str | None = None
        self._last_port: int | None = None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, port: int) -> None:
        if self.running:
            return
        self._want_stop = False
        self._restarts = 0
        exe = cloudflared_path()
        if not exe:
            self.on_state("starting")
            threading.Thread(target=self._download_and_start,
                             args=(port,), daemon=True).start()
            return
        self._spawn(exe, port)

    def _download_and_start(self, port: int) -> None:
        dest_dir = os.path.join(os.path.expanduser("~"), ".litedrop")
        dest = os.path.join(dest_dir, "cloudflared.exe")
        try:
            os.makedirs(dest_dir, exist_ok=True)
            self.on_log("正在下载 cloudflared(约 20MB,GitHub 源,国内可能较慢)…")
            urllib.request.urlretrieve(CLOUDFLARED_URL, dest,
                                       reporthook=self._progress)
            self.on_log("cloudflared 下载完成")
            self._spawn(dest, port)
        except Exception as exc:  # noqa: BLE001
            self.on_state("error")
            self.on_log(f"cloudflared 下载失败:{exc}")
            self.on_log(f"可手动下载 {CLOUDFLARED_URL} 保存到 {dest} 后重试")

    def _progress(self, count: int, block: int, total: int) -> None:
        if total > 0:
            pct = min(100, count * block * 100 // total)
            if pct % 10 == 0:
                self.on_log(f"cloudflared 下载 {pct}%")

    def _spawn(self, exe: str, port: int) -> None:
        self._last_exe = exe
        self._last_port = port
        self.url = None
        self.on_state("starting")
        self.on_log(f"正在启动隧道:{exe}")
        self.proc = subprocess.Popen(
            [exe, "tunnel", "--url", f"http://127.0.0.1:{port}",
             "--no-autoupdate", "--protocol", "http2"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
            creationflags=CREATE_NO_WINDOW)
        threading.Thread(target=self._pump, daemon=True).start()

    MAX_RESTARTS = 3

    def _pump(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            m = TUNNEL_URL_RE.search(line)
            if m and not self.url:
                self.url = m.group(0)
                self.on_state("running")
                self.on_url(self.url)
                self.on_log(f"公网隧道已就绪:{self.url}")
            elif "failed" in line.lower() or "error" in line.lower():
                self.on_log(f"隧道:{line[:160]}")
        if self._want_stop:
            self.on_state("stopped")
            return
        # 意外退出:自动重启(每次启动都会换新地址)
        self._restarts += 1
        if self._restarts <= self.MAX_RESTARTS and self._last_exe:
            self.on_log(f"隧道意外退出,正在自动重启({self._restarts}/"
                        f"{self.MAX_RESTARTS})…")
            time.sleep(2)
            self._spawn(self._last_exe, self._last_port)
        else:
            self.on_state("error")
            self.on_log("隧道多次退出已放弃,可再点「启动公网隧道」重试,"
                        "或改用其他通道")

    def stop(self) -> None:
        self._want_stop = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        self.url = None
        self.on_state("stopped")


# ---------------- Windows 防火墙 ----------------
def _firewall_rule_text(name: str = "LiteDrop") -> str | None:
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule",
             f"name={name}"], capture_output=True, timeout=10,
            creationflags=CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    # 中文版 netsh 输出为 GBK;英文版为 ASCII(gbk 解码兼容)
    text = r.stdout.decode("gbk", "replace")
    return text if ("规则名称" in text or "Rule Name" in text) else None


def firewall_rule_port(name: str = "LiteDrop") -> int | None:
    """返回 LiteDrop 入站规则的本地端口;无规则或无法解析返回 None。"""
    text = _firewall_rule_text(name)
    if not text:
        return None
    m = re.search(r"(?:本地端口|Local Port):\s*[　\s]*(\d+)", text)
    return int(m.group(1)) if m else None


def add_firewall_rule(port: int, name: str = "LiteDrop") -> bool:
    """弹 UAC 提权重加入站规则(先删旧规则,避免改端口后规则失效/重复)。"""
    inner = (f'netsh advfirewall firewall delete rule name="{name}" >nul 2>&1& '
             f"netsh advfirewall firewall add rule name=\"{name}\" dir=in "
             f"action=allow protocol=TCP localport={port}")
    ps_cmd = ("Start-Process cmd -Verb RunAs -Wait -WindowStyle Hidden "
              f"-ArgumentList '/c {inner}'")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                       timeout=120, creationflags=CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return firewall_rule_port() == port

