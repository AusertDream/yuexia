"""Action 子进程入口"""
from __future__ import annotations
import asyncio
import multiprocessing as mp
from src.core.bus import AsyncQueueBridge
from src.core.config import load_config, get
from src.core.message import Message, MessageType
from src.core.logger import get_logger

log = get_logger("action.process")


async def _run(bridge: AsyncQueueBridge):
    from src.action.screen import ScreenCapture
    from src.action.browser import BrowserAgent

    screen = ScreenCapture()
    browser = BrowserAgent()

    async def on_screenshot(path: str):
        await bridge.send(Message(
            type=MessageType.SCREENSHOT_MEMORY,
            source="action", target="brain",
            payload={"path": path},
        ))

    # 启动屏幕感知
    mode = get("action.screen.mode", "screenshot")
    if mode == "video_stream":
        screen_task = asyncio.create_task(screen.start_video_stream(on_screenshot))
    else:
        screen_task = asyncio.create_task(screen.start_periodic(on_screenshot))

    # 轮询 inbound 处理 action 请求
    try:
        while True:
            msg = await bridge.recv()
            if msg:
                if msg.type == MessageType.ACTION_REQUEST:
                    action = msg.payload.get("action", "")
                    if action == "browse":
                        url = msg.payload.get("url", "")
                        title = await browser.goto(url)
                        shot = await browser.screenshot()
                        await bridge.send(Message(
                            type=MessageType.SCREENSHOT,
                            source="action", target="brain",
                            payload={"path": shot, "text": f"浏览器打开了: {title}"},
                        ))
                elif msg.type == MessageType.SHUTDOWN:
                    break
            await asyncio.sleep(0.01)
    finally:
        screen.stop()
        screen_task.cancel()
        await browser.close()


def action_main(inbound: mp.Queue, outbound: mp.Queue, config_path: str = "config.yaml",
                log_queue: mp.Queue | None = None):
    load_config(config_path)
    if log_queue:
        from src.core.logger import setup_queue_logging
        setup_queue_logging(log_queue)
    log.info("Action 进程启动")
    bridge = AsyncQueueBridge(inbound, outbound)
    asyncio.run(_run(bridge))
    log.info("Action 进程退出")
