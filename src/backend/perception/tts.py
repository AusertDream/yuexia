"""GPT-SoVITS TTS 集成 (HTTP API 模式)"""
import atexit
import re
import httpx
from pathlib import Path
from datetime import datetime
from src.backend.core.config import get, resolve_path
from src.backend.core.logger import get_logger
from src.backend.perception.emotion_pool import EmotionPool

log = get_logger("tts")


class TTSError(Exception):
    """TTS 合成失败时抛出的异常"""
    pass


def _strip_emoji(text: str) -> str:
    """移除 emoji 和其他非 BMP 字符，保留中日韩文字和常用标点"""
    return re.sub(r'[\U00010000-\U0010ffff]', '', text)


class TTSEngine:
    def __init__(self):
        self.emotion_pool = EmotionPool()
        self.output_dir = resolve_path(get("perception.tts.output_dir", "data/tts_output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        api_url = get("perception.tts.api_url", "")
        if not api_url:
            tts_port = get("server.tts_port", 9880)
            api_url = f"http://127.0.0.1:{tts_port}"
        self.api_url = api_url.rstrip("/")
        timeout = get("perception.tts.timeout", 60)
        self._client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            timeout=httpx.Timeout(timeout, connect=10)
        )
        atexit.register(self._sync_close)

    async def synthesize(self, text: str, emotion: str = "neutral") -> str | None:
        text = _strip_emoji(text).strip()
        if not text:
            log.warning("TTS 文本过滤 emoji 后为空，跳过合成")
            return None

        ref = self.emotion_pool.get_ref(emotion)

        output_path = self.output_dir / f"{datetime.now().strftime('%H%M%S_%f')}.wav"
        speed = get("perception.tts.speed", 1.0)
        payload = {
            "text": text,
            "text_lang": "zh",
            "text_split_method": "cut5",
            "media_type": "wav",
            "speed": speed,
        }
        if ref:
            payload["ref_audio_path"] = ref.get("path", "")
            payload["prompt_text"] = ref.get("text", "")
            payload["prompt_lang"] = "zh"
        try:
            # 使用持久连接池发送请求
            r = await self._client.post(f"{self.api_url}/tts", json=payload)
            if r.status_code == 200:
                output_path.write_bytes(r.content)
                log.info(f"TTS 合成完成: {output_path}")
                return str(output_path)
            error_detail = r.text[:200] if r.text else "无响应内容"
            log.error(f"TTS API 返回 {r.status_code}: {error_detail}")
            raise TTSError(f"TTS 服务返回错误状态码 {r.status_code}")
        except TTSError:
            raise
        except Exception as e:
            log.error(f"TTS 请求失败: {e}", exc_info=True)
            raise TTSError(f"TTS 请求异常: {e}") from e

    async def close(self):
        """关闭连接池，释放资源"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _sync_close(self):
        """进程退出时同步关闭连接池"""
        if self._client and not self._client.is_closed:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._client.aclose())
                else:
                    loop.run_until_complete(self._client.aclose())
            except Exception:
                pass
