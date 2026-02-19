"""屏幕截图 / 视频流"""
import asyncio
from pathlib import Path
from datetime import datetime
from src.core.config import get
from src.core.logger import get_logger

log = get_logger("screen")


class ScreenCapture:
    def __init__(self):
        self._running = False

    async def capture_once(self) -> str:
        """截取一张屏幕截图，返回路径"""
        import mss
        loop = asyncio.get_event_loop()
        path = f"data/screenshots/screen_{datetime.now().strftime('%H%M%S_%f')}.png"

        def _shot():
            with mss.mss() as sct:
                sct.shot(output=path)
            return path

        return await loop.run_in_executor(None, _shot)

    async def start_periodic(self, callback):
        """定时截图模式"""
        interval = get("action.screen.interval", 5)
        self._running = True
        log.info(f"定时截图已启动，间隔 {interval}s")
        while self._running:
            path = await self.capture_once()
            await callback(path)
            await asyncio.sleep(interval)

    async def start_video_stream(self, callback):
        """视频流模式（低帧率截图）"""
        import cv2
        fps = get("action.screen.fps", 1)
        self._running = True
        loop = asyncio.get_event_loop()
        log.info(f"视频流模式已启动，fps={fps}")

        def _grab_frame():
            import mss, numpy as np
            with mss.mss() as sct:
                img = np.array(sct.grab(sct.monitors[1]))
            path = f"data/screenshots/frame_{datetime.now().strftime('%H%M%S_%f')}.jpg"
            cv2.imwrite(path, img)
            return path

        while self._running:
            path = await loop.run_in_executor(None, _grab_frame)
            await callback(path)
            await asyncio.sleep(1.0 / fps)

    def stop(self):
        self._running = False
