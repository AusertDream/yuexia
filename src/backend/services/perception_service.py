"""感知服务 - 封装 src/perception/tts"""
from src.backend.core.logger import get_logger
from src.backend.perception.tts import TTSEngine, TTSError

log = get_logger("perception_service")


class PerceptionService:
    def __init__(self, socketio):
        self.socketio = socketio
        self.tts = TTSEngine()
        log.info("PerceptionService 初始化完成")

    async def synthesize_and_notify(self, text: str, emotion: str):
        try:
            path = await self.tts.synthesize(text, emotion)
            if path:
                await self.socketio.emit("tts_done", {"path": path, "emotion": emotion}, namespace="/ws/events")
        except TTSError as e:
            log.error(f"TTS 合成失败: {e}")
            await self.socketio.emit("tts_error", {"error": str(e)}, namespace="/ws/events")
