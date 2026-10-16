from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult
from app.tools.calendar.service import CalendarService, parse_month


class CalendarTool(BaseTool):
    name = "calendar"
    description = (
        "Список дней рождения за указанный месяц. "
        "Верни пользователю только готовые строки «дата - ФИО» по возрастанию даты. "
        "Напоминания не упоминай."
    )
    menu_title = "Календарь"
    menu_hint = "Дни рождения за месяц: дата и ФИО, без напоминаний."

    def __init__(self, service: CalendarService) -> None:
        self._service = service

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Месяц: число 1-12 или название, например март",
                    },
                },
                "required": ["month"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        month = parse_month(kwargs.get("month"))
        if month is None:
            return ToolResult(ok=False, message="Укажите месяц, например: март.")
        return ToolResult(ok=True, message=self._service.format_month_birthdays(month))
