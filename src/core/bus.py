"""AsyncIO <-> multiprocessing.Queue 桥接"""
import asyncio
import multiprocessing as mp
from typing import Callable, Awaitable
from src.core.message import Message, MessageType
from src.core.logger import get_logger

log = get_logger("bus")


class AsyncQueueBridge:
    """将阻塞的 mp.Queue 桥接到 asyncio"""

    def __init__(self, inbound: mp.Queue, outbound: mp.Queue):
        self.inbound = inbound
        self.outbound = outbound

    async def send(self, msg: Message):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.outbound.put, msg.model_dump())

    async def recv(self, timeout: float = 0.05) -> Message | None:
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, self.inbound.get, True, timeout)
            return Message(**data)
        except Exception:
            return None

    def send_sync(self, msg: Message):
        self.outbound.put(msg.model_dump())

    def recv_sync(self, timeout: float = 0.05) -> Message | None:
        try:
            data = self.inbound.get(timeout=timeout)
            return Message(**data)
        except Exception:
            return None


class MessageRouter:
    """轮询多个 bridge，按 MessageType 分发到 handler"""

    def __init__(self):
        self._bridges: list[AsyncQueueBridge] = []
        self._handlers: dict[MessageType, list[Callable[[Message], Awaitable]]] = {}
        self._running = False

    def add_bridge(self, bridge: AsyncQueueBridge):
        self._bridges.append(bridge)

    def on(self, msg_type: MessageType, handler: Callable[[Message], Awaitable]):
        self._handlers.setdefault(msg_type, []).append(handler)

    async def start(self):
        self._running = True
        log.info("MessageRouter 启动")
        while self._running:
            for bridge in self._bridges:
                msg = await bridge.recv()
                if msg:
                    handlers = self._handlers.get(msg.type, [])
                    if handlers:
                        for h in handlers:
                            asyncio.create_task(self._safe_call(h, msg))
                    else:
                        log.debug(f"未处理消息: {msg.type}")
            await asyncio.sleep(0.01)

    async def _safe_call(self, handler, msg: Message):
        try:
            await handler(msg)
        except Exception:
            log.exception(f"Handler 异常: {msg.type}")

    def stop(self):
        self._running = False
        log.info("MessageRouter 停止")
