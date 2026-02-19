"""Brain 主控逻辑"""
import asyncio
import re
from src.core.message import Message, MessageType
from src.core.bus import AsyncQueueBridge, MessageRouter
from src.core.config import get
from src.core.logger import get_logger
from src.brain.engine import LLMEngine, create_engine
from src.brain.memory import Memory
from src.brain.prompt import PromptManager
from src.brain.diary import DiaryWriter
from src.brain.session import SessionManager

log = get_logger("brain")


class Brain:
    def __init__(
        self,
        face_bridge: AsyncQueueBridge,
        perception_bridge: AsyncQueueBridge,
        action_bridge: AsyncQueueBridge,
    ):
        self.face = face_bridge
        self.perception = perception_bridge
        self.action = action_bridge
        self.router = MessageRouter()
        self.history: list[dict] = []
        self.engine: LLMEngine | None = None
        self.memory: Memory | None = None
        self.prompt_mgr: PromptManager | None = None
        self.diary: DiaryWriter | None = None
        self.latest_screenshot: str | None = None
        self.session_mgr = SessionManager()

    async def run(self):
        log.info("Brain 启动中...")
        self.engine = create_engine()
        self.memory = Memory()
        self.prompt_mgr = PromptManager()
        self.diary = DiaryWriter()

        # 注册桥接
        self.router.add_bridge(self.face)
        self.router.add_bridge(self.perception)
        self.router.add_bridge(self.action)

        # 注册消息处理
        self.router.on(MessageType.USER_TEXT_INPUT, self._on_user_text)
        self.router.on(MessageType.ASR_RESULT, self._on_asr_result)
        self.router.on(MessageType.SCREENSHOT, self._on_screenshot)
        self.router.on(MessageType.SCREENSHOT_MEMORY, self._on_screenshot_memory)
        self.router.on(MessageType.SHUTDOWN, self._on_shutdown)
        self.router.on(MessageType.TTS_DONE, self._on_tts_done)
        self.router.on(MessageType.CONFIG_RELOAD, self._on_config_reload)
        self.router.on(MessageType.SESSION_CREATE, self._on_session_create)
        self.router.on(MessageType.SESSION_SWITCH, self._on_session_switch)
        self.router.on(MessageType.SESSION_LIST_REQUEST, self._on_session_list_request)
        self.router.on(MessageType.SESSION_RENAME, self._on_session_rename)
        self.router.on(MessageType.SESSION_DELETE, self._on_session_delete)

        # 加载最近会话或新建
        if self.session_mgr.index:
            self.history = self.session_mgr.load(self.session_mgr.index[0]["id"])
        else:
            self.session_mgr.create()

        log.info("Brain 就绪")
        await self._send_session_list()
        await self.face.send(Message(
            type=MessageType.SESSION_LOADED,
            source="brain", target="face",
            payload={"session_id": self.session_mgr.current_id, "messages": self.history},
        ))
        await self.router.start()

    async def _on_user_text(self, msg: Message):
        text = msg.payload.get("text", "")
        log.info(f"收到用户输入: {text}")
        await self._think_and_reply(text)

    async def _on_asr_result(self, msg: Message):
        text = msg.payload.get("text", "")
        log.info(f"收到语音识别: {text}")
        # 先把识别文字发给 Face 显示为用户气泡
        await self.face.send(Message(
            type=MessageType.ASR_TEXT_DISPLAY,
            source="brain", target="face",
            payload={"text": text},
        ))
        await self._think_and_reply(text)

    async def _on_screenshot(self, msg: Message):
        image_path = msg.payload.get("path", "")
        self.latest_screenshot = image_path
        text = msg.payload.get("text", "请描述你看到的屏幕内容")
        messages = self.prompt_mgr.build_messages(text, self.history)
        # 插入图片到最后一条 user 消息
        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "image", "image": image_path},
                {"type": "text", "text": text},
            ],
        }
        full_reply = ""
        async for chunk in self.engine.generate(messages, images=[image_path]):
            full_reply += chunk
            await self.face.send(Message(
                type=MessageType.LLM_STREAM_CHUNK,
                source="brain", target="face",
                payload={"text": chunk},
            ))
        await self.face.send(Message(
            type=MessageType.LLM_STREAM_END,
            source="brain", target="face",
            payload={"text": full_reply},
        ))

    async def _think_and_reply(self, user_input: str):
        # 记忆检索
        mem_ctx = self.memory.query(user_input) if self.memory else []
        messages = self.prompt_mgr.build_messages(user_input, self.history, mem_ctx)

        images = None
        if self.latest_screenshot:
            messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "image", "image": self.latest_screenshot},
                    {"type": "text", "text": user_input},
                ],
            }
            images = [self.latest_screenshot]

        full_reply = ""
        async for chunk in self.engine.generate(messages, images=images):
            full_reply += chunk
            await self.face.send(Message(
                type=MessageType.LLM_STREAM_CHUNK,
                source="brain", target="face",
                payload={"text": chunk},
            ))

        # 提取 emotion_tag
        emotion = "neutral"
        m = re.search(r"\[emotion:(\w+)\]", full_reply)
        if m:
            emotion = m.group(1)
            full_reply = re.sub(r"\[emotion:\w+\]", "", full_reply).strip()

        # 更新历史（移到 stream end 之前，确保 msg_index 可用）
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": full_reply, "tts_path": ""})
        msg_index = len(self.history) - 1
        if len(self.history) > 40:
            self.history = self.history[-30:]
            msg_index = len(self.history) - 1

        # 流结束（带 msg_index）
        await self.face.send(Message(
            type=MessageType.LLM_STREAM_END,
            source="brain", target="face",
            payload={"text": full_reply, "msg_index": msg_index},
        ))

        # 存入记忆
        self.memory.add(f"用户: {user_input}\n{get('ai_name', 'AI')}: {full_reply}")
        self.session_mgr.save_messages(self.history)

        # 发送 TTS 请求
        await self.perception.send(Message(
            type=MessageType.TTS_REQUEST,
            source="brain", target="perception",
            payload={"text": full_reply, "emotion": emotion, "msg_index": msg_index},
        ))

        # 发送表情更新
        await self.face.send(Message(
            type=MessageType.EXPRESSION_UPDATE,
            source="brain", target="face",
            payload={"emotion": emotion},
        ))

    async def _on_screenshot_memory(self, msg: Message):
        """截图只存记忆 + 转发给 Face 显示，不触发模型回复"""
        image_path = msg.payload.get("path", "")
        log.info(f"视觉记忆截图: {image_path}")
        self.latest_screenshot = image_path
        if self.memory:
            self.memory.add(f"[视觉记忆] 屏幕截图: {image_path}")
        await self.face.send(Message(
            type=MessageType.SCREENSHOT_MEMORY,
            source="brain", target="face",
            payload={"path": image_path},
        ))

    async def _on_tts_done(self, msg: Message):
        msg_index = msg.payload.get("msg_index", -1)
        path = msg.payload.get("path", "")
        if 0 <= msg_index < len(self.history):
            self.history[msg_index]["tts_path"] = path
            self.session_mgr.save_messages(self.history)
        await self.face.send(msg)

    async def _on_config_reload(self, msg: Message):
        from src.core.config import reload_config
        reload_config()
        # 重建 brain 组件
        await self.engine.shutdown()
        self.engine = create_engine()
        self.memory = Memory()
        self.prompt_mgr = PromptManager()
        # 重启 perception / action 子进程
        if hasattr(self, '_restart_services'):
            await asyncio.get_event_loop().run_in_executor(None, self._restart_services)
        log.info("配置已热更新，服务已重启")

    async def _on_session_create(self, msg: Message):
        self.session_mgr.save_messages(self.history)
        self.session_mgr.create()
        self.history = []
        self.latest_screenshot = None
        await self.face.send(Message(
            type=MessageType.SESSION_LOADED,
            source="brain", target="face",
            payload={"session_id": self.session_mgr.current_id, "messages": []},
        ))
        await self._send_session_list()

    async def _on_session_switch(self, msg: Message):
        sid = msg.payload.get("session_id", "")
        if sid == self.session_mgr.current_id:
            return
        self.session_mgr.save_messages(self.history)
        self.history = self.session_mgr.load(sid)
        self.latest_screenshot = None
        await self.face.send(Message(
            type=MessageType.SESSION_LOADED,
            source="brain", target="face",
            payload={"session_id": sid, "messages": self.history},
        ))

    async def _on_session_list_request(self, msg: Message):
        await self._send_session_list()

    async def _on_session_rename(self, msg: Message):
        sid = msg.payload.get("session_id", "")
        title = msg.payload.get("title", "")
        self.session_mgr.rename(sid, title)
        await self._send_session_list()

    async def _on_session_delete(self, msg: Message):
        sid = msg.payload.get("session_id", "")
        was_current = sid == self.session_mgr.current_id
        self.session_mgr.delete(sid)
        if was_current:
            if self.session_mgr.current_id:
                self.history = self.session_mgr.load(self.session_mgr.current_id)
            else:
                self.session_mgr.create()
                self.history = []
            self.latest_screenshot = None
            await self.face.send(Message(
                type=MessageType.SESSION_LOADED,
                source="brain", target="face",
                payload={"session_id": self.session_mgr.current_id, "messages": self.history},
            ))
        await self._send_session_list()

    async def _send_session_list(self):
        await self.face.send(Message(
            type=MessageType.SESSION_LIST,
            source="brain", target="face",
            payload={"sessions": self.session_mgr.list_sessions(),
                     "current_id": self.session_mgr.current_id},
        ))

    async def _on_shutdown(self, msg: Message):
        log.info("收到关闭信号，生成日记...")
        if self.history:
            await self.diary.write(self.history, self.engine)
        self.router.stop()
        await self.engine.shutdown()
