from __future__ import annotations

import re

from app.tools.calendar.repository import CalendarRepository
from app.tools.calendar.schemas import PersonBirthday

_MONTH_WORDS: dict[str, int] = {
    "январь": 1,
    "января": 1,
    "январе": 1,
    "февраль": 2,
    "февраля": 2,
    "феврале": 2,
    "март": 3,
    "марта": 3,
    "марте": 3,
    "апрель": 4,
    "апреля": 4,
    "апреле": 4,
    "май": 5,
    "мая": 5,
    "мае": 5,
    "июнь": 6,
    "июня": 6,
    "июне": 6,
    "июль": 7,
    "июля": 7,
    "июле": 7,
    "август": 8,
    "августа": 8,
    "августе": 8,
    "сентябрь": 9,
    "сентября": 9,
    "сентябре": 9,
    "октябрь": 10,
    "октября": 10,
    "октябре": 10,
    "ноябрь": 11,
    "ноября": 11,
    "ноябре": 11,
    "декабрь": 12,
    "декабря": 12,
    "декабре": 12,
}
_BIRTHDAY_QUERY = re.compile(r"рожден|именин|календар", re.IGNORECASE)


class CalendarService:
    """Сервис календаря и именинников."""

    def __init__(self, repo: CalendarRepository) -> None:
        self.repo = repo

    def add_birthday(self, person: PersonBirthday) -> int:
        return self.repo.add_person(person)

    def list_month_birthdays(self, month: int) -> list[dict]:
        return self.repo.by_month(month)

    def search_fio(self, query: str) -> list[dict]:
        return self.repo.find_by_fio(query)

    def format_month_birthdays(self, month: int) -> str:
        """Строки «дата - ФИО» по возрастанию дня. Напоминания не включаются."""
        rows = self.list_month_birthdays(month)
        if not rows:
            return "В этом месяце дней рождения нет."
        lines: list[str] = []
        for row in rows:
            fio = " ".join(
                part.strip()
                for part in (row.get("last_name"), row.get("first_name"), row.get("middle_name"))
                if isinstance(part, str) and part.strip()
            )
            lines.append(f"{int(row['birth_day']):02d}.{int(row['birth_month']):02d} - {fio}")
        return "\n".join(lines)

    def answer_month_request(self, text: str) -> str | None:
        """Ответ на запрос дней рождения за месяц, если месяц в тексте указан."""
        if not text or not _BIRTHDAY_QUERY.search(text):
            return None
        month = parse_month(text)
        if month is None:
            return None
        return self.format_month_birthdays(month)


def parse_month(value: object) -> int | None:
    """Номер месяца из числа или русского названия."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 12 else None
    if isinstance(value, float) and value.is_integer():
        number = int(value)
        return number if 1 <= number <= 12 else None
    text = str(value or "").strip().lower().replace("ё", "е")
    if not text:
        return None
    if text.isdigit():
        number = int(text)
        return number if 1 <= number <= 12 else None
    words = re.findall(r"[0-9]+|[а-я]+", text)
    for word in words:
        month = _MONTH_WORDS.get(word)
        if month is not None:
            return month
    for word in words:
        if word.isdigit():
            number = int(word)
            if 1 <= number <= 12:
                return number
    return None
