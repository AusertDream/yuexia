"""对话页面 - QQ 风格气泡"""
from __future__ import annotations
import dataclasses
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QStyledItemDelegate,
)
from PySide6.QtCore import Qt, QRect, QSize, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPainterPath
from src.core.message import Message, MessageType

_USER_BG = QColor(0xF4, 0x8F, 0xB1)
_AI_BG = QColor(0xFF, 0xFF, 0xFF)
_USER_FG = QColor(0xFF, 0xFF, 0xFF)
_AI_FG = QColor(0x37, 0x47, 0x4F)
_RADIUS = 12
_PAD = 10
_MARGIN = 8
_MAX_W_RATIO = 0.65
_FONT = QFont("Microsoft YaHei", 10)
_PLAY_SIZE = 24


@dataclasses.dataclass
class ChatMessage:
    role: str  # "user" | "ai"
    text: str
    msg_index: int = -1
    tts_path: str = ""


def _calc_text_rect(text: str, max_w: int) -> QRect:
    fm = QFontMetrics(_FONT)
    return fm.boundingRect(QRect(0, 0, max_w - 2 * _PAD, 100000), Qt.TextFlag.TextWordWrap, text)


class BubbleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, play_callback=None):
        super().__init__(parent)
        self._play_cb = play_callback

    def paint(self, painter: QPainter, option, index):
        msg: ChatMessage = index.data(Qt.ItemDataRole.UserRole)
        if not msg:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        lw = option.rect.width()
        max_bw = int(lw * _MAX_W_RATIO)
        tr = _calc_text_rect(msg.text, max_bw)
        bw = tr.width() + 2 * _PAD
        bh = tr.height() + 2 * _PAD
        is_user = msg.role == "user"

        y = option.rect.top() + 4
        x = (lw - bw - _MARGIN) if is_user else _MARGIN
        bubble = QRectF(x, y, bw, bh)

        path = QPainterPath()
        path.addRoundedRect(bubble, _RADIUS, _RADIUS)
        painter.fillPath(path, _USER_BG if is_user else _AI_BG)
        if not is_user:
            painter.setPen(QColor(0xF8, 0xBB, 0xD0))
            painter.drawPath(path)

        painter.setFont(_FONT)
        painter.setPen(_USER_FG if is_user else _AI_FG)
        painter.drawText(QRectF(x + _PAD, y + _PAD, tr.width(), tr.height()),
                         Qt.TextFlag.TextWordWrap, msg.text)
        # 播放按钮
        if not is_user and msg.tts_path:
            btn_x = x + bw + 4
            btn_y = y + (bh - _PLAY_SIZE) / 2
            painter.setPen(QColor(0x90, 0x90, 0x90))
            painter.setFont(QFont("Segoe UI Emoji", 11))
            painter.drawText(QRectF(btn_x, btn_y, _PLAY_SIZE, _PLAY_SIZE),
                             Qt.AlignmentFlag.AlignCenter, "\u25b6")
        painter.restore()

    def editorEvent(self, event, model, option, index):
        from PySide6.QtCore import QEvent, QPointF
        if event.type() != QEvent.Type.MouseButtonRelease:
            return super().editorEvent(event, model, option, index)
        msg: ChatMessage = index.data(Qt.ItemDataRole.UserRole)
        if not msg or msg.role == "user" or not msg.tts_path:
            return False
        lw = option.rect.width()
        max_bw = int(lw * _MAX_W_RATIO)
        tr = _calc_text_rect(msg.text, max_bw)
        bw = tr.width() + 2 * _PAD
        bh = tr.height() + 2 * _PAD
        y = option.rect.top() + 4
        x = _MARGIN
        btn_rect = QRectF(x + bw + 4, y + (bh - _PLAY_SIZE) / 2, _PLAY_SIZE, _PLAY_SIZE)
        pos = event.position() if hasattr(event, 'position') else QPointF(event.pos())
        if btn_rect.contains(pos) and self._play_cb:
            self._play_cb(msg.tts_path)
            return True
        return False

    def sizeHint(self, option, index) -> QSize:
        msg: ChatMessage = index.data(Qt.ItemDataRole.UserRole)
        if not msg:
            return QSize(0, 40)
        lw = option.rect.width() or 600
        tr = _calc_text_rect(msg.text, int(lw * _MAX_W_RATIO))
        return QSize(lw, tr.height() + 2 * _PAD + 8)


class ChatPage(QWidget):
    def __init__(self, send_callback=None, mic_callback=None, play_callback=None):
        super().__init__()
        self._send = send_callback
        self._mic_cb = mic_callback
        self._play_cb = play_callback
        self._streaming_item: QListWidgetItem | None = None
        self._streaming_text = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.list_widget = QListWidget()
        self.list_widget.setItemDelegate(BubbleDelegate(self.list_widget, play_callback=self._play_cb))
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.list_widget, stretch=1)

        bar = QHBoxLayout()
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedWidth(40)
        self.mic_btn.setCheckable(True)
        self.mic_btn.toggled.connect(self._on_mic_toggle)
        bar.addWidget(self.mic_btn)
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入消息...")
        self.input.returnPressed.connect(self._on_send)
        bar.addWidget(self.input)
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedWidth(60)
        self.send_btn.clicked.connect(self._on_send)
        bar.addWidget(self.send_btn)
        layout.addLayout(bar)

    def _add_message(self, role: str, text: str) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, ChatMessage(role=role, text=text))
        self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()
        return item

    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._add_message("user", text)
        if self._send:
            self._send(Message(
                type=MessageType.USER_TEXT_INPUT,
                source="face", target="brain",
                payload={"text": text},
            ))

    def on_stream_chunk(self, chunk: str):
        self._streaming_text += chunk
        if not self._streaming_item:
            self._streaming_item = self._add_message("ai", self._streaming_text)
        else:
            self._streaming_item.setData(
                Qt.ItemDataRole.UserRole,
                ChatMessage(role="ai", text=self._streaming_text),
            )
            self.list_widget.doItemsLayout()
            self.list_widget.scrollToBottom()

    def on_stream_end(self, msg_index: int = -1):
        if self._streaming_item and msg_index >= 0:
            cm = self._streaming_item.data(Qt.ItemDataRole.UserRole)
            cm.msg_index = msg_index
            self._streaming_item.setData(Qt.ItemDataRole.UserRole, cm)
        self._streaming_item = None
        self._streaming_text = ""

    def set_tts_path(self, msg_index: int, path: str):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            cm: ChatMessage = item.data(Qt.ItemDataRole.UserRole)
            if cm and cm.msg_index == msg_index:
                cm.tts_path = path
                item.setData(Qt.ItemDataRole.UserRole, cm)
                self.list_widget.doItemsLayout()
                break

    def load_history(self, messages: list[dict]):
        self.list_widget.clear()
        self._streaming_item = None
        self._streaming_text = ""
        for i, m in enumerate(messages):
            role = "user" if m["role"] == "user" else "ai"
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, ChatMessage(
                role=role, text=m.get("content", ""),
                msg_index=i, tts_path=m.get("tts_path", ""),
            ))
            self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()

    def _on_mic_toggle(self, checked: bool):
        self.set_recording(checked)
        if self._mic_cb:
            self._mic_cb(checked)

    def set_recording(self, active: bool):
        self.mic_btn.blockSignals(True)
        self.mic_btn.setChecked(active)
        self.mic_btn.blockSignals(False)
        if active:
            self.mic_btn.setStyleSheet("background:#c62828;color:white;border-radius:6px;")
            self.mic_btn.setText("⏹")
        else:
            self.mic_btn.setStyleSheet("")
            self.mic_btn.setText("🎤")
