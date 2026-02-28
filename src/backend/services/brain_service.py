"""Brain 服务单例 - 封装 src/brain/ 核心逻辑"""
import re
import time
import queue
import asyncio
import threading
from src.backend.core.config import get
from src.backend.core.logger import get_logger
from src.backend.brain.engine import create_engine
from src.backend.brain.memory import Memory
from src.backend.brain.prompt import PromptManager
from src.backend.brain.session import SessionManager
from src.backend.brain.diary import DiaryWriter

log = get_logger("brain_service")


class BrainService:
    def __init__(self, socketio):
        self.socketio = socketio
        self.history: list[dict] = []
        self.engine = None
        self.memory = None
        self.prompt_mgr = None
        self.diary = None
        self.session_mgr = SessionManager()
        self.latest_screenshot = None
        self._last_inference_speed = 0

        # 独立 asyncio 事件循环线程（供 async engine.generate 使用）
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

        # 加载最近会话
        if self.session_mgr.index:
            self.history = self.session_mgr.load(self.session_mgr.index[0]["id"])
        else:
            self.session_mgr.create()

        self._engine_lock = threading.Lock()
        self._engine_loading = False
        self._inferring = False  # 推理状态标志，供行为引擎检查
        self.behavior_engine = None

        log.info("BrainService 初始化完成（引擎延迟加载）")

    @property
    def is_inferring(self) -> bool:
        """当前是否正在推理，供行为引擎检查"""
        return self._inferring

    def _do_load_engine(self):
        """实际加载引擎逻辑，调用方需持有 _engine_lock"""
        self._engine_loading = True
        try:
            self.engine = create_engine()
            if get("memory.enabled", False):
                try:
                    self.memory = Memory()
                except Exception:
                    log.warning("Memory 初始化失败，已禁用", exc_info=True)
                    self.memory = None
            self.prompt_mgr = PromptManager()
            self.diary = DiaryWriter()
            log.info("LLM 引擎已加载")
            # 引擎加载完成后启动行为引擎
            self._start_behavior_engine()
        except Exception:
            self.engine = None
            self.memory = None
            self.prompt_mgr = None
            self.diary = None
            raise
        finally:
            self._engine_loading = False

    def _start_behavior_engine(self):
        """如果配置启用，启动行为引擎"""
        if not get("behavior.enabled", False):
            log.info("行为引擎未启用（behavior.enabled=false）")
            return
        try:
            from src.backend.brain.behavior_engine import BehaviorEngine
            self.behavior_engine = BehaviorEngine(self.socketio, self)
            self.behavior_engine.start()
        except Exception:
            log.warning("行为引擎启动失败", exc_info=True)
            self.behavior_engine = None

    def _ensure_engine(self):
        """延迟加载 LLM 引擎，线程安全"""
        if self.engine is not None:
            return
        with self._engine_lock:
            if self.engine is not None:
                return
            self._do_load_engine()

    def chat_stream(self, user_input: str):
        """同步 generator，yield dict。供 SSE 端点消费。"""
        if self.behavior_engine:
            self.behavior_engine.notify_user_input()
        if self._engine_loading:
            yield {"type": "error", "text": "AI 引擎正在加载中，请稍后再试"}
            return
        self._ensure_engine()
        q = queue.Queue()
        future = asyncio.run_coroutine_threadsafe(self._stream_to_queue(user_input, q), self._loop)
        try:
            while True:
                try:
                    item = q.get(timeout=300)
                except queue.Empty:
                    yield {"type": "error", "text": "推理超时 (300s)"}
                    break
                if item is None:
                    break
                yield item
        except GeneratorExit:
            future.cancel()

    async def _stream_to_queue(self, user_input: str, q: queue.Queue):
        """核心推理流程，复用 src/brain/brain.py._think_and_reply 逻辑"""
        self._inferring = True
        try:
            mem_ctx = self.memory.query(user_input) if self.memory else []
            messages = self.prompt_mgr.build_messages(user_input, self.history, mem_ctx)

            full_reply = ""
            chunk_count = 0
            t0 = time.time()
            async for chunk in self.engine.generate(messages):
                full_reply += chunk
                chunk_count += 1
                q.put({"type": "chunk", "text": chunk})
            elapsed = time.time() - t0
            if elapsed > 0:
                self._last_inference_speed = round(chunk_count / elapsed, 1)

            # 提取 emotion_tag
            emotion = "neutral"
            m = re.search(r"\[emotion:(\w+)\]", full_reply)
            if m:
                emotion = m.group(1)
                full_reply = re.sub(r"\[emotion:\w+\]", "", full_reply).strip()

            # 更新历史
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": full_reply, "tts_path": ""})
            max_hist = get("session.max_history_messages", 40)
            if len(self.history) > max_hist:
                self.history = self.history[-int(max_hist * 0.75):]

            self.session_mgr.save_messages(self.history)
            await self.socketio.emit("user_message", {"text": user_input}, namespace="/ws/events")
            await self.socketio.emit("ai_message", {"text": full_reply}, namespace="/ws/events")
            if self.memory:
                self.memory.add(f"用户: {user_input}\n{get('ai_name', 'AI')}: {full_reply}")

            q.put({"type": "end", "text": full_reply, "emotion": emotion})

            # 触发 TTS（异步，不阻塞流）
            self._trigger_tts(full_reply, emotion)
            # 推送表情更新
            await self.socketio.emit("expression", {"emotion": emotion}, namespace="/ws/events")
            # 日记记录检查
            if self.diary and get("diary.enabled", True):
                try:
                    await self.diary.write(self.history, self.engine)
                except Exception:
                    log.debug("日记写入跳过", exc_info=True)

        except Exception as e:
            log.exception("推理异常")
            q.put({"type": "error", "text": str(e)})
        finally:
            self._inferring = False
            q.put(None)

    def _trigger_tts(self, text: str, emotion: str):
        """后台触发 TTS 合成"""
        from src.backend.services import get_perception
        perc = get_perception()
        if perc:
            asyncio.run_coroutine_threadsafe(perc.synthesize_and_notify(text, emotion), self._loop)

    def reload(self):
        """重新加载引擎，失败时保留旧引擎继续服务"""
        log.info("开始重新加载引擎...")
        old_engine = self.engine
        old_memory = self.memory
        old_prompt_mgr = self.prompt_mgr
        old_diary = self.diary
        old_behavior = self.behavior_engine

        try:
            # 先创建新引擎
            new_engine = create_engine()
            new_memory = None
            if get("memory.enabled", False):
                try:
                    new_memory = Memory()
                except Exception:
                    log.warning("Memory 重新初始化失败，已禁用", exc_info=True)
            new_prompt_mgr = PromptManager()
            new_diary = DiaryWriter()

            # 新引擎创建成功，替换旧引擎
            self.engine = new_engine
            self.memory = new_memory
            self.prompt_mgr = new_prompt_mgr
            self.diary = new_diary

            # 停止旧的行为引擎
            if old_behavior and old_behavior.is_running:
                old_behavior.stop()

            # 异步关闭旧引擎，释放 GPU 显存和连接池
            if old_engine is not None and hasattr(old_engine, 'shutdown'):
                try:
                    asyncio.run_coroutine_threadsafe(old_engine.shutdown(), self._loop)
                    log.info("旧引擎已提交异步关闭")
                except Exception:
                    log.warning("旧引擎关闭失败", exc_info=True)

            # 启动新的行为引擎
            self._start_behavior_engine()

            log.info("引擎重新加载完成")
        except Exception:
            # 新引擎创建失败，保留旧引擎
            self.engine = old_engine
            self.memory = old_memory
            self.prompt_mgr = old_prompt_mgr
            self.diary = old_diary
            self.behavior_engine = old_behavior
            log.error("引擎重新加载失败，保留旧引擎继续服务", exc_info=True)
            raise

    def shutdown(self):
        """关闭 BrainService，停止行为引擎"""
        if self.behavior_engine and self.behavior_engine.is_running:
            self.behavior_engine.stop()
            log.info("行为引擎已随 BrainService 关闭")
