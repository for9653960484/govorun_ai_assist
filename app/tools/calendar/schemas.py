from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PersonBirthday:
    """Сущность записи календаря по ФИО и дате рождения."""

    last_name: str
    first_name: str
    middle_name: str
    day: int
    month: int
    year: int
