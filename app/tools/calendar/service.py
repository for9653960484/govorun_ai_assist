from __future__ import annotations

from app.tools.calendar.repository import CalendarRepository
from app.tools.calendar.schemas import PersonBirthday


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
