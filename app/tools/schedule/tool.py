from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult
from app.tools.schedule.service import ScheduleService


class ScheduleTool(BaseTool):
    name = "schedule"
    description = (
        "Личное расписание владельца в Google Календаре. "
        "Команды: сегодня, неделя, создать, изменить, перенести, удалить, напоминание. "
        "Передай фразу пользователя в text и покажи ответ дословно."
    )
    menu_title = "Расписание"
    menu_hint = ""

    def __init__(self, service: ScheduleService) -> None:
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
                        "description": "Команда или ответ шага: сегодня, неделя, создать, изменить, перенести, удалить, напоминание",
                    },
                },
                "required": ["text"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        user_id = str(kwargs.get("user_id") or self._user_id)
        text = str(kwargs.get("text") or "").strip()
        if not self._service.allowed(user_id):
            return ToolResult(ok=False, message=self._service.deny_text())
        if not text:
            return ToolResult(ok=True, message=self._service.open_text())
        reply = self._service.answer(user_id, text)
        return ToolResult(ok=True, message=reply.text)
