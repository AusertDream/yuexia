"""日记调度器 — 定时检查并生成到期日记

与行为引擎独立。APScheduler 每小时检查一次，并在启动时立即检查一次（补上
应用错过整点的情况）。只在「已过当天 generation_time、_should_generate 通过、
有对话历史、引擎已加载且未在推理」时才生成，保证行为可预期。
"""
import asyncio
import threading
from datetime import datetime, time as dtime
from apscheduler.schedulers.background import BackgroundScheduler
from src.backend.core.config import get
from src.backend.core.logger import get_logger

log = get_logger("diary_scheduler")

_DIARY_TYPES = ["daily", "weekly", "monthly", "yearly"]


class DiaryScheduler:
    """定时日记调度器：到点检查并生成各类型到期日记。"""

    def __init__(self, brain_service):
        self._brain_service = brain_service
        self._scheduler = BackgroundScheduler(daemon=True)
        self._running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        with self._lock:
            if self._running:
                return
            self._scheduler = BackgroundScheduler(daemon=True)
            # 每小时检查一次；frequency/generation_time 决定是否真的生成
            self._scheduler.add_job(self._tick, "interval", hours=1, id="diary_tick")
            self._scheduler.start()
            self._running = True
            log.info("日记调度器已启动")
        # 启动时立即检查一次（补上应用未在整点运行的情况）
        self._tick()

    def stop(self):
        with self._lock:
            if not self._running:
                return
            self._scheduler.shutdown(wait=False)
            self._running = False
            log.info("日记调度器已停止")

    def _past_generation_time(self) -> bool:
        """当前是否已过当天的 generation_time"""
        try:
            t_str = get("diary.generation_time", "22:00")
            parts = t_str.split(":")
            target = dtime(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            return datetime.now().time() >= target
        except Exception:
            return True  # 配置异常时不阻塞生成

    def _tick(self):
        """检查并生成到期日记。"""
        if not get("diary.enabled", True):
            return
        brain = self._brain_service
        if brain.diary is None or brain.engine is None:
            return
        if brain.is_inferring:
            log.debug("日记调度器：正在推理，跳过本次检查")
            return
        if not brain.history:
            log.debug("日记调度器：当前会话无对话历史，跳过")
            return
        if not self._past_generation_time():
            return

        for diary_type in _DIARY_TYPES:
            if not get(f"diary.{diary_type}.enabled", False):
                continue
            try:
                # diary.write 内部会再做 _should_generate 与 enabled 双重校验
                future = asyncio.run_coroutine_threadsafe(
                    brain.diary.write(brain.history, brain.engine, diary_type),
                    brain._loop,
                )
                content = future.result(timeout=120)
                if content:
                    log.info("日记调度器：已生成 %s 日记", diary_type)
            except Exception:
                log.warning("日记调度器：%s 生成失败", diary_type, exc_info=True)
