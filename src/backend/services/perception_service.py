"""感知服务 - 封装 src/perception/tts"""
import os
from src.backend.core.logger import get_logger
from src.backend.perception.tts import TTSEngine, TTSError

log = get_logger("perception_service")


class PerceptionService:
    def __init__(self, socketio, brain=None):
        self.socketio = socketio
        self.brain = brain
        self.tts = TTSEngine()
        log.info("PerceptionService 初始化完成")

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
