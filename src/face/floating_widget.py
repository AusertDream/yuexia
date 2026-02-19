"""可拖动可缩放的悬浮窗"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, QPoint, Signal
from PySide6.QtGui import QColor, QCursor
from pathlib import Path

_EDGE = 8  # 边缘缩放检测区域


class FloatingWidget(QWidget):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = None
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(200, 300)
        self.resize(400, 600)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部控制栏
        bar = QHBoxLayout()
        bar.setContentsMargins(8, 4, 4, 0)

        drag_area = QWidget()
        drag_area.setFixedHeight(24)
        drag_area.setStyleSheet("background: rgba(30,30,40,180); border-radius: 4px;")
        bar.addWidget(drag_area, stretch=1)

        _BTN_SS = (
            "QPushButton[floatBtn='true'] { background: rgba(30,30,40,180); color: white; "
            "border: none; font-size: 14px; border-radius: 4px; padding: 0; }"
            "QPushButton[floatBtn='true']:hover { background: rgba(80,80,100,200); }"
        )
        for text, slot in [("—", self._on_minimize), ("×", self.close)]:
            btn = QPushButton(text)
            btn.setProperty("floatBtn", True)
            btn.setFixedSize(28, 24)
            btn.setStyleSheet(_BTN_SS)
            btn.clicked.connect(slot)
            bar.addWidget(btn)

        layout.addLayout(bar)

        # WebView
        self.web_view = QWebEngineView()
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        web_path = Path(__file__).parent / "web" / "index.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(web_path)))
        layout.addWidget(self.web_view, stretch=1)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def _on_minimize(self):
        self.showMinimized()

    def js_call(self, code: str):
        self.web_view.page().runJavaScript(code)

    # --- 拖动 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._detect_edge(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._drag_pos = event.globalPosition().toPoint()
            elif event.position().y() < 30:
                self._drag_pos = event.globalPosition().toPoint() - self.pos()
            else:
                self._drag_pos = None

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._resizing and self._drag_pos is not None:
            self._do_resize(event.globalPosition().toPoint())
            return
        if self._drag_pos is not None and not self._resizing:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            return
        # 更新光标
        edge = self._detect_edge(pos)
        if edge in ("right", "bottom"):
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor if edge == "bottom" else Qt.CursorShape.SizeHorCursor))
        elif edge == "corner":
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = None

    def _detect_edge(self, pos: QPoint) -> str | None:
        w, h = self.width(), self.height()
        at_right = pos.x() >= w - _EDGE
        at_bottom = pos.y() >= h - _EDGE
        if at_right and at_bottom:
            return "corner"
        if at_right:
            return "right"
        if at_bottom:
            return "bottom"
        return None

    def _do_resize(self, global_pos: QPoint):
        delta = global_pos - self._drag_pos
        self._drag_pos = global_pos
        geo = self.geometry()
        if self._resize_edge in ("right", "corner"):
            geo.setWidth(max(self.minimumWidth(), geo.width() + delta.x()))
        if self._resize_edge in ("bottom", "corner"):
            geo.setHeight(max(self.minimumHeight(), geo.height() + delta.y()))
        self.setGeometry(geo)
