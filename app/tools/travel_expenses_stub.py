from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult


class TravelExpensesStubTool(BaseTool):
    name = "travel_expenses_stub"
    description = "Безопасная заглушка расходов в поездках"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_name": {"type": "string", "description": "Название поездки"},
                    "amount": {"type": "number", "description": "Сумма"},
                },
                "required": ["trip_name", "amount"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        trip_name = kwargs.get("trip_name", "")
        amount = kwargs.get("amount", 0)
        # TODO: подключить постоянное хранилище и аналитику.
        return ToolResult(ok=True, message=f"Расход {amount} для '{trip_name}' принят (заглушка).")
