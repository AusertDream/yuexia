"""QThread 轮询 mp.Queue，emit Signal 到 GUI 线程"""
from PySide6.QtCore import QThread, Signal
from src.core.bus import AsyncQueueBridge
from src.core.message import Message


class QueueBridgeThread(QThread):
    message_received = Signal(dict)  # 发射 Message.model_dump()

    def __init__(self, bridge: AsyncQueueBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self._running = True

    def run(self):
        while self._running:
            msg = self.bridge.recv_sync(timeout=0.05)
            if msg:
                self.message_received.emit(msg.model_dump())

    def stop(self):
        self._running = False
        self.wait()

    def send(self, msg: Message):
        self.bridge.send_sync(msg)
