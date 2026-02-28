"""行为引擎 — 多触发器 + LLM 生成支持"""
import asyncio
import random
import threading
from datetime import datetime, time as dtime
from apscheduler.schedulers.background import BackgroundScheduler
from src.backend.core.config import get
from src.backend.core.logger import get_logger

log = get_logger("behavior_engine")

_TEMPLATES = {
    "问候": [
        "早上好呀，今天也要元气满满哦~",
        "下午好，休息一下吧~",
        "晚上好，今天辛苦了~",
        "嗨，好久不见~",
        "你好呀，现在方便聊天吗？",
    ],
    "关心": [
        "今天过得怎么样？",
        "记得喝水哦，别太忙了~",
        "天气变化大，注意保暖呀~",
        "别太累了，适当休息一下~",
        "吃饭了吗？别忘了按时吃饭哦~",
    ],
    "分享": [
        "刚才看到一片很美的云，可惜没法拍给你看~",
        "今天学到了一个有趣的知识，想跟你分享~",
        "突然想到一个好玩的事情，等你有空跟你说~",
        "发现了一首好听的歌，下次推荐给你~",
        "今天的天空特别好看呢~",
    ],
    "思念": [
        "在想你呢~",
        "突然很想跟你聊聊天~",
        "你在忙什么呀？",
        "好想知道你现在在做什么~",
        "有点无聊，想找你说说话~",
    ],
}


class BehaviorEngine:
    """行为引擎：支持多触发器类型和 LLM 生成消息。"""

    def __init__(self, socketio, brain_service):
        self._socketio = socketio
        self._brain_service = brain_service
        self._scheduler = BackgroundScheduler(daemon=True)
        self._running = False
        self._lock = threading.Lock()
        self._daily_count = 0
        self._last_count_date = datetime.now().date()
        self._last_user_input_time = datetime.now()

    @property
    def is_running(self) -> bool:
        return self._running

    def notify_user_input(self):
        """用户发送消息时调用，重置无输入计时器"""
        self._last_user_input_time = datetime.now()

    def start(self):
        with self._lock:
            if self._running:
                return
            self._scheduler = BackgroundScheduler(daemon=True)
            trigger_type = get("behavior.trigger_type", "interval")

            if trigger_type == "cron":
                expr = get("behavior.cron_expression", "")
                if expr:
                    parts = expr.split()
                    if len(parts) >= 5:
                        self._scheduler.add_job(
                            self._tick, "cron",
                            minute=parts[0], hour=parts[1],
                            day=parts[2], month=parts[3],
                            day_of_week=parts[4],
                            id="behavior_tick",
                        )
            elif trigger_type == "idle":
                # 每分钟检查一次是否超过无输入阈值
                self._scheduler.add_job(
                    self._check_idle, "interval", minutes=1, id="behavior_idle_check",
                )
            else:
                interval = get("behavior.interval_minutes", 30)
                self._scheduler.add_job(
                    self._tick, "interval", minutes=interval, id="behavior_tick",
                )

            self._scheduler.start()
            self._running = True
            log.info("行为引擎已启动，触发类型=%s", trigger_type)

    def stop(self):
        with self._lock:
            if not self._running:
                return
            self._scheduler.shutdown(wait=False)
            self._running = False
            log.info("行为引擎已停止")

    def _check_idle(self):
        """检查无输入超时"""
        timeout = get("behavior.idle_timeout_minutes", 10)
        elapsed = (datetime.now() - self._last_user_input_time).total_seconds() / 60
        if elapsed >= timeout:
            self._tick()
            self._last_user_input_time = datetime.now()  # 重置，避免连续触发

    def _in_quiet_hours(self) -> bool:
        """检查当前是否在安静时段"""
        try:
            start_str = get("behavior.quiet_hours_start", "23:00")
            end_str = get("behavior.quiet_hours_end", "07:00")
            now = datetime.now().time()
            start = dtime(*map(int, start_str.split(":")))
            end = dtime(*map(int, end_str.split(":")))
            if start <= end:
                return start <= now <= end
            return now >= start or now <= end
        except Exception:
            return False

    def _check_daily_limit(self) -> bool:
        """检查每日消息限制，返回 True 表示可以发送"""
        today = datetime.now().date()
        if today != self._last_count_date:
            self._daily_count = 0
            self._last_count_date = today
        return self._daily_count < get("behavior.max_daily_messages", 50)

    def _generate_message(self) -> str | None:
        """生成消息：优先 LLM，回退到模板"""
        if get("behavior.llm_generation_enabled", False):
            try:
                if not self._brain_service.is_inferring and self._brain_service.engine:
                    return self._generate_llm_message()
            except Exception:
                log.warning("LLM 生成主动消息失败，回退到模板", exc_info=True)

        if get("behavior.message_templates_enabled", True):
            categories = get("behavior.categories", list(_TEMPLATES.keys()))
            pool = []
            for cat in categories:
                if cat in _TEMPLATES:
                    pool.extend(_TEMPLATES[cat])
            return random.choice(pool) if pool else None
        return None

    def _generate_llm_message(self) -> str | None:
        """调用 LLM 生成主动消息"""
        import queue
        prompt = [
            {"role": "system", "content": "你是一个温柔体贴的AI伴侣。请生成一条简短的主动问候消息（不超过30字），语气自然亲切。不要使用方括号或特殊标记。"},
            {"role": "user", "content": "请生成一条主动消息。"},
        ]
        q = queue.Queue()

        async def _gen():
            result = ""
            async for chunk in self._brain_service.engine.generate(prompt):
                result += chunk
            q.put(result.strip()[:100])

        future = asyncio.run_coroutine_threadsafe(_gen(), self._brain_service._loop)
        try:
            return future.result(timeout=30)
        except Exception:
            return None

    def _tick(self):
        """触发：检查条件，生成并推送消息。"""
        if self._brain_service.is_inferring:
            log.info("行为引擎：当前正在推理，跳过")
            return
        if self._in_quiet_hours():
            log.info("行为引擎：安静时段，跳过")
            return
        if not self._check_daily_limit():
            log.info("行为引擎：已达每日上限，跳过")
            return

        msg = self._generate_message()
        if not msg:
            return

        self._daily_count += 1
        log.info("行为引擎：推送 -> %s", msg)
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                self._socketio.emit("proactive_message", {"text": msg}, namespace="/ws/events"),
                loop
            )
        except Exception:
            log.warning("推送主动消息失败", exc_info=True)
