"""API 引擎：通过 OpenAI 兼容接口调用远程 LLM"""
import json
import asyncio
import base64
import mimetypes
from typing import AsyncIterator

import httpx

from src.backend.brain.base_engine import BaseEngine
from src.backend.core.config import get
from src.backend.core.logger import get_logger

log = get_logger("engine.api")


class APIEngine(BaseEngine):
    """通过 OpenAI 兼容的 /v1/chat/completions 接口调用远程 LLM"""

    def __init__(self):
        api_url = get("brain.api_url", "")
        if not api_url:
            raise ValueError("brain.api_url 未配置，无法启动 API 引擎")
        self.api_url = api_url.rstrip("/")
        self.api_key = get("brain.api_key", "")
        self.api_model = get("brain.api_model", "")
        if not self.api_model:
            raise ValueError("brain.api_model 未配置，无法启动 API 引擎")

        timeout = httpx.Timeout(
            get("network.request_timeout", 120),
            connect=get("network.connect_timeout", 10)
        )
        proxy = None
        if get("network.proxy_enabled", False):
            proxy = get("network.proxy_url", None) or None
        limits = httpx.Limits(
            max_connections=get("network.pool_max_size", 20),
            max_keepalive_connections=get("network.pool_size", 10)
        )
        self.client = httpx.AsyncClient(timeout=timeout, proxy=proxy, limits=limits)
        self._retry_count = get("network.retry_count", 3)
        log.info(f"API 引擎已初始化: url={self.api_url}, model={self.api_model}")

    @property
    def engine_type(self) -> str:
        return "api"

    def _build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _image_to_base64_url(path: str) -> str:
        """将本地图片文件转为 base64 data URL"""
        mime, _ = mimetypes.guess_type(path)
        if not mime:
            mime = "image/png"
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{data}"

    @staticmethod
    def _build_messages_with_images(messages: list[dict], images: list[str]) -> list[dict]:
        """将图片以 OpenAI vision 格式嵌入到最后一条用户消息中"""
        result = [m.copy() for m in messages]
        # 找到最后一条 user 消息
        last_user_idx = None
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("role") == "user":
                last_user_idx = i
                break
        if last_user_idx is None:
            return result

        msg = result[last_user_idx]
        original_content = msg.get("content", "")
        # 构建 multimodal content 数组
        content_parts = []
        if isinstance(original_content, str):
            content_parts.append({"type": "text", "text": original_content})
        elif isinstance(original_content, list):
            content_parts.extend(original_content)

        for img in images:
            if img.startswith("data:"):
                image_url = img
            else:
                image_url = APIEngine._image_to_base64_url(img)
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": image_url},
            })

        msg["content"] = content_parts
        return result

    async def generate(self, messages: list[dict], images: list[str] | None = None) -> AsyncIterator[str]:
        if images:
            messages = self._build_messages_with_images(messages, images)

        payload = {
            "model": self.api_model,
            "messages": messages,
            "stream": True,
            "temperature": get("brain.temperature", 0.7),
            "max_tokens": get("brain.max_tokens", 4096),
            "top_p": get("brain.top_p", 0.9),
            "frequency_penalty": get("brain.frequency_penalty", 0.0),
            "presence_penalty": get("brain.presence_penalty", 0.0),
            "stop": get("brain.stop_sequences", None) or None,
        }
        url = f"{self.api_url}/v1/chat/completions"
        headers = self._build_headers()

        last_err = None
        for attempt in range(self._retry_count + 1):
            try:
                async with self.client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code >= 500 and attempt < self._retry_count:
                        body = await resp.aread()
                        log.warning(f"API 5xx (尝试 {attempt+1}/{self._retry_count+1}): HTTP {resp.status_code}")
                        last_err = Exception(f"HTTP {resp.status_code}")
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    if resp.status_code != 200:
                        body = await resp.aread()
                        log.error(f"API 请求失败 (HTTP {resp.status_code}): {body.decode('utf-8', errors='replace')}")
                        yield f"[API 错误: HTTP {resp.status_code}]"
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, IndexError, KeyError) as e:
                            log.debug(f"SSE 解析跳过: {e}")
                            continue
                return
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_err = e
                if attempt < self._retry_count:
                    log.warning(f"API 请求失败 (尝试 {attempt+1}/{self._retry_count+1}): {e}")
                    await asyncio.sleep(min(2 ** attempt, 8))
                    continue
            except Exception as e:
                log.error(f"API 请求异常: {e}", exc_info=True)
                yield f"[API 错误: {e}]"
                return
        if last_err:
            log.error(f"API 请求在 {self._retry_count+1} 次尝试后失败: {last_err}")
            yield f"[API 连接失败: {last_err}]"

    async def shutdown(self):
        await self.client.aclose()
        log.info("API 引擎已关闭")
