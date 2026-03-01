"""AI 日记：对话结束后生成日记条目"""
from pathlib import Path
from datetime import datetime
import json
from src.backend.core.config import get, resolve_path
from src.backend.core.logger import get_logger

log = get_logger("diary")


class DiaryWriter:
    def __init__(self):
        self.output_dir = resolve_path(get("diary.output_dir", "data/diary"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.output_dir / ".diary_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """加载日记生成状态"""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                log.debug("状态文件读取失败，使用空状态")
        return {}

    def _save_state(self):
        """保存日记生成状态"""
        try:
            self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            log.debug("状态文件保存失败", exc_info=True)

    def _should_generate(self, diary_type: str) -> bool:
        """判断是否应该生成该类型的日记"""
        last_time_str = self.state.get(f"{diary_type}_last")
        if not last_time_str:
            return True
        try:
            last_time = datetime.fromisoformat(last_time_str)
        except ValueError:
            return True
        now = datetime.now()
        intervals = {
            "daily": lambda: now.date() > last_time.date(),
            "weekly": lambda: (now - last_time).days >= 7,
            "monthly": lambda: (now.year, now.month) > (last_time.year, last_time.month),
            "yearly": lambda: now.year > last_time.year,
        }
        check = intervals.get(diary_type)
        return check() if check else True

    def _update_state(self, diary_type: str):
        """更新日记生成状态"""
        self.state[f"{diary_type}_last"] = datetime.now().isoformat()
        self._save_state()

    async def write(self, conversation: list[dict], engine, diary_type: str = "daily") -> str:
        """用 LLM 生成日记条目并保存

        Args:
            conversation: 对话历史
            engine: LLM 引擎
            diary_type: 日记类型（daily/weekly/monthly/yearly）
        """
        # 频率检查
        if not self._should_generate(diary_type):
            log.debug(f"{diary_type} 日记尚未到生成时间，跳过")
            return ""

        # 获取对应类型的配置
        config_key = f"diary.{diary_type}"
        enabled = get(f"{config_key}.enabled", False)
        if not enabled:
            log.debug(f"{diary_type} 日记未启用")
            return ""

        # 获取自定义提示词，如果没有则使用默认提示词
        custom_prompt = get(f"{config_key}.prompt", "")
        if not custom_prompt:
            custom_prompt = self._get_default_prompt(diary_type)

        diary_prompt = [
            {"role": "system", "content": custom_prompt},
            {"role": "user", "content": self._format_conversation(conversation)},
        ]

        chunks = []
        async for chunk in engine.generate(diary_prompt):
            chunks.append(chunk)
        content = "".join(chunks)

        now = datetime.now()
        # 根据日记类型使用不同的文件名前缀
        type_prefix = {"daily": "日记", "weekly": "周记", "monthly": "月记", "yearly": "年记"}
        prefix = type_prefix.get(diary_type, diary_type)
        path = self.output_dir / f"{prefix}_{now.strftime('%Y-%m-%d_%H%M%S')}.md"
        path.write_text(f"# {prefix} - {now.strftime('%Y年%m月%d日 %H:%M')}\n\n{content}\n", encoding="utf-8")
        log.info(f"{prefix}已保存: {path}")
        self._update_state(diary_type)
        return content

    def _get_default_prompt(self, diary_type: str) -> str:
        """获取默认提示词"""
        prompts = {
            "daily": "请以第一人称写一篇简短的日记，记录这次对话的内容、你的感受和思考。用自然亲切的语气，像真的在写日记一样。",
            "weekly": "请以第一人称写一篇周记，总结本周的对话内容、主要活动、成长和感悟。",
            "monthly": "请以第一人称写一篇月记，总结本月的对话内容、重要变化、成就和反思。",
            "yearly": "请以第一人称写一篇年记，总结今年的对话内容、成长轨迹、重大事件和人生感悟。",
        }
        return prompts.get(diary_type, prompts["daily"])

    def _format_conversation(self, conversation: list[dict]) -> str:
        lines = []
        for msg in conversation:
            role = "用户" if msg["role"] == "user" else get("ai_name", "AI")
            lines.append(f"{role}: {msg['content']}")
        return "以下是刚才的对话:\n" + "\n".join(lines)
