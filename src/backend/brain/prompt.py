"""Prompt 模板管理"""
from pathlib import Path
from src.backend.core.config import get, resolve_path
from src.backend.core.logger import get_logger

log = get_logger("prompt")

DEFAULT_SYSTEM_PROMPT = "回复时请在末尾附加一个 emotion_tag，格式为 [emotion:xxx]，xxx 可选值：happy, sad, angry, surprised, neutral, shy, excited。"


class PromptManager:
    def __init__(self):
        prompt_path = get("brain.system_prompt_path", "assets/prompts/system.txt")
        p = resolve_path(prompt_path)
        self.ai_name = get("ai_name", "AI")
        if p.exists():
            self.system_prompt = p.read_text(encoding="utf-8").replace("$name", self.ai_name)
            log.info(f"已加载系统 prompt: {prompt_path}")
        else:
            self.system_prompt = DEFAULT_SYSTEM_PROMPT
            log.info("使用默认系统 prompt")

    def build_messages(
        self, user_input: str, history: list[dict], memory_context: list[str] | None = None
    ) -> list[dict]:
        max_history = int(get("brain.max_history_messages", 20))
        messages = [{"role": "system", "content": self.system_prompt}]
        if memory_context:
            ctx = "\n".join(memory_context)
            messages.append({"role": "system", "content": f"相关记忆:\n{ctx}"})
        # 裁剪历史消息，只保留最近 N 条
        trimmed = history[-max_history:] if len(history) > max_history else history
        messages.extend(trimmed)
        messages.append({"role": "user", "content": user_input})
        return messages
