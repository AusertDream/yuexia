"""AI 日记：对话结束后生成日记条目"""
from pathlib import Path
from datetime import datetime
from src.core.config import get
from src.core.logger import get_logger

log = get_logger("diary")


class DiaryWriter:
    def __init__(self):
        self.output_dir = Path(get("diary.output_dir", "data/diary"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def write(self, conversation: list[dict], engine) -> str:
        """用 LLM 生成日记条目并保存"""
        diary_prompt = [
            {"role": "system", "content": (
                "请以第一人称写一篇简短的日记，记录这次对话的内容、"
                "你的感受和思考。用自然亲切的语气，像真的在写日记一样。"
            )},
            {"role": "user", "content": self._format_conversation(conversation)},
        ]
        chunks = []
        async for chunk in engine.generate(diary_prompt):
            chunks.append(chunk)
        content = "".join(chunks)

        now = datetime.now()
        path = self.output_dir / f"{now.strftime('%Y-%m-%d_%H%M%S')}.md"
        path.write_text(f"# {now.strftime('%Y年%m月%d日 %H:%M')}\n\n{content}\n", encoding="utf-8")
        log.info(f"日记已保存: {path}")
        return content

    def _format_conversation(self, conversation: list[dict]) -> str:
        lines = []
        for msg in conversation:
            role = "用户" if msg["role"] == "user" else get("ai_name", "AI")
            lines.append(f"{role}: {msg['content']}")
        return "以下是刚才的对话:\n" + "\n".join(lines)
