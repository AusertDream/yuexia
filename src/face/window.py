"""PySide6 双模式窗口：窗口模式 / 桌宠模式"""
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLineEdit,
    QMenu, QWidgetAction, QSlider, QLabel, QHBoxLayout,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, Slot, QPoint
from PySide6.QtGui import QColor, QAction, QCursor
from pathlib import Path
from src.core.message import Message, MessageType
from src.core.config import get
from src.core.logger import get_logger
from src.face.bridge import QueueBridgeThread
import threading, http.server, functools

log = get_logger("face.window")
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _start_asset_server() -> int:
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(_PROJECT_ROOT),
    )
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return port


class _LiveWebView(QWebEngineView):
    """拦截 WebEngine 默认右键菜单，改用自定义菜单"""
    def contextMenuEvent(self, event):
        self.window()._show_menu()


class FaceWindow(QMainWindow):
    def __init__(self, bridge_thread: QueueBridgeThread):
        super().__init__()
        self.bridge_thread = bridge_thread
        self._pet_mode = False
        self._stay_on_top = True
        self._drag_pos = None
        self._model_scale = 1.0
        self._w = get("face.width", 400)
        self._h = get("face.height", 600)
        self._port = _start_asset_server()
        self._setup_window()
        self._setup_ui()
        self._connect_signals()

    # ── 窗口设置 ──
    def _setup_window(self):
        self.resize(self._w, self._h)
        self.setMinimumSize(200, 300)
        self.setWindowTitle("月下")
        self._apply_window_mode()

    def _apply_window_mode(self):
        was_visible = self.isVisible()
        pos = self.pos()
        if self._pet_mode:
            flags = Qt.FramelessWindowHint | Qt.Tool
            if self._stay_on_top:
                flags |= Qt.WindowStaysOnTopHint
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setStyleSheet("")
        else:
            flags = Qt.Window
            if self._stay_on_top:
                flags |= Qt.WindowStaysOnTopHint
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setStyleSheet("QMainWindow { background: #1a1a2e; }")
        if was_visible:
            self.move(pos)
            self.show()

    # ── UI 构建 ──
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.web_view = _LiveWebView()
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.web_view.setUrl(
            QUrl(f"http://127.0.0.1:{self._port}/src/face/web/index.html")
        )
        layout.addWidget(self.web_view, stretch=1)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入消息...")
        self.input_box.setStyleSheet(
            "QLineEdit { background: rgba(30,30,40,200); color: white; "
            "border: 1px solid #555; border-radius: 8px; padding: 6px; "
            "font-size: 14px; margin: 4px; }"
        )
        self.input_box.returnPressed.connect(self._on_send)
        layout.addWidget(self.input_box)

    # ── 右键菜单 ──
    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2a2a3e; color: #eee; border: 1px solid #444; "
            "border-radius: 6px; padding: 4px; font-size: 13px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; }"
            "QMenu::item:selected { background: #4a4a6e; }"
            "QMenu::separator { height: 1px; background: #444; margin: 4px 8px; }"
        )

        # 桌宠模式切换
        pet_text = "窗口模式" if self._pet_mode else "桌宠模式"
        pet_act = menu.addAction(pet_text)
        pet_act.triggered.connect(self._toggle_pet_mode)

        menu.addSeparator()

        # 缩放滑块
        scale_widget = QWidget()
        sl = QHBoxLayout(scale_widget)
        sl.setContentsMargins(12, 4, 12, 4)
        lbl = QLabel("缩放")
        lbl.setStyleSheet("color: #eee; font-size: 13px;")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(30, 250)
        slider.setValue(int(self._model_scale * 100))
        slider.setFixedWidth(120)
        slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 4px; background: #555; border-radius: 2px; }"
            "QSlider::handle:horizontal { width: 12px; margin: -4px 0; "
            "background: #8888cc; border-radius: 6px; }"
        )
        val_lbl = QLabel(f"{int(self._model_scale * 100)}%")
        val_lbl.setStyleSheet("color: #aaa; font-size: 12px; min-width: 36px;")
        slider.valueChanged.connect(
            lambda v: (val_lbl.setText(f"{v}%"), self._set_scale(v / 100))
        )
        sl.addWidget(lbl)
        sl.addWidget(slider)
        sl.addWidget(val_lbl)
        wa = QWidgetAction(menu)
        wa.setDefaultWidget(scale_widget)
        menu.addAction(wa)

        menu.addSeparator()

        # 置顶
        top_act = menu.addAction("✓ 置顶" if self._stay_on_top else "  置顶")
        top_act.triggered.connect(self._toggle_top)

        # 重置
        reset_act = menu.addAction("重置位置")
        reset_act.triggered.connect(self._reset_model)

        menu.addSeparator()

        # 退出
        quit_act = menu.addAction("退出")
        quit_act.triggered.connect(self.close)

        menu.exec(QCursor.pos())

    # ── 菜单动作 ──
    def _toggle_pet_mode(self):
        self._pet_mode = not self._pet_mode
        self._apply_window_mode()
        bg = "transparent" if self._pet_mode else "#1a1a2e"
        self._js_call(f"setBackground('{bg}')")
        self.input_box.setVisible(not self._pet_mode)

    def _toggle_top(self):
        self._stay_on_top = not self._stay_on_top
        self._apply_window_mode()

    def _set_scale(self, s):
        self._model_scale = s
        self._js_call(f"setModelScale({s})")

    def _reset_model(self):
        self._model_scale = 1.0
        self._js_call("resetModel()")

    # ── 窗口大小变化 → 通知 JS ──
    def resizeEvent(self, event):
        super().resizeEvent(event)
        s = self.web_view.size()
        self._js_call(f"resizeCanvas({s.width()},{s.height()})")

    # ── 桌宠模式拖拽 ──
    def mousePressEvent(self, event):
        if self._pet_mode and event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pet_mode and self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ── 消息通信 ──
    def _connect_signals(self):
        self.bridge_thread.message_received.connect(self._on_message)
        self.bridge_thread.start()

    def _on_send(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self.bridge_thread.send(Message(
            type=MessageType.USER_TEXT_INPUT,
            source="face", target="brain",
            payload={"text": text},
        ))
        self._js_call(f"addMessage('user', {self._js_str(text)})")

    @Slot(dict)
    def _on_message(self, data: dict):
        msg = Message(**data)
        if msg.type == MessageType.LLM_STREAM_CHUNK:
            chunk = msg.payload.get("text", "")
            self._js_call(f"appendChunk({self._js_str(chunk)})")
        elif msg.type == MessageType.LLM_STREAM_END:
            self._js_call("endStream()")
        elif msg.type == MessageType.EXPRESSION_UPDATE:
            emotion = msg.payload.get("emotion", "neutral")
            self._js_call(f"setEmotion('{emotion}')")
        elif msg.type == MessageType.TTS_DONE:
            audio_path = msg.payload.get("path", "")
            self._js_call(f"playAudio({self._js_str(audio_path)})")

    def _js_call(self, code: str):
        self.web_view.page().runJavaScript(code)

    def _js_str(self, s: str) -> str:
        escaped = s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        return f"'{escaped}'"

    def closeEvent(self, event):
        self.bridge_thread.send(Message(
            type=MessageType.SHUTDOWN,
            source="face", target="brain",
        ))
        self.bridge_thread.stop()
        super().closeEvent(event)
