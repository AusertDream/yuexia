"""可拖动可缩放的悬浮窗"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QMenu, QWidgetAction, QSlider, QLabel, QDialog,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, QPoint, Signal
from PySide6.QtGui import QColor, QCursor
from pathlib import Path

_EDGE = 8  # 边缘缩放检测区域


class _LiveWebView(QWebEngineView):
    """拦截 WebEngine 默认右键菜单"""
    def contextMenuEvent(self, event):
        event.accept()
        w = self.window()
        if hasattr(w, '_show_context_menu'):
            w._show_context_menu()


class _MoveDialog(QDialog):
    """拖拽控制窗口：按住拖拽区移动 Live2D 模型位置"""
    def __init__(self, js_call, parent=None):
        super().__init__(parent)
        self._js_call = js_call
        self._last_pos = None
        self.setWindowTitle("调整模型位置")
        self.setFixedSize(220, 220)
        layout = QVBoxLayout(self)
        tip = QLabel("按住下方区域拖动\n移动 Live2D 模型")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip)
        self._pad = QWidget()
        self._pad.setFixedSize(180, 150)
        self._pad.setStyleSheet(
            "background: #ddd; border: 2px solid #999; border-radius: 8px;"
        )
        self._pad.setMouseTracking(True)
        self._pad.installEventFilter(self)
        layout.addWidget(self._pad, alignment=Qt.AlignmentFlag.AlignCenter)

    def eventFilter(self, obj, event):
        if obj is not self._pad:
            return False
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = event.globalPosition().toPoint()
            return True
        if event.type() == QEvent.Type.MouseMove and self._last_pos is not None:
            cur = event.globalPosition().toPoint()
            dx = cur.x() - self._last_pos.x()
            dy = cur.y() - self._last_pos.y()
            self._last_pos = cur
            self._js_call(f"moveModel({dx},{dy})")
            return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            self._last_pos = None
            return True
        return False


class FloatingWidget(QWidget):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = None
        self._model_scale = 1.0
        self._stay_on_top = True
        self._transparent_bg = True
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
        self.setStyleSheet("FloatingWidget { border: 1px solid white; border-radius: 6px; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        # 顶部控制栏
        bar = QHBoxLayout()
        bar.setContentsMargins(8, 4, 4, 0)

        drag_area = QWidget()
        drag_area.setFixedHeight(24)
        drag_area.setStyleSheet("background: white; border-radius: 4px;")
        bar.addWidget(drag_area, stretch=1)

        _BTN_SS = (
            "QPushButton[floatBtn='true'] { background: white; color: #333; "
            "border: none; font-size: 14px; border-radius: 4px; padding: 0; }"
            "QPushButton[floatBtn='true']:hover { background: #ddd; }"
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
        self.web_view = _LiveWebView()
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

    # --- 右键菜单 ---
    def _show_context_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2a2a3e; color: #eee; border: 1px solid #444; "
            "border-radius: 6px; padding: 4px; font-size: 13px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; }"
            "QMenu::item:selected { background: #4a4a6e; }"
            "QMenu::separator { height: 1px; background: #444; margin: 4px 8px; }"
        )

        # 缩放滑块
        scale_w = QWidget()
        sl = QHBoxLayout(scale_w)
        sl.setContentsMargins(12, 4, 12, 4)
        lbl = QLabel("缩放")
        lbl.setStyleSheet("color: #eee; font-size: 13px;")
        slider = QSlider(Qt.Orientation.Horizontal)
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
        wa.setDefaultWidget(scale_w)
        menu.addAction(wa)

        menu.addSeparator()

        # 背景透明
        bg_act = menu.addAction("✓ 背景透明" if self._transparent_bg else "  背景透明")
        bg_act.triggered.connect(self._toggle_bg)

        # 置顶
        top_act = menu.addAction("✓ 置顶" if self._stay_on_top else "  置顶")
        top_act.triggered.connect(self._toggle_top)

        # 重置
        menu.addAction("重置位置").triggered.connect(self._reset_model)

        # 调整位置
        menu.addAction("调整位置").triggered.connect(self._open_move_dialog)

        menu.addSeparator()
        menu.addAction("退出").triggered.connect(self.close)

        menu.exec(QCursor.pos())

    def _set_scale(self, s):
        self._model_scale = s
        self.js_call(f"setModelScale({s})")

    def _reset_model(self):
        self._model_scale = 1.0
        self.js_call("resetModel()")

    def _toggle_bg(self):
        self._transparent_bg = not self._transparent_bg
        bg = "transparent" if self._transparent_bg else "#1a1a2e"
        self.js_call(f"setBackground('{bg}')")

    def _open_move_dialog(self):
        dlg = _MoveDialog(self.js_call, self)
        dlg.exec()

    def _toggle_top(self):
        self._stay_on_top = not self._stay_on_top
        flags = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                 | (Qt.WindowType.WindowStaysOnTopHint if self._stay_on_top else Qt.WindowType(0)))
        pos = self.pos()
        self.setWindowFlags(flags)
        self.move(pos)
        self.show()

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
