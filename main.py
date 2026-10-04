# -*- coding: utf-8 -*-
"""轻传 LiteDrop — PC 端主程序(PySide6 深色界面)。

用法:python main.py [--selftest]
"""
from __future__ import annotations

import os
import sys
import threading
import time
import urllib.error
import urllib.request

from PySide6.QtCore import (QBuffer, QEasingCurve, QObject, QPropertyAnimation,
                            QSettings, QSize, Qt, QTime, QTimer, Signal)
from PySide6.QtGui import QFont, QIcon, QLinearGradient, QPainter, QPixmap, QColor
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QFileDialog, QFrame, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QPlainTextEdit, QPushButton,
                               QScrollArea, QSpinBox, QSplitter,
                               QSystemTrayIcon, QTabWidget, QTextEdit,
                               QVBoxLayout, QWidget)

import channels
from mobile_page import PAGE_HTML
from server import LiteDropServer, TransferState

APP_NAME = "轻传 LiteDrop"

STYLE = """
* { font-family:"Microsoft YaHei UI"; outline:none; }
QMainWindow, QDialog { background:#0a0f1c; }
QFrame#card { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
  stop:0 #121b30, stop:1 #0f1728); border:1px solid #1d2942; border-radius:16px; }
QLabel { color:#e8eef9; background:transparent; }
QLabel#h1 { font-size:17px; font-weight:700; }
QLabel#sect { color:#8ca0c0; font-size:12px; font-weight:600; letter-spacing:1px; }
QLabel#muted { color:#8ca0c0; font-size:12px; }
QPushButton { background:#1a2540; color:#e8eef9; border:1px solid #26355a;
  border-radius:10px; padding:7px 14px; font-size:13px; }
QPushButton:hover { background:#223054; }
QPushButton:pressed { background:#182342; }
QPushButton:disabled { color:#5a6b8c; background:#141d33; border-color:#1d2942; }
QPushButton#primary { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #4f7cff, stop:1 #22d3ee); border:none; color:#fff; font-weight:600;
  padding:8px 22px; letter-spacing:1px; }
QPushButton#primary:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #5f8aff, stop:1 #3cd8f2); }
QPushButton#primary:pressed { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #4068e0, stop:1 #18bcd8); }
QPushButton#small { padding:4px 12px; font-size:12px; border-radius:8px; }
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {
  background:#0d1526; color:#e8eef9; border:1px solid #22304d;
  border-radius:10px; padding:6px 10px; font-size:13px;
  selection-background-color:#2a3f6e; }
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
  border-color:#4f7cff; }
QComboBox::drop-down { border:none; width:22px; }
QComboBox::down-arrow { image:none; border-left:5px solid transparent;
  border-right:5px solid transparent; border-top:6px solid #8ca0c0;
  margin-right:8px; }
QComboBox QAbstractItemView { background:#111a2e; border:1px solid #26355a;
  color:#e8eef9; selection-background-color:#223054; outline:none;
  border-radius:8px; padding:4px; }
QSpinBox::up-button, QSpinBox::down-button { width:16px; border:none;
  background:transparent; }
QSpinBox::up-arrow { border-left:4px solid transparent;
  border-right:4px solid transparent; border-bottom:5px solid #8ca0c0; }
QSpinBox::down-arrow { border-left:4px solid transparent;
  border-right:4px solid transparent; border-top:5px solid #8ca0c0; }
QTabWidget::pane { border:1px solid #1d2942; border-radius:12px; top:-1px; }
QTabBar::tab { background:transparent; color:#8ca0c0; padding:7px 18px;
  border-top-left-radius:10px; border-top-right-radius:10px; font-size:13px; }
QTabBar::tab:selected { color:#e8eef9; background:#16213c; }
QScrollBar:vertical { background:transparent; width:8px; margin:2px; }
QScrollBar::handle:vertical { background:#26355a; border-radius:4px; min-height:30px; }
QScrollBar::handle:vertical:hover { background:#33477a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar:horizontal { background:transparent; height:8px; margin:2px; }
QScrollBar::handle:horizontal { background:#26355a; border-radius:4px; min-width:30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
QTextEdit#log { color:#8ca0c0; font-size:12px; border-radius:12px;
  background:#0d1526; border:1px solid #1d2942; }
QTextEdit#log QScrollBar:vertical { width:6px; }
QCheckBox { color:#e8eef9; font-size:13px; spacing:6px; }
QCheckBox::indicator { width:16px; height:16px; border-radius:5px;
  border:1px solid #2c3d60; background:#0d1526; }
QCheckBox::indicator:hover { border-color:#4f7cff; }
QCheckBox::indicator:checked { background:#4f7cff; border-color:#4f7cff; }
QSplitter::handle { background:#0a0f1c; width:5px; }
QStatusBar { color:#5a6b8c; background:transparent;
  border-top:1px solid #14203a; }
QStatusBar::item { border:none; }
QMenu { background:#111a2e; border:1px solid #26355a; border-radius:10px; padding:6px; }
QMenu::item { color:#e8eef9; padding:6px 22px; border-radius:6px; }
QMenu::item:selected { background:#223054; }
"""

CHANNEL_HINTS = {
    "局域网": "手机与电脑连同一个 Wi-Fi 时使用,速度最快。",
    "热点": "电脑已连接手机热点,手机直接扫码即可;此方式不要求手机能上网。",
    "IPv4": "跨网通道:手机开流量即可访问;宽带重拨后 IP 会变,点「重新检测」刷新。",
    "IPv6": "手机用流量或不同 Wi-Fi 时可用;连不上时依次检查:"
            "① 点「防火墙放行」;② 手机浏览器打开 test-ipv6.com 确认手机有 IPv6;"
            "③ 路由器「IPv6 防火墙」放行(华为路由器:更多功能 → 网络设置 → "
            "IPv6 防火墙,关闭或添加放行本端口的 TCP 规则)。",
    "隧道": "经 Cloudflare 中转,任何网络都能连;速度较慢,适合兜底。",
    "Tailscale": "虚拟局域网通道,两端需登录同一 Tailscale 账号。",
}


def channel_hint(name: str) -> str:
    for key, hint in CHANNEL_HINTS.items():
        if key in name:
            return hint
    return ""


def make_app_icon() -> QIcon:
    """程序图标:圆角渐变方块 + 「传」字。"""
    size = 256
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor("#4f7cff"))
    grad.setColorAt(1, QColor("#22d3ee"))
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(8, 8, size - 16, size - 16, 56, 56)
    f = QFont("Microsoft YaHei UI", 120)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#ffffff"))
    p.drawText(pm.rect(), Qt.AlignCenter, "传")
    p.end()
    return QIcon(pm)


def make_qr_pixmap(url: str, px: int = 204) -> QPixmap | None:
    try:
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0b1220", back_color="#ffffff")
        buf = QBuffer()
        buf.open(QBuffer.ReadWrite)
        img.save(buf, "PNG")
        pm = QPixmap()
        pm.loadFromData(buf.data(), "PNG")
        buf.close()
        if px:
            pm = pm.scaled(px, px, Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
        return pm
    except Exception:
        return None


def fmt_size(n) -> str:
    x = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if x < 1024 or unit == "GB":
            return f"{x:.1f} {unit}" if unit != "B" else f"{int(x)} B"
        x /= 1024
    return f"{x:.1f} GB"


class Bridge(QObject):
    """后台线程 → GUI 线程的事件桥(跨线程信号自动排队)。"""
    text_received = Signal(dict)
    file_received = Signal(dict)
    log = Signal(str)
    channels_ready = Signal(dict)
    tunnel_state = Signal(str)
    tunnel_url = Signal(str)
    tunnel_verified = Signal(str)
    firewall_done = Signal(bool)
    page_opened = Signal()


class ServerEvents:
    """server.py 回调接口,转发到 Bridge(可在任意线程调用)。"""

    def __init__(self, bridge: Bridge):
        self.bridge = bridge

    def on_text_received(self, item):
        self.bridge.text_received.emit(item)

    def on_file_received(self, entry):
        self.bridge.file_received.emit(entry)

    def on_receiving(self, name):
        self.bridge.log.emit(f"正在接收文件:{name}")

    def on_page_opened(self):
        self.bridge.page_opened.emit()

    def on_log(self, msg):
        self.bridge.log.emit(str(msg))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_app_icon())
        self.resize(1280, 800)
        self.setMinimumSize(1060, 660)

        self.settings = QSettings("LiteDrop", "LiteDrop")
        self.server: LiteDropServer | None = None
        self.state: TransferState | None = None
        self.bridge = Bridge()
        self.events = ServerEvents(self.bridge)
        self.tunnel = channels.TunnelManager(
            on_log=self.bridge.log.emit,
            on_url=self.bridge.tunnel_url.emit,
            on_state=self.bridge.tunnel_state.emit)
        self.channels: list[tuple[str, str]] = []   # (通道名, url)
        self._mapped_port: int | None = None        # 本程序建立的 UPnP 映射
        self._tunnel_verified_url: str | None = None  # 自检通过的隧道地址
        self._fw_hint_state: str | None = None      # 防火墙提示去重
        self.tray_msg_shown = False

        self._build_ui()
        self._connect_signals()
        self._build_tray()

    # ------------------------------------------------------------------ UI
    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        if title:
            t = QLabel(title)
            t.setObjectName("sect")
            lay.addWidget(t)
        return card, lay

    def _build_ui(self):
        # ---------- 顶栏 ----------
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(18, 14, 18, 4)
        top_lay.setSpacing(12)
        title = QLabel('<span style="font-size:19px;font-weight:800;">轻传 '
                       '</span><span style="font-size:19px;font-weight:800;'
                       'color:#5f8aff;">LiteDrop</span>')
        self.pill = QLabel("● 已停止")
        self.pill.setStyleSheet(self._pill_qss(False))
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(self.settings.value("port", 8765, type=int))
        self.spin_port.setPrefix("端口 ")
        self.spin_port.setFixedWidth(130)
        self.spin_port.setToolTip("修改端口后如服务已在运行,会自动重启")
        self.chk_token = QCheckBox("扫码鉴权")
        self.chk_token.setChecked(True)
        self.chk_token.setToolTip("开启后手机需持二维码中的口令才能访问")
        self.chk_tray = QCheckBox("关闭时最小化到托盘")
        self.chk_tray.setChecked(
            self.settings.value("minimize_tray", True, type=bool))
        self.btn_toggle = QPushButton("  启动服务  ")
        self.btn_toggle.setObjectName("primary")
        top_lay.addWidget(title)
        top_lay.addWidget(self.pill)
        top_lay.addStretch()
        top_lay.addWidget(self.spin_port)
        top_lay.addWidget(self.chk_token)
        top_lay.addWidget(self.chk_tray)
        top_lay.addWidget(self.btn_toggle)

        # ---------- 左列 ----------
        conn_card, conn_lay = self._card("连 接 通 道")
        self.combo = QComboBox()
        conn_lay.addWidget(self.combo)

        qr_wrap = QHBoxLayout()
        qr_wrap.addStretch()
        qr_box = QVBoxLayout()
        qr_box.setSpacing(8)
        self.qr_label = QLabel("服务未启动")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(220, 220)
        self.qr_label.setStyleSheet(
            "background:#ffffff; border-radius:16px; color:#64748b; font-size:13px;")
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(38)
        glow.setColor(QColor(79, 124, 255, 105))
        glow.setOffset(0, 6)
        self.qr_label.setGraphicsEffect(glow)
        qr_box.addWidget(self.qr_label)
        qr_cap = QLabel("手机扫码连接 · 或复制下方地址")
        qr_cap.setObjectName("muted")
        qr_cap.setAlignment(Qt.AlignCenter)
        qr_box.addWidget(qr_cap)
        qr_wrap.addLayout(qr_box)
        qr_wrap.addStretch()
        conn_lay.addLayout(qr_wrap)

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setReadOnly(True)
        self.url_edit.setPlaceholderText("连接地址将显示在这里")
        btn_copy = QPushButton("复制")
        btn_copy.setObjectName("small")
        btn_copy.clicked.connect(self._copy_url)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(btn_copy)
        conn_lay.addLayout(url_row)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("⟳ 重新检测")
        btn_firewall = QPushButton("🛡 防火墙放行")
        btn_map = QPushButton("🔗 IPv4 映射")
        self.btn_tunnel = QPushButton("☁ 启动公网隧道")
        for b in (btn_refresh, btn_firewall, btn_map, self.btn_tunnel):
            b.setObjectName("small")
        btn_refresh.clicked.connect(self.refresh_channels)
        btn_map.clicked.connect(self._retry_mapping)
        btn_firewall.clicked.connect(self._firewall)
        self.btn_tunnel.clicked.connect(self._toggle_tunnel)
        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_firewall)
        btn_row.addWidget(btn_map)
        btn_row.addWidget(self.btn_tunnel)
        conn_lay.addLayout(btn_row)

        self.channel_hint = QLabel(" ")
        self.channel_hint.setObjectName("muted")
        self.channel_hint.setWordWrap(True)
        conn_lay.addWidget(self.channel_hint)
        conn_lay.addStretch()

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(12)
        left_lay.addWidget(conn_card)
        left_lay.addStretch(1)

        # ---------- 中列:发送到手机 ----------
        send_card, send_lay = self._card("发 送 到 手 机")
        self.send_text = QPlainTextEdit()
        self.send_text.setPlaceholderText("输入文字,手机「接收」页可查看并复制")
        self.send_text.setFixedHeight(72)
        btn_send = QPushButton("发送文本")
        btn_send.setObjectName("primary")
        btn_send.clicked.connect(self._push_text)
        send_lay.addWidget(self.send_text)
        send_lay.addWidget(btn_send)

        file_head = QHBoxLayout()
        ftitle = QLabel("可下载文件")
        ftitle.setObjectName("muted")
        btn_add = QPushButton("添加文件")
        btn_rm = QPushButton("移除选中")
        for b in (btn_add, btn_rm):
            b.setObjectName("small")
        btn_add.clicked.connect(self._add_files)
        btn_rm.clicked.connect(self._remove_shared)
        file_head.addWidget(ftitle, 1)
        file_head.addWidget(btn_add)
        file_head.addWidget(btn_rm)
        send_lay.addLayout(file_head)

        self.shared_list = QListWidget()
        self.shared_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.shared_list.setStyleSheet(
            "QListWidget{background:#0d1526;border:1px solid #1d2942;"
            "border-radius:10px;}")
        self.shared_list.itemDoubleClicked.connect(
            lambda item: os.startfile(item.data(Qt.UserRole)))
        send_lay.addWidget(self.shared_list, 1)

        mid = QWidget()
        mid_lay = QVBoxLayout(mid)
        mid_lay.setContentsMargins(0, 0, 0, 0)
        mid_lay.addWidget(send_card, 1)

        # ---------- 右列 ----------
        recv_card, recv_lay = self._card("从 手 机 接 收")
        recv_head = QHBoxLayout()
        self.chk_autocopy = QCheckBox("新文本自动复制到剪贴板")
        self.chk_autocopy.setChecked(
            self.settings.value("autocopy", True, type=bool))
        self.chk_autocopy.toggled.connect(
            lambda v: self.settings.setValue("autocopy", v))
        btn_open = QPushButton("打开接收目录")
        btn_open.setObjectName("small")
        btn_open.clicked.connect(self._open_receive_dir)
        recv_head.addWidget(self.chk_autocopy)
        recv_head.addStretch()
        recv_head.addWidget(btn_open)
        recv_lay.addLayout(recv_head)

        self.tabs = QTabWidget()
        self.text_scroll = self._make_list_scroll()
        self.file_scroll = self._make_list_scroll()
        self.text_vbox = self.text_scroll._vbox
        self.file_vbox = self.file_scroll._vbox
        self._add_empty_hint(self.text_vbox, "📭", "手机发来的文本会出现在这里")
        self._add_empty_hint(self.file_vbox, "📥",
                             "手机发来的文件保存在接收目录,可点目录按钮打开")
        self.tabs.addTab(self.text_scroll, "文 本")
        self.tabs.addTab(self.file_scroll, "文 件")
        recv_lay.addWidget(self.tabs, 1)

        dir_row = QHBoxLayout()
        dlabel = QLabel("接收目录")
        dlabel.setObjectName("muted")
        self.dir_edit = QLineEdit(self._receive_dir())
        self.dir_edit.editingFinished.connect(self._dir_changed)
        btn_browse = QPushButton("浏览")
        btn_browse.setObjectName("small")
        btn_browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(dlabel)
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(btn_browse)
        recv_lay.addLayout(dir_row)

        log_card, log_lay = self._card("运 行 日 志")
        self.log_box = QTextEdit()
        self.log_box.setObjectName("log")
        self.log_box.setReadOnly(True)
        self.log_box.document().setMaximumBlockCount(400)
        log_lay.addWidget(self.log_box, 1)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(12)
        right_lay.addWidget(recv_card, 3)
        right_lay.addWidget(log_card, 2)

        # ---------- 总布局 ----------
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 0, 14, 6)
        root.setSpacing(8)
        root.addWidget(top)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.addWidget(left)
        splitter.addWidget(mid)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)
        splitter.setSizes([370, 330, 470])
        root.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage(
            "手机端无需安装任何 App,浏览器扫码即用")

    @staticmethod
    def _make_list_scroll() -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;}")
        scroll.viewport().setStyleSheet("background:#0e1628;")
        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(10, 12, 10, 12)
        vbox.setSpacing(10)
        vbox.addStretch()
        scroll.setWidget(inner)
        scroll._vbox = vbox  # scroll 持有 inner 的所有权,防止提前回收
        return scroll

    def _add_empty_hint(self, vbox: QVBoxLayout, emoji: str, text: str):
        hint = QLabel(f"{emoji}\n{text}")
        hint.setObjectName("empty_hint")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            "font-size:14px; color:#8ca0c0; padding:34px 0; background:transparent;")
        vbox.insertWidget(0, hint)

    @staticmethod
    def _pill_qss(running: bool) -> str:
        if running:
            fg, bg, bd = "#34d399", "rgba(52,211,153,.12)", "rgba(52,211,153,.4)"
        else:
            fg, bg, bd = "#f87171", "rgba(239,68,68,.10)", "rgba(239,68,68,.35)"
        return (f"background:{bg}; color:{fg}; border:1px solid {bd};"
                "border-radius:20px; padding:3px 12px; font-size:12px;"
                "font-weight:600;")

    # ------------------------------------------------------------- 信号接线
    def _connect_signals(self):
        self.bridge.log.connect(self._log)
        self.bridge.text_received.connect(self._on_text)
        self.bridge.file_received.connect(self._on_file)
        self.bridge.channels_ready.connect(self._on_channels)
        self.bridge.tunnel_url.connect(self._on_tunnel_url)
        self.bridge.tunnel_verified.connect(self._on_tunnel_verified)
        self.bridge.tunnel_state.connect(self._on_tunnel_state)
        self.bridge.firewall_done.connect(self._on_firewall)
        self.bridge.page_opened.connect(
            lambda: self._log("手机已打开页面"))
        self.combo.currentIndexChanged.connect(self._update_qr)
        self.btn_toggle.clicked.connect(self._toggle_server)
        self.spin_port.editingFinished.connect(self._port_changed)
        self.chk_token.toggled.connect(self._token_toggled)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        menu = QMenu()
        act_show = menu.addAction("显示主窗口")
        act_show.triggered.connect(self.showNormal)
        act_quit = menu.addAction("退出")
        act_quit.triggered.connect(self._quit)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(
            lambda r: self.showNormal() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    # ------------------------------------------------------------- 服务控制
    def _receive_dir(self) -> str:
        return self.settings.value(
            "receive_dir",
            os.path.join(os.path.expanduser("~"), "Desktop", "LiteDrop接收"))

    def _toggle_server(self):
        if self.server:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        if self.server:
            return
        recv = self.dir_edit.text().strip() or self._receive_dir()
        try:
            os.makedirs(recv, exist_ok=True)
            # 口令持久化:重启后不变,手机旧链接/历史记录仍可用
            token = self.settings.value("token") or None
            self.state = TransferState(recv, token=token)
            self.settings.setValue("token", self.state.token)
            self.state.require_token = self.chk_token.isChecked()
            self.server = LiteDropServer(self.spin_port.value(), self.state,
                                         self.events, PAGE_HTML)
            self.server.start()
        except OSError as exc:
            self.server = None
            self.state = None
            self._log(f"启动失败:{exc}(端口可能被占用,换一个试试)")
            return
        self.settings.setValue("port", self.server.port)
        self.pill.setText(f"● 运行中 · 端口 {self.server.port}")
        self.pill.setStyleSheet(self._pill_qss(True))
        self.btn_toggle.setText("  停止服务  ")
        stack = ("IPv4 + IPv6 双栈" if
                 self.server.httpd.address_family.name == "AF_INET6"
                 else "仅 IPv4(IPv6 监听失败,跨网 v6 不可用)")
        self._log(f"服务已启动,端口 {self.server.port},监听:{stack}")
        self._log(f"接收目录:{recv}")
        self.refresh_channels()

    def _stop_server(self):
        self._remove_mapping()
        if self.tunnel.running:
            self.tunnel.stop()
            self.btn_tunnel.setText("☁ 启动公网隧道")
        if self.server:
            self.server.stop()
            self.server = None
        self.state = None
        self.pill.setText("● 已停止")
        self.pill.setStyleSheet(self._pill_qss(False))
        self.btn_toggle.setText("  启动服务  ")
        self.channels = []
        self._rebuild_combo()
        self._log("服务已停止")

    def _remove_mapping(self):
        """删除本程序在路由器上建立的 UPnP 映射(尽力而为)。"""
        if self._mapped_port is None:
            return
        port, self._mapped_port = self._mapped_port, None
        channels.upnp_delete_mapping(port)
        self._log(f"已删除路由器端口映射(TCP {port})")

    def _retry_mapping(self):
        if not self.server:
            self._log("请先启动服务再尝试 IPv4 映射")
            return
        self._log("正在尝试建立 IPv4 端口映射…")
        self.refresh_channels()

    def _port_changed(self):
        new_port = self.spin_port.value()
        if self.server and self.server.port == new_port:
            return  # 未实际修改(如切换焦点触发),不重启
        self.settings.setValue("port", new_port)
        if self.server:
            self._log(f"端口改为 {new_port},正在重启服务…")
            self._stop_server()
            self._start_server()

    def _token_toggled(self, on: bool):
        if self.state:
            self.state.require_token = on
            self.refresh_channels()

    # ------------------------------------------------------------- 通道
    def refresh_channels(self):
        if not self.server:
            return
        threading.Thread(target=self._detect, daemon=True).start()

    def _detect(self):
        nets = channels.active_networks()
        if not nets:
            lan = channels.lan_ipv4()
            if lan:
                nets = [{"ip": lan, "gateway": "", "mask": "", "desc": "",
                         "is_wifi": False, "hotspot": False}]
        info = {
            "nets": nets,
            "v6": channels.global_ipv6(),
            "ts": channels.tailscale_ip(),
        }
        # 公网端口映射仅对非热点网络尝试(手机热点网关不提供 UPnP IGD)
        main_net = next((n for n in nets if not n["hotspot"]), None)
        if self.server and main_net:
            ok, wan, err = channels.upnp_map_auto(self.server.port)
            info["wan"] = wan or None
            info["mapped"] = ok
            info["map_err"] = err
        else:
            info["wan"] = None
            info["mapped"] = False
            info["map_err"] = "热点网络下无需公网端口映射" if nets else ""
        self.bridge.channels_ready.emit(info)

    def _on_channels(self, info: dict):
        if not self.server or not self.state:
            return
        port = self.server.port
        suffix = f"/?k={self.state.token}" if self.state.require_token else "/"
        chans: list[tuple[str, str, str]] = []
        nets = info.get("nets") or []
        plain = [n for n in nets if not n.get("hotspot")]
        multi = len(plain) > 1
        for net in nets:
            url = f"http://{net['ip']}:{port}{suffix}"
            if net.get("hotspot"):
                chans.append(("手机热点直连", url,
                              "电脑已连接手机热点,手机直接扫码即可;"
                              "此方式不要求手机能上网。"))
            else:
                name = "局域网直连(IPv4)"
                if multi:
                    name += "·WLAN" if net.get("is_wifi") else "·以太网"
                chans.append((name, url, channel_hint(name)))
        if info.get("wan"):
            if info.get("mapped"):
                hint = (f"已自动在路由器建立端口映射(UPnP),手机开流量即可访问。"
                        f"宽带重拨后 IP 会变,点「重新检测」刷新。")
            else:
                hint = (f"未建立端口映射:{info.get('map_err') or '原因未知'}。"
                        f"可在路由器后台手动转发 TCP {port} 到本机,或点「IPv4 映射」重试。")
            chans.append(("IPv4 直连(跨网)",
                          f"http://{info['wan']}:{port}{suffix}", hint))
        if info.get("v6"):
            chans.append(("IPv6 直连(跨网)",
                          f"http://[{info['v6']}]:{port}{suffix}",
                          channel_hint("IPv6")))
        if self._tunnel_verified_url and self.tunnel.running:
            chans.append(("公网隧道(跨网兜底)",
                          f"{self._tunnel_verified_url}{suffix}",
                          channel_hint("隧道")))
        if info.get("ts"):
            chans.append(("Tailscale",
                          f"http://{info['ts']}:{port}{suffix}",
                          channel_hint("Tailscale")))
        seen: set[str] = set()
        chans = [c for c in chans if not (c[1] in seen or seen.add(c[1]))]
        self.channels = chans
        self._mapped_port = port if info.get("mapped") else None
        self._rebuild_combo()
        self._log("通道检测完成:" + ("、".join(n for n, _, _ in chans) or "无"))
        if info.get("wan") and not info.get("mapped"):
            self._log(f"IPv4 映射失败:{info.get('map_err')}")
        # 防火墙体检(每个端口状态只提示一次)
        if self.server:
            rule_port = channels.firewall_rule_port()
            state = f"{rule_port}/{self.server.port}"
            if state != self._fw_hint_state:
                self._fw_hint_state = state
                if rule_port is None:
                    self._log("提示:防火墙放行规则不存在,跨网直连可能被 "
                              "Windows 拦截,请点「防火墙放行」")
                elif rule_port != self.server.port:
                    self._log(f"提示:防火墙规则端口({rule_port})与服务端口"
                              f"({self.server.port})不一致,请重新点"
                              f"「防火墙放行」(会自动清理旧规则)")

    # ------------------------------------------------------------- 隧道自检
    def _on_tunnel_url(self, url: str):
        self._log(f"隧道地址已获取,正在自检回环可达性…")
        threading.Thread(target=self._verify_tunnel, args=(url,),
                         daemon=True).start()

    def _verify_tunnel(self, url: str):
        """经 Cloudflare 回环访问本机服务,确认隧道真正可用(而非残留旧地址)。"""
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for attempt in range(6):
            time.sleep(2 + attempt)
            try:
                r = opener.open(url + "/", timeout=8)
                headers, status = r.headers, r.status
            except urllib.error.HTTPError as exc:
                headers, status = exc.headers, exc.code
            except OSError:
                continue
            if headers and headers.get("X-LiteDrop"):
                self.bridge.tunnel_verified.emit(url)
                return
        self._log("隧道自检未通过(经 Cloudflare 无法回环到本机服务),"
                  "已不显示该隧道地址;可停止后重新启动隧道")

    def _on_tunnel_verified(self, url: str):
        self._tunnel_verified_url = url
        self._log("隧道自检通过 ✓")
        self.refresh_channels()

    def _on_tunnel_state(self, state: str):
        if state in ("stopped", "error"):
            self._tunnel_verified_url = None
            self.btn_tunnel.setText("☁ 启动公网隧道")
            self.refresh_channels()

    def _rebuild_combo(self):
        prev = self.combo.currentData()
        self.combo.blockSignals(True)
        self.combo.clear()
        if not self.channels and self.server:
            self.combo.addItem("正在检测通道…", None)
        for name, url, _ in self.channels:
            self.combo.addItem(name, url)
        self.combo.blockSignals(False)
        idx = next((i for i, (_, u, _) in enumerate(self.channels)
                    if u == prev), -1)
        if idx < 0:
            idx = next((i for i, (n, _, _) in enumerate(self.channels)
                        if "隧道" in n), 0 if self.channels else -1)
        if 0 <= idx < self.combo.count():
            self.combo.setCurrentIndex(idx)
        self._update_qr()

    def _update_qr(self):
        if not self.server:
            self.qr_label.setText("服务未启动")
            self.qr_label.setPixmap(QPixmap())
            self.url_edit.clear()
            self.channel_hint.setText(" ")
            return
        url = self.combo.currentData()
        if not url:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText("暂无可用地址")
            self.url_edit.clear()
            self.channel_hint.setText(" ")
            return
        pm = make_qr_pixmap(url)
        if pm:
            self.qr_label.setText("")
            self.qr_label.setPixmap(pm)
        self.url_edit.setText(url)
        idx = self.combo.currentIndex()
        hint = self.channels[idx][2] if 0 <= idx < len(self.channels) else ""
        self.channel_hint.setText(hint)

    def _copy_url(self):
        url = self.url_edit.text()
        if url:
            QApplication.clipboard().setText(url)
            self.statusBar().showMessage("连接地址已复制", 2000)

    # ------------------------------------------------------------- 隧道/防火墙
    def _toggle_tunnel(self):
        if not self.server:
            self._log("请先启动服务再开隧道")
            return
        if self.tunnel.running:
            self.tunnel.stop()
            self.btn_tunnel.setText("☁ 启动公网隧道")
            self.refresh_channels()
        else:
            self.tunnel.start(self.server.port)
            self.btn_tunnel.setText("☁ 停止隧道")
            self._log("隧道启动中,请稍候…")

    def _firewall(self):
        self._log("正在请求管理员权限添加防火墙入站规则…(如弹出 UAC 请允许)")
        threading.Thread(
            target=lambda: self.bridge.firewall_done.emit(
                channels.add_firewall_rule(self.spin_port.value())),
            daemon=True).start()

    def _on_firewall(self, ok: bool):
        self._log("防火墙规则添加成功 ✓" if ok
                  else "防火墙规则未生效,可手动放行该端口的 TCP 入站")

    # ------------------------------------------------------------- 发送
    def _push_text(self):
        text = self.send_text.toPlainText().strip()
        if not text:
            return
        if not self.state:
            self._log("请先启动服务")
            return
        self.state.push_text(text)
        self.send_text.clear()
        self._log("文本已推送,手机「接收」页可见")

    def _add_files(self):
        if not self.state:
            self._log("请先启动服务")
            return
        files, _ = QFileDialog.getOpenFileNames(self, "选择要发送的文件")
        for path in files:
            entry = self.state.add_file(path)
            self._add_shared_row(entry)
            self._log(f"已加入可下载:{entry['name']}({fmt_size(entry['size'])})")

    def _add_shared_row(self, entry: dict):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 8, 8, 8)
        lay.setSpacing(8)
        name = QLabel(entry["name"])
        name.setToolTip(entry["path"])
        size = QLabel(fmt_size(entry["size"]))
        size.setObjectName("muted")
        btn = QPushButton("✕")
        btn.setFixedSize(26, 26)
        btn.setObjectName("small")
        btn.clicked.connect(lambda: self._remove_shared_id(entry["id"]))
        lay.addWidget(name, 1)
        lay.addWidget(size)
        lay.addWidget(btn)
        it = QListWidgetItem()
        it.setData(Qt.UserRole, entry["id"])
        it.setSizeHint(row.sizeHint() + QSize(0, 6))
        self.shared_list.addItem(it)
        self.shared_list.setItemWidget(it, row)

    def _remove_shared_id(self, fid: int):
        if self.state:
            self.state.remove_file(fid)
        for i in range(self.shared_list.count()):
            if self.shared_list.item(i).data(Qt.UserRole) == fid:
                self.shared_list.takeItem(i)
                break

    def _remove_shared(self):
        for item in self.shared_list.selectedItems():
            self._remove_shared_id(item.data(Qt.UserRole))

    # ------------------------------------------------------------- 接收
    def _drop_hint(self, vbox: QVBoxLayout):
        for i in range(vbox.count()):
            w = vbox.itemAt(i).widget()
            if w and w.objectName() == "empty_hint":
                w.deleteLater()

    def _on_text(self, item: dict):
        self._drop_hint(self.text_vbox)
        row = QWidget()
        lay = QVBoxLayout(row)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        head = QHBoxLayout()
        chip = QLabel(item.get("time", ""))
        chip.setStyleSheet("color:#8ca0c0; font-size:11px; background:transparent;")
        btn = QPushButton("复制")
        btn.setObjectName("small")
        btn.clicked.connect(
            lambda: QApplication.clipboard().setText(item["text"]))
        head.addWidget(chip)
        head.addStretch()
        head.addWidget(btn)
        body = QLabel(item["text"])
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addLayout(head)
        lay.addWidget(body)
        row.setStyleSheet(
            "QWidget{background:#0d1526;border:1px solid #1d2942;"
            "border-radius:12px;}")
        self._insert_animated(self.text_vbox, row)
        if self.chk_autocopy.isChecked():
            QApplication.clipboard().setText(item["text"])
            self.statusBar().showMessage("手机新文本已复制到剪贴板", 2500)
        self.tabs.setCurrentIndex(0)

    def _on_file(self, entry: dict):
        self._drop_hint(self.file_vbox)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)
        ico = QLabel("📄")
        name = QLabel(entry["name"])
        name.setToolTip(entry.get("path", ""))
        size = QLabel(f"{fmt_size(entry['size'])} · {entry.get('time', '')}")
        size.setObjectName("muted")
        btn = QPushButton("打开目录")
        btn.setObjectName("small")
        btn.clicked.connect(self._open_receive_dir)
        lay.addWidget(ico)
        lay.addWidget(name, 1)
        lay.addWidget(size)
        lay.addWidget(btn)
        row.setStyleSheet(
            "QWidget{background:#0d1526;border:1px solid #1d2942;"
            "border-radius:12px;}")
        self._insert_animated(self.file_vbox, row)
        self.tabs.setCurrentIndex(1)
        self._log(f"收到文件:{entry['name']}({fmt_size(entry['size'])})")

    def _insert_animated(self, vbox: QVBoxLayout, widget: QWidget):
        """新条目淡入 + 上滑,让界面有反馈感。"""
        vbox.insertWidget(0, widget)
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", widget)
        anim.setDuration(240)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _open_receive_dir(self):
        d = self.dir_edit.text().strip()
        os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def _dir_changed(self):
        d = self.dir_edit.text().strip()
        if self.state:
            os.makedirs(d, exist_ok=True)
            self.state.receive_dir = d
        self.settings.setValue("receive_dir", d)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择接收目录")
        if d:
            self.dir_edit.setText(d)
            self._dir_changed()

    # ------------------------------------------------------------- 日志/退出
    def _log(self, msg: str):
        from html import escape
        if "✓" in msg or "成功" in msg:
            color = "#34d399"
        elif "失败" in msg or "错误" in msg or "不一致" in msg or "无效" in msg:
            color = "#f87171"
        elif msg.startswith("提示") or "提示:" in msg or "提示:" in msg:
            color = "#fbbf24"
        else:
            color = "#c6d4ee"
        stamp = QTime.currentTime().toString("HH:mm:ss")
        self.log_box.append(
            f'<span style="color:#4a5a7a;">[{stamp}]</span> '
            f'<span style="color:{color};">{escape(msg)}</span>')

    def _quit(self):
        self.settings.sync()
        self._remove_mapping()
        if self.tunnel.running:
            self.tunnel.stop()
        if self.server:
            self.server.stop()
        QApplication.quit()

    def closeEvent(self, event):
        if self.settings.value("minimize_tray", True, type=bool):
            event.ignore()
            self.hide()
            if not self.tray_msg_shown:
                self.tray.showMessage(APP_NAME, "已最小化到托盘,继续接收传输",
                                      QSystemTrayIcon.Information, 2000)
                self.tray_msg_shown = True
        else:
            self._quit()


def main():
    if "--selftest" in sys.argv:
        import time as _time
        recv = os.path.join(os.getcwd(), "selftest-received")
        os.makedirs(recv, exist_ok=True)
        st = TransferState(recv)

        class _Ev:
            def __getattr__(self, name):
                return lambda *a: None

        srv = LiteDropServer(8799, st, _Ev(), PAGE_HTML)
        srv.start()
        print(f"SELFTEST-OK port={srv.port} token={st.token}")
        _time.sleep(1.5)
        srv.stop()
        return

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setStyleSheet(STYLE)
    app.setQuitOnLastWindowClosed(False)
    win = MainWindow()
    win.show()
    QTimer.singleShot(300, win._start_server)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
