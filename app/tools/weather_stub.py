from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult


class WeatherStubTool(BaseTool):
    name = "weather_stub"
    description = "Безопасная заглушка погоды"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "Город"}},
                "required": ["city"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        city = kwargs.get("city", "")
        # TODO: подключить реальный провайдер погоды.
        return ToolResult(ok=True, message=f"Погода для '{city}' временно недоступна (заглушка).")
