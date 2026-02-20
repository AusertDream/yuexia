"""Face 子进程入口"""
from __future__ import annotations
import sys
import multiprocessing as mp
from src.core.bus import AsyncQueueBridge
from src.core.config import load_config
from src.core.logger import get_logger

log = get_logger("face.process")


def face_main(inbound: mp.Queue, outbound: mp.Queue, config_path: str = "config.yaml",
              log_queue: mp.Queue | None = None,
              perc_inbound: mp.Queue | None = None, perc_outbound: mp.Queue | None = None):
    load_config(config_path)
    log.info("Face 进程启动")

    from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel
    from PySide6.QtCore import Qt
    from src.face.main_window import MainWindow
    from src.face.bridge import QueueBridgeThread
    from src.core.message import MessageType

    app = QApplication(sys.argv)
    from src.face.theme import apply_theme
    apply_theme(app)

    # 加载提示框
    loading = QDialog()
    loading.setWindowTitle("月下 AI 助手")
    loading.setFixedSize(280, 100)
    loading.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
    layout = QVBoxLayout(loading)
    label = QLabel("正在初始化，请稍候...")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    loading.show()

    bridge = AsyncQueueBridge(inbound, outbound)
    bridge_thread = QueueBridgeThread(bridge)

    perc_bridge_thread = None
    if perc_inbound and perc_outbound:
        perc_bridge = AsyncQueueBridge(perc_inbound, perc_outbound)
        perc_bridge_thread = QueueBridgeThread(perc_bridge)

    window = MainWindow(bridge_thread, log_queue=log_queue, perc_bridge_thread=perc_bridge_thread)

    def on_message(data: dict):
        if data.get("type") == MessageType.INIT_READY:
            loading.close()
            window.show()

    bridge_thread.message_received.connect(on_message)
    bridge_thread.start()
    if perc_bridge_thread:
        perc_bridge_thread.start()

    app.exec()
    log.info("Face 进程退出")
