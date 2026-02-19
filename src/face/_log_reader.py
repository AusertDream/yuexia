"""从 mp.Queue 读取日志行的 QThread"""
import multiprocessing as mp
from PySide6.QtCore import QThread, Signal


class LogReaderThread(QThread):
    log_line = Signal(str)

    def __init__(self, queue: mp.Queue, parent=None):
        super().__init__(parent)
        self._queue = queue
        self._running = True

    def run(self):
        while self._running:
            try:
                record = self._queue.get(timeout=0.1)
                self.log_line.emit(str(record))
            except Exception:
                pass

    def stop(self):
        self._running = False
        self.wait()
