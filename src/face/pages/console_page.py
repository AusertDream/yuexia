"""控制台页面 - 实时显示日志"""
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import Signal, QObject


class _LogSignal(QObject):
    log_received = Signal(str)


class QtLogHandler(logging.Handler):
    """接收日志并通过 Signal 转发到 GUI"""
    def __init__(self):
        super().__init__()
        self._signal = _LogSignal()
        self.setFormatter(logging.Formatter(
            "[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        ))

    @property
    def log_received(self):
        return self._signal.log_received

    def emit(self, record):
        self._signal.log_received.emit(self.format(record))


class ConsolePage(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._handler = QtLogHandler()
        self._handler.log_received.connect(self._append)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(2000)
        layout.addWidget(self.console)

    @property
    def handler(self) -> QtLogHandler:
        return self._handler

    def _append(self, text: str):
        self.console.appendPlainText(text)

    def append_log(self, text: str):
        """供外部直接追加日志文本"""
        self.console.appendPlainText(text)
