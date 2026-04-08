from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult


class CryptoStubTool(BaseTool):
    name = "crypto_stub"
    description = "Безопасная заглушка криптовалют"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "Символ"}},
                "required": ["symbol"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        symbol = kwargs.get("symbol", "")
        # TODO: подключить крипто-биржу.
        return ToolResult(ok=True, message=f"Данные по '{symbol}' недоступны (заглушка).")
