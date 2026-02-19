"""视觉预览页面 - 显示最新截图"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


class VisionPage(QWidget):
    def __init__(self):
        super().__init__()
        self._original_pixmap = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.image_label = QLabel("等待截图...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.image_label)

    def update_screenshot(self, path: str):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._original_pixmap = pixmap
            self._rescale()

    def _rescale(self):
        if not self._original_pixmap:
            return
        scaled = self._original_pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()
