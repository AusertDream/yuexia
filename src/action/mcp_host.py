"""基础 MCP 宿主框架（预留）"""
from src.core.logger import get_logger

log = get_logger("mcp_host")


class MCPHost:
    """MCP 工具宿主，当前为占位实现"""

    def __init__(self):
        self.tools: dict[str, callable] = {}

    def register(self, name: str, func):
        self.tools[name] = func
        log.info(f"MCP 工具已注册: {name}")

    async def call(self, name: str, **kwargs):
        if name not in self.tools:
            log.warning(f"未知工具: {name}")
            return None
        return await self.tools[name](**kwargs)
