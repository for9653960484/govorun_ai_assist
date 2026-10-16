from __future__ import annotations

import re
from datetime import date, timedelta

from app.tools.habits.repository import HabitsRepository
from app.tools.habits.schemas import Habit

MAX_HABITS = 5
_WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
_DONE = "🟢"
_MISSED = "🔴"
_ADD = re.compile(r"^(?:добавить|добавь)\s+привычк[уа]\s+(.+)$", re.IGNORECASE)
_DELETE = re.compile(r"^(?:удалить|удали)\s+привычк[уа]\s+(.+)$", re.IGNORECASE)
_RENAME = re.compile(
    r"^(?:переименовать|переименуй)\s+привычк[уа]\s+(.+?)\s+в\s+(.+)$",
    re.IGNORECASE,
)
_DONE_CMD = re.compile(r"^(?:сделал|сделала|отметить|отметь)\s+(.+)$", re.IGNORECASE)
_SHOW = re.compile(r"^(?:привычки|трекер привычек)$", re.IGNORECASE)


class HabitsService:
    """Список привычек и отметки за текущую неделю."""

    def __init__(self, repo: HabitsRepository) -> None:
        self.repo = repo

    def week_board(self, user_id: str, today: date | None = None) -> str:
        current = today or date.today()
        monday = current - timedelta(days=current.weekday())
        days = [monday + timedelta(days=offset) for offset in range(7)]
        habits = self.repo.list_habits(user_id)
        marks = self.repo.marks_between(user_id, days[0].isoformat(), days[-1].isoformat())
        example = habits[0].title if habits else "зарядка"
        lines = [
            "Трекер привычек",
            f"{_DONE} сделано, {_MISSED} не сделано",
            f"Отметить сегодня: сделал {example}",
            " ".join(_WEEKDAYS),
        ]
        if not habits:
            lines.append("Список пуст.")
            return "\n".join(lines)
        for index, habit in enumerate(habits, start=1):
            circles = [
                _DONE if (habit.id, day.isoformat()) in marks else _MISSED
                for day in days
            ]
            lines.append(f"{index}. {habit.title}")
            lines.append(" ".join(circles))
        return "\n".join(lines)

    def add_habit(self, user_id: str, title: str) -> str:
        name = _clean_title(title)
        if not name:
            return "Укажите название привычки."
        habits = self.repo.list_habits(user_id)
        if len(habits) >= MAX_HABITS:
            return "Можно вести не больше 5 привычек."
        if _find(habits, name) is not None:
            return "Такая привычка уже есть."
        self.repo.add_habit(user_id, name)
        return self.week_board(user_id)

    def delete_habit(self, user_id: str, query: str) -> str:
        habit = _find(self.repo.list_habits(user_id), query)
        if habit is None:
            return "Привычка не найдена."
        self.repo.delete_habit(habit.id)
        return self.week_board(user_id)

    def rename_habit(self, user_id: str, query: str, new_title: str) -> str:
        name = _clean_title(new_title)
        if not name:
            return "Укажите новое название."
        habits = self.repo.list_habits(user_id)
        habit = _find(habits, query)
        if habit is None:
            return "Привычка не найдена."
        other = _find(habits, name)
        if other is not None and other.id != habit.id:
            return "Такая привычка уже есть."
        self.repo.rename_habit(habit.id, name)
        return self.week_board(user_id)

    def mark_today(self, user_id: str, query: str, today: date | None = None) -> str | None:
        habit = _find(self.repo.list_habits(user_id), query)
        if habit is None:
            return None
        day = (today or date.today()).isoformat()
        self.repo.mark(habit.id, day)
        return self.week_board(user_id, today)

    def reminder_text(self, user_id: str, today: date | None = None) -> str | None:
        """Краткий текст, если к 15:00 есть неотмеченные привычки."""
        current = (today or date.today()).isoformat()
        if self.repo.reminder_sent(user_id, current):
            return None
        habits = self.repo.list_habits(user_id)
        if not habits:
            return None
        marks = self.repo.marks_between(user_id, current, current)
        pending = [habit.title for habit in habits if (habit.id, current) not in marks]
        if not pending:
            return None
        return f"Не отмечено: {', '.join(pending)}."

    def remember_reminder(self, user_id: str, today: date | None = None) -> None:
        current = (today or date.today()).isoformat()
        self.repo.mark_reminder_sent(user_id, current)

    def answer_request(self, user_id: str, text: str) -> str | None:
        """Команда списка, правки или отметки. Иначе None."""
        raw = " ".join((text or "").split())
        if not raw:
            return None
        if _SHOW.fullmatch(raw):
            return self.week_board(user_id)
        if match := _ADD.fullmatch(raw):
            return self.add_habit(user_id, match.group(1))
        if match := _DELETE.fullmatch(raw):
            return self.delete_habit(user_id, match.group(1))
        if match := _RENAME.fullmatch(raw):
            return self.rename_habit(user_id, match.group(1), match.group(2))
        if match := _DONE_CMD.fullmatch(raw):
            return self.mark_today(user_id, match.group(1))
        return None


def _clean_title(title: str) -> str:
    return " ".join(title.replace("ё", "е").split())[:40].strip()


def _find(habits: list[Habit], query: str) -> Habit | None:
    needle = " ".join(query.replace("ё", "е").split()).casefold()
    if needle.isdigit():
        index = int(needle)
        if 1 <= index <= len(habits):
            return habits[index - 1]
        return None
    for habit in habits:
        if _same_habit(habit.title.casefold(), needle):
            return habit
    return None


def _same_habit(title: str, query: str) -> bool:
    if title == query:
        return True
    return _stem(title) == _stem(query) and abs(len(title) - len(query)) <= 2


def _stem(value: str) -> str:
    for suffix in ("ами", "ого", "ому", "ыми", "ими", "ая", "яя", "ую", "юю", "ой", "ий", "ый", "ом", "ем", "ах", "ях", "ов", "ев", "ам", "ям", "а", "я", "у", "ю", "е", "и", "ы", "о"):
        if len(value) > len(suffix) + 2 and value.endswith(suffix):
            return value[: -len(suffix)]
    return value
