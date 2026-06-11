"""感知服务 - 封装 src/perception/tts 和 asr"""
import os
import asyncio
from src.backend.core.logger import get_logger
from src.backend.perception.tts import TTSEngine, TTSError
from src.backend.perception.asr import ASREngine, ASRError

log = get_logger("perception_service")


class PerceptionService:
    def __init__(self, socketio, brain=None):
        self.socketio = socketio
        self.brain = brain
        self.tts = TTSEngine()
        self.asr = ASREngine()
        self._realtime_asr_active = False
        log.info("PerceptionService 初始化完成（TTS + ASR）")

    async def synthesize_and_notify(self, text: str, emotion: str):
        try:
            path = await self.tts.synthesize(text, emotion)
            if path:
                await self.socketio.emit("tts_done", {"path": path, "emotion": emotion}, namespace="/ws/events")
                # 回写 tts_path 到 brain.history 并持久化
                if self.brain and self.brain.history:
                    filename = os.path.basename(path.replace("\\", "/"))
                    audio_url = f"/audio/{filename}"
                    for msg in reversed(self.brain.history):
                        if msg.get("role") == "assistant":
                            msg["tts_path"] = audio_url
                            break
                    self.brain.session_mgr.save_messages(self.brain.history)
        except TTSError as e:
            log.error(f"TTS 合成失败: {e}")
            await self.socketio.emit("tts_error", {"error": str(e)}, namespace="/ws/events")

    async def transcribe_audio(self, audio_data, sample_rate: int = 16000) -> dict:
        """
        转写音频数据

        Args:
            audio_data: 音频数据（numpy数组）
            sample_rate: 采样率

        Returns:
            dict: 包含 text、language、confidence
        """
        try:
            # 在线程池中执行CPU密集型操作，避免阻塞事件循环
            result = await asyncio.to_thread(
                self.asr.transcribe,
                audio_data,
                sample_rate
            )
            log.info(f"ASR 转写成功: {result['text'][:50]}...")
            return result
        except ASRError as e:
            log.error(f"ASR 转写失败: {e}")
            raise

    async def transcribe_file(self, file_path: str) -> dict:
        """
        转写音频文件

        Args:
            file_path: 音频文件路径

        Returns:
            dict: 包含 text、language、confidence
        """
        try:
            # 在线程池中执行CPU密集型操作，避免阻塞事件循环
            result = await asyncio.to_thread(
                self.asr.transcribe_file,
                file_path
            )
            log.info(f"ASR 文件转写成功: {result['text'][:50]}...")
            return result
        except ASRError as e:
            log.error(f"ASR 文件转写失败: {e}")
            raise

    async def start_realtime_asr(self, device=None):
        """启动实时ASR会话

        Returns:
            bool: False表示已在运行中，None/True表示启动成功
        """
        if self._realtime_asr_active:
            log.warning("实时 ASR 已在运行中")
            return False

        self._realtime_asr_active = True

        # 捕获主线程的事件循环，传递给回调函数
        main_loop = asyncio.get_event_loop()

        # 定义回调函数，在子线程中被调用
        def on_asr_result(text: str, language: str, confidence: float):
            """ASR识别结果回调，运行在子线程中"""
            try:
                # 使用主线程的事件循环调度 emit
                asyncio.run_coroutine_threadsafe(
                    self.socketio.emit(
                        "asr_result",
                        {"text": text, "language": language, "confidence": confidence},
                        namespace="/ws/events"
                    ),
                    main_loop
                )
            except Exception as e:
                log.error(f"推送 ASR 结果失败: {e}", exc_info=True)

        # 在线程池中启动实时识别，避免阻塞事件循环
        await asyncio.to_thread(self.asr.start_realtime, device, on_asr_result)

        log.info(f"实时 ASR 会话已启动，设备: {device}")
        await self.socketio.emit("asr_started", {}, namespace="/ws/events")

    async def stop_realtime_asr(self):
        """停止实时ASR会话"""
        if not self._realtime_asr_active:
            log.warning("实时 ASR 未运行")
            return

        # 在线程池中停止实时识别，避免阻塞事件循环
        await asyncio.to_thread(self.asr.stop_realtime)

        self._realtime_asr_active = False
        log.info("实时 ASR 会话已停止")
        await self.socketio.emit("asr_stopped", {}, namespace="/ws/events")

    def is_realtime_asr_active(self) -> bool:
        """检查实时ASR是否激活"""
        return self._realtime_asr_active

