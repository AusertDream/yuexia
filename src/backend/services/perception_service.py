"""感知服务 - 封装 src/perception/tts"""
from src.backend.core.logger import get_logger
from src.backend.perception.tts import TTSEngine

log = get_logger("perception_service")


class PerceptionService:
    def __init__(self, socketio):
        self.socketio = socketio
        self.tts = TTSEngine()
        log.info("PerceptionService 初始化完成")

    async def synthesize_and_notify(self, text: str, emotion: str):
        path = await self.tts.synthesize(text, emotion)
        if path:
            self.socketio.emit("tts_done", {"path": path, "emotion": emotion}, namespace="/ws/events")
