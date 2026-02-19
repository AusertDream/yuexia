"""PySide6 无边框透明窗口"""
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLineEdit
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtGui import QColor
from pathlib import Path
from src.core.message import Message, MessageType
from src.core.config import get
from src.core.logger import get_logger
from src.face.bridge import QueueBridgeThread

log = get_logger("face.window")


class FaceWindow(QMainWindow):
    def __init__(self, bridge_thread: QueueBridgeThread):
        super().__init__()
        self.bridge_thread = bridge_thread
        self._setup_window()
        self._setup_ui()
        self._connect_signals()

    def _setup_window(self):
        w = get("face.width", 400)
        h = get("face.height", 600)
        self.setFixedSize(w, h)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # WebView 渲染角色
        self.web_view = QWebEngineView()
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        web_path = Path(__file__).parent / "web" / "index.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(web_path)))
        layout.addWidget(self.web_view, stretch=1)

        # 文本输入框
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入消息...")
        self.input_box.setStyleSheet(
            "QLineEdit { background: rgba(30,30,40,200); color: white; "
            "border: 1px solid #555; border-radius: 8px; padding: 6px; font-size: 14px; }"
        )
        self.input_box.returnPressed.connect(self._on_send)
        layout.addWidget(self.input_box)

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
