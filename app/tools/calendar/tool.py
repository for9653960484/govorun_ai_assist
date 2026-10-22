from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult
from app.tools.calendar.schemas import PersonBirthday
from app.tools.calendar.service import CalendarService, parse_month


class CalendarTool(BaseTool):
    name = "calendar"
    description = (
        "Дни рождения в базе. Команды: запиши, выведи, удали. "
        "Передай фразу пользователя в text и покажи ответ дословно, "
        "строками «ДД.ММ - фамилия имя»."
    )
    menu_title = "Дни рождения"
    menu_hint = "Дни рождения: запиши, выведи месяц или год, удали по имени."

    def __init__(self, service: CalendarService) -> None:
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
                    "month": {
                        "type": "string",
                        "description": "Месяц списка: число 1-12 или название, например март",
                    },
                    "text": {
                        "type": "string",
                        "description": "Фраза с датой и ФИО, например: 12 октября Иванов Иван",
                    },
                    "day": {"type": "integer", "description": "День рождения"},
                    "last_name": {"type": "string", "description": "Фамилия"},
                    "first_name": {"type": "string", "description": "Имя"},
                    "middle_name": {"type": "string", "description": "Отчество, если есть"},
                    "year": {"type": "integer", "description": "Год, если известен"},
                },
                "required": [],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        phrase = str(kwargs.get("text") or "").strip()
        if phrase:
            answer = self._service.answer_request(self._user_id, phrase, capture=True)
            if answer is None:
                return ToolResult(ok=False, message=self._service.section_hint())
            return ToolResult(ok=True, message=answer)

        day = _as_int(kwargs.get("day"))
        month = parse_month(kwargs.get("month"))
        last_name = str(kwargs.get("last_name") or "").strip()
        first_name = str(kwargs.get("first_name") or "").strip()
        if day and month and last_name and first_name:
            year = _as_int(kwargs.get("year")) or 0
            person = PersonBirthday(
                last_name,
                first_name,
                str(kwargs.get("middle_name") or "").strip(),
                day,
                month,
                year,
            )
            return ToolResult(ok=True, message=self._service.save_birthday(self._user_id, person))

        if month is None:
            return ToolResult(ok=False, message="Укажите месяц, например: март.")
        return ToolResult(ok=True, message=self._service.format_month_birthdays(self._user_id, month))


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = str(value).strip()
    return int(text) if text.isdigit() else None
