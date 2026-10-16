from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult
from app.tools.habits.service import HabitsService


class HabitsTool(BaseTool):
    name = "habits"
    description = (
        "Трекер привычек: до 5 регулярных действий. "
        "Список за неделю, добавление, удаление, переименование и отметка за сегодня. "
        "Верни пользователю готовый текст инструмента."
    )
    menu_title = "Привычки"
    menu_hint = "До 5 привычек: список за неделю и отметка за сегодня."

    def __init__(self, service: HabitsService) -> None:
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
                    "action": {
                        "type": "string",
                        "description": "list, add, delete, rename или done",
                        "enum": ["list", "add", "delete", "rename", "done"],
                    },
                    "name": {"type": "string", "description": "Название или номер привычки"},
                    "new_name": {"type": "string", "description": "Новое название при переименовании"},
                },
                "required": ["action"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        user_id = str(kwargs.get("user_id") or self._user_id)
        action = str(kwargs.get("action") or "list").strip().lower()
        name = str(kwargs.get("name") or "")
        new_name = str(kwargs.get("new_name") or "")
        if action == "add":
            return ToolResult(ok=True, message=self._service.add_habit(user_id, name))
        if action == "delete":
            return ToolResult(ok=True, message=self._service.delete_habit(user_id, name))
        if action == "rename":
            return ToolResult(ok=True, message=self._service.rename_habit(user_id, name, new_name))
        if action == "done":
            marked = self._service.mark_today(user_id, name)
            if marked is None:
                return ToolResult(ok=False, message="Привычка не найдена.")
            return ToolResult(ok=True, message=marked)
        return ToolResult(ok=True, message=self._service.week_board(user_id))
