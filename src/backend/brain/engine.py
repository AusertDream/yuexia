"""LLM 推理引擎：vLLM / Transformers 双模"""
from abc import ABC, abstractmethod
from typing import AsyncIterator
from src.backend.core.config import get
from src.backend.core.logger import get_logger

log = get_logger("engine")


MAX_IMAGE_SIZE = 720


def _load_and_resize(path: str) -> "Image.Image":
    from PIL import Image
    img = Image.open(path)
    img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE))
    return img


class LLMEngine(ABC):
    @abstractmethod
    async def generate(self, messages: list[dict], images: list[str] | None = None) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def shutdown(self):
        ...


class VLLMEngine(LLMEngine):
    def __init__(self):
        from vllm import AsyncLLMEngine as _AsyncEngine
        from vllm import AsyncEngineArgs, SamplingParams
        from transformers import AutoProcessor
        self.SamplingParams = SamplingParams

        model_path = get("brain.model_path")
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        args = AsyncEngineArgs(
            model=model_path,
            gpu_memory_utilization=get("brain.gpu_memory_utilization", 0.85),
            max_model_len=get("brain.max_model_len", 8192),
            trust_remote_code=True,
            dtype="auto",
        )
        self.engine = _AsyncEngine.from_engine_args(args)
        log.info(f"vLLM 引擎已加载: {model_path}")

    async def generate(self, messages: list[dict], images: list[str] | None = None) -> AsyncIterator[str]:
        enable_thinking = get("brain.enable_thinking", False)
        extra = {"enable_thinking": enable_thinking} if enable_thinking else {}
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **extra)

        mm_data = None
        if images:
            from PIL import Image
            import io, base64
            pil_images = []
            for img in images:
                if img.startswith("data:"):
                    img_data = base64.b64decode(img.split(",", 1)[1])
                    im = Image.open(io.BytesIO(img_data))
                    im.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE))
                    pil_images.append(im)
                else:
                    pil_images.append(_load_and_resize(img))
            mm_data = {"image": pil_images}

        params = self.SamplingParams(temperature=0.7, max_tokens=2048)
        request_id = f"req-{id(messages)}"

        results = self.engine.generate(text, params, request_id=request_id) if not mm_data else self.engine.generate({"prompt": text, "multi_modal_data": mm_data}, params, request_id=request_id)
        prev_len = 0
        async for result in results:
            text_out = result.outputs[0].text
            delta = text_out[prev_len:]
            prev_len = len(text_out)
            if delta:
                yield delta

    async def shutdown(self):
        pass


class TransformersEngine(LLMEngine):
    def __init__(self):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        model_path = get("brain.model_path")
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_path,
            dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        log.info(f"Transformers 引擎已加载: {model_path}")

    async def generate(self, messages: list[dict], images: list[str] | None = None) -> AsyncIterator[str]:
        import torch, asyncio
        from threading import Thread
        from transformers import TextIteratorStreamer

        enable_thinking = get("brain.enable_thinking", False)
        extra = {"enable_thinking": enable_thinking} if enable_thinking else {}
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **extra)

        if images:
            pil_images = [_load_and_resize(img) for img in images]
            inputs = self.processor(text=text, images=pil_images, return_tensors="pt").to(self.model.device)
        else:
            inputs = self.processor(text=text, return_tensors="pt").to(self.model.device)
        streamer = TextIteratorStreamer(self.processor, skip_prompt=True, skip_special_tokens=True)

        gen_kwargs = {**inputs, "streamer": streamer, "max_new_tokens": 2048, "temperature": 0.7, "do_sample": True}
        thread = Thread(target=self.model.generate, kwargs=gen_kwargs)
        thread.start()

        for chunk in streamer:
            if chunk:
                yield chunk
                await asyncio.sleep(0)
        await asyncio.to_thread(thread.join)

    async def shutdown(self):
        del self.model
        import torch
        torch.cuda.empty_cache()


def create_engine() -> LLMEngine:
    import sys
    engine_type = get("brain.engine", "vllm")
    if engine_type == "vllm":
        if sys.platform == "win32":
            log.warning("vLLM 不支持 Windows，降级到 Transformers")
            return TransformersEngine()
        try:
            return VLLMEngine()
        except Exception as e:
            log.warning(f"vLLM 加载失败，降级到 Transformers: {e}")
            return TransformersEngine()
    return TransformersEngine()
