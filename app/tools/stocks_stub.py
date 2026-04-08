from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult


class StocksStubTool(BaseTool):
    name = "stocks_stub"
    description = "Безопасная заглушка котировок"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {"ticker": {"type": "string", "description": "Тикер"}},
                "required": ["ticker"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        ticker = kwargs.get("ticker", "")
        # TODO: подключить биржевой API.
        return ToolResult(ok=True, message=f"Котировка '{ticker}' недоступна (заглушка).")
