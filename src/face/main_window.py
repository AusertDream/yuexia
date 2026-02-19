"""主应用窗口"""
from __future__ import annotations
import multiprocessing as mp
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QStackedWidget, QListWidgetItem,
    QPushButton, QMenu, QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Slot, QUrl
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.core.message import Message, MessageType
from src.core.config import get
from src.core.logger import get_logger
from src.face.bridge import QueueBridgeThread
from src.face.pages import ChatPage, SettingsPage, ConsolePage, VisionPage
from src.face.floating_widget import FloatingWidget

log = get_logger("face.main_window")

_NAV_ITEMS = ["💬 对话", "⚙ 设置", "📋 控制台", "👁 视觉"]


class MainWindow(QMainWindow):
    def __init__(self, bridge_thread: QueueBridgeThread, log_queue: mp.Queue | None = None,
                 perc_bridge_thread: QueueBridgeThread | None = None):
        super().__init__()
        self.bridge_thread = bridge_thread
        self.perc_bridge_thread = perc_bridge_thread
        self.log_queue = log_queue
        self.floating = None
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._setup_window()
        self._setup_pages()
        self._setup_ui()
        self._connect_signals()
        if log_queue:
            self._start_log_reader()

    def _setup_window(self):
        w = get("face.main_window.width", 900)
        h = get("face.main_window.height", 650)
        self.setWindowTitle("月下 AI 助手")
        self.resize(w, h)

    def _setup_pages(self):
        self.chat_page = ChatPage(send_callback=self._send_msg, mic_callback=self._on_mic_from_chat,
                                   play_callback=self._play_tts)
        self.settings_page = SettingsPage()
        self.console_page = ConsolePage()
        self.vision_page = VisionPage()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶部导航栏
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(4, 2, 4, 2)
        self._nav_btns: list[QPushButton] = []
        for i, label in enumerate(_NAV_ITEMS):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.clicked.connect(lambda checked, idx=i: self._on_nav(idx))
            nav_bar.addWidget(btn)
            self._nav_btns.append(btn)
        nav_bar.addStretch()
        self.float_btn = QPushButton("悬浮窗")
        self.float_btn.setCheckable(True)
        self.float_btn.toggled.connect(self._toggle_floating)
        nav_bar.addWidget(self.float_btn)
        root.addLayout(nav_bar)

        # 下方内容区
        body = QHBoxLayout()
        body.setSpacing(0)

        # 左侧会话面板
        left = QWidget()
        left.setFixedWidth(160)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        self.new_chat_btn = QPushButton("+ 新对话")
        self.new_chat_btn.clicked.connect(self._on_new_chat)
        left_layout.addWidget(self.new_chat_btn)
        self.session_list = QListWidget()
        self.session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._on_session_context_menu)
        self.session_list.currentItemChanged.connect(self._on_session_switch)
        left_layout.addWidget(self.session_list, stretch=1)
        body.addWidget(left)

        # 右侧页面栈
        self.stack = QStackedWidget()
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.console_page)
        self.stack.addWidget(self.vision_page)
        body.addWidget(self.stack, stretch=1)
        root.addLayout(body, stretch=1)

    def _connect_signals(self):
        self.bridge_thread.message_received.connect(self._dispatch)
        self.bridge_thread.start()
        if self.perc_bridge_thread:
            self.perc_bridge_thread.message_received.connect(self._dispatch_perc)
            self.perc_bridge_thread.start()
        self.settings_page.mic_test_requested.connect(self._on_mic_test)
        self.settings_page.config_saved.connect(self._on_config_saved)
        # PTT 快捷键
        self._ptt_active = False
        ptt_key = get("perception.asr.ptt_key", "ctrl+`")
        shortcut = QShortcut(QKeySequence(ptt_key), self)
        shortcut.activated.connect(self._toggle_ptt)

    def _on_nav(self, index: int):
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)

    def _send_msg(self, msg: Message):
        self.bridge_thread.send(msg)

    def _toggle_floating(self, checked: bool):
        if checked:
            if not self.floating:
                self.floating = FloatingWidget()
                self.floating.closed.connect(lambda: self.float_btn.setChecked(False))
            self.floating.show()
        elif self.floating:
            self.floating.hide()

    @Slot(dict)
    def _dispatch(self, data: dict):
        msg = Message(**data)
        if msg.type == MessageType.LLM_STREAM_CHUNK:
            chunk = msg.payload.get("text", "")
            self.chat_page.on_stream_chunk(chunk)
            if self.floating:
                self.floating.js_call(f"appendChunk({self._js_str(chunk)})")
        elif msg.type == MessageType.LLM_STREAM_END:
            msg_index = msg.payload.get("msg_index", -1)
            self.chat_page.on_stream_end(msg_index)
            if self.floating:
                self.floating.js_call("endStream()")
        elif msg.type == MessageType.EXPRESSION_UPDATE:
            emotion = msg.payload.get("emotion", "neutral")
            if self.floating:
                self.floating.js_call(f"setEmotion('{emotion}')")
        elif msg.type == MessageType.TTS_DONE:
            audio = msg.payload.get("path", "")
            msg_index = msg.payload.get("msg_index", -1)
            if audio:
                self._player.setSource(QUrl.fromLocalFile(audio))
                self._player.play()
            self.chat_page.set_tts_path(msg_index, audio)
            if self.floating:
                self.floating.js_call(f"playAudio({self._js_str(audio)})")
        elif msg.type == MessageType.SCREENSHOT_MEMORY:
            path = msg.payload.get("path", "")
            self.vision_page.update_screenshot(path)
        elif msg.type == MessageType.ASR_TEXT_DISPLAY:
            text = msg.payload.get("text", "")
            self.chat_page._add_message("user", f"🎤 {text}")
        elif msg.type == MessageType.SESSION_LIST:
            self._update_session_list(
                msg.payload.get("sessions", []),
                msg.payload.get("current_id", ""),
            )
        elif msg.type == MessageType.SESSION_LOADED:
            self.chat_page.load_history(msg.payload.get("messages", []))
            self.stack.setCurrentIndex(0)

    def _send_perc(self, msg: Message):
        if self.perc_bridge_thread:
            self.perc_bridge_thread.send(msg)

    @Slot(dict)
    def _dispatch_perc(self, data: dict):
        msg = Message(**data)
        if msg.type == MessageType.MIC_TEST_RESULT:
            path = msg.payload.get("path", "")
            log.info(f"麦克风测试结果: {path}")

    def _on_mic_test(self):
        self._send_perc(Message(
            type=MessageType.MIC_TEST_REQUEST,
            source="face", target="perception",
        ))

    def _on_config_saved(self):
        from src.core.config import reload_config
        reload_config()
        reload_msg = Message(type=MessageType.CONFIG_RELOAD, source="face")
        self.bridge_thread.send(reload_msg)
        self._send_perc(reload_msg)

    def _play_tts(self, path: str):
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def _on_new_chat(self):
        self._send_msg(Message(
            type=MessageType.SESSION_CREATE,
            source="face", target="brain",
        ))

    def _on_session_switch(self, current, previous):
        if not current:
            return
        sid = current.data(Qt.ItemDataRole.UserRole)
        if sid:
            self._send_msg(Message(
                type=MessageType.SESSION_SWITCH,
                source="face", target="brain",
                payload={"session_id": sid},
            ))

    def _update_session_list(self, sessions: list[dict], current_id: str = ""):
        self.session_list.blockSignals(True)
        self.session_list.clear()
        for s in sessions:
            item = QListWidgetItem(s.get("title", "新对话"))
            item.setData(Qt.ItemDataRole.UserRole, s["id"])
            self.session_list.addItem(item)
            if s["id"] == current_id:
                self.session_list.setCurrentItem(item)
        self.session_list.blockSignals(False)

    def _on_session_context_menu(self, pos):
        item = self.session_list.itemAt(pos)
        if not item:
            return
        sid = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename_act = menu.addAction("重命名")
        delete_act = menu.addAction("删除")
        action = menu.exec(self.session_list.mapToGlobal(pos))
        if action == rename_act:
            title, ok = QInputDialog.getText(self, "重命名", "新名称:", text=item.text())
            if ok and title.strip():
                self._send_msg(Message(
                    type=MessageType.SESSION_RENAME,
                    source="face", target="brain",
                    payload={"session_id": sid, "title": title.strip()},
                ))
        elif action == delete_act:
            if QMessageBox.question(self, "删除", f"确定删除「{item.text()}」？") == QMessageBox.StandardButton.Yes:
                self._send_msg(Message(
                    type=MessageType.SESSION_DELETE,
                    source="face", target="brain",
                    payload={"session_id": sid},
                ))

    def _toggle_ptt(self):
        self._ptt_active = not self._ptt_active
        self._set_ptt(self._ptt_active)

    def _on_mic_from_chat(self, active: bool):
        self._ptt_active = active
        self._set_ptt(active)

    def _set_ptt(self, active: bool):
        msg_type = MessageType.MIC_START_RECORDING if active else MessageType.MIC_STOP_RECORDING
        self._send_perc(Message(type=msg_type, source="face", target="perception"))
        self.chat_page.set_recording(active)
        log.info(f"PTT {'开始' if active else '停止'}录音")

    def _js_str(self, s: str) -> str:
        escaped = s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        return f"'{escaped}'"

    def _start_log_reader(self):
        from src.face._log_reader import LogReaderThread
        self._log_thread = LogReaderThread(self.log_queue)
        self._log_thread.log_line.connect(self.console_page.append_log)
        self._log_thread.start()

    def closeEvent(self, event):
        self.bridge_thread.send(Message(
            type=MessageType.SHUTDOWN,
            source="face", target="brain",
        ))
        self.bridge_thread.stop()
        if self.perc_bridge_thread:
            self.perc_bridge_thread.stop()
        self.settings_page.cleanup()
        if self.floating:
            self.floating.close()
        if hasattr(self, '_log_thread'):
            self._log_thread.stop()
        super().closeEvent(event)
