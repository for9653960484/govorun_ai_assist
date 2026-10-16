from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult
from app.tools.travel.service import TravelService


class TravelTool(BaseTool):
    name = "travel"
    description = (
        "Планирование поездки и учёт расходов: создать поездку, баланс, "
        "расход в валюте назначения, история, курс, завершить. "
        "Верни пользователю готовый текст инструмента."
    )
    menu_title = "Путешествие"
    menu_hint = "Поездка, курс и расходы. Создать: новая поездка."

    def __init__(self, service: TravelService) -> None:
        self._service = service
        self._user_id = ""

    def bind(self, user_id: str) -> None:
        self._user_id = user_id

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Команда: новая поездка, баланс, история, расход 1200 такси, курс 92.5, завершить",
                    },
                },
                "required": ["text"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        user_id = str(kwargs.get("user_id") or self._user_id)
        text = str(kwargs.get("text") or "").strip()
        if not text:
            return ToolResult(ok=True, message=self._service.menu_text(user_id))
        answer = self._service.answer(user_id, text)
        if answer is None:
            return ToolResult(ok=True, message=self._service.menu_text(user_id))
        return ToolResult(ok=True, message=answer)
