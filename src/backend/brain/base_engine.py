"""LLM 引擎抽象基类"""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseEngine(ABC):
    """所有 LLM 引擎的抽象基类"""

    @property
    @abstractmethod
    def engine_type(self) -> str:
        """返回引擎类型标识，如 "vllm"、"transformers"、"api" """
        ...

    @abstractmethod
    async def generate(self, messages: list[dict], images: list[str] | None = None) -> AsyncIterator[str]:
        """流式生成文本，yield 每个增量文本片段"""
        ...

    @abstractmethod
    async def shutdown(self):
        """关闭引擎，释放资源"""
        ...
