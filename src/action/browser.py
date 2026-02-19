"""Playwright 浏览器自动化"""
import asyncio
from src.core.config import get
from src.core.logger import get_logger

log = get_logger("browser")


class BrowserAgent:
    def __init__(self):
        self.browser = None
        self.page = None

    async def launch(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        headless = get("action.browser.headless", False)
        self.browser = await self._pw.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        log.info("浏览器已启动")

    async def goto(self, url: str) -> str:
        if not self.page:
            await self.launch()
        await self.page.goto(url, wait_until="domcontentloaded")
        return await self.page.title()

    async def screenshot(self, path: str | None = None) -> str:
        if not self.page:
            return ""
        p = path or "data/tts_output/browser_shot.png"
        await self.page.screenshot(path=p)
        return p

    async def get_text(self) -> str:
        if not self.page:
            return ""
        return await self.page.inner_text("body")

    async def close(self):
        if self.browser:
            await self.browser.close()
            await self._pw.stop()
            log.info("浏览器已关闭")
