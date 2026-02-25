"""GPT-SoVITS TTS 集成 (HTTP API 模式)"""
import re
import httpx
from pathlib import Path
from datetime import datetime
from src.backend.core.config import get
from src.backend.core.logger import get_logger
from src.backend.perception.emotion_pool import EmotionPool

log = get_logger("tts")


def _strip_emoji(text: str) -> str:
    """移除 emoji 和其他非 BMP 字符，保留中日韩文字和常用标点"""
    return re.sub(r'[\U00010000-\U0010ffff]', '', text)


class TTSEngine:
    def __init__(self):
        self.emotion_pool = EmotionPool()
        self.output_dir = Path(get("perception.tts.output_dir", "data/tts_output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tts_port = get("server.tts_port", 9880)
        self.api_url = f"http://127.0.0.1:{tts_port}"

    async def synthesize(self, text: str, emotion: str = "neutral") -> str | None:
        text = _strip_emoji(text).strip()
        if not text:
            log.warning("TTS 文本过滤 emoji 后为空，跳过合成")
            return None

        ref = self.emotion_pool.get_ref(emotion)

        output_path = self.output_dir / f"{datetime.now().strftime('%H%M%S_%f')}.wav"
        payload = {
            "text": text,
            "text_lang": "zh",
            "text_split_method": "cut5",
            "media_type": "wav",
        }
        if ref:
            payload["ref_audio_path"] = ref.get("path", "")
            payload["prompt_text"] = ref.get("text", "")
            payload["prompt_lang"] = "zh"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10)) as c:
                r = await c.post(f"{self.api_url}/tts", json=payload)
            if r.status_code == 200:
                output_path.write_bytes(r.content)
                log.info(f"TTS 合成完成: {output_path}")
                return str(output_path)
            log.warning(f"TTS API 返回 {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log.exception("TTS 请求失败")
        return None
