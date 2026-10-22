from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class ScheduleError(Exception):
    """Ошибка расписания, которую можно показать владельцу."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(slots=True)
class CalendarEvent:
    """Событие Google Календаря."""

    uid: str
    href: str
    etag: str
    summary: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    sequence: int = 0
    birthday: bool = False


@dataclass(slots=True)
class ScheduleReply:
    """Ответ раздела и какая клавиатура нужна дальше."""

    text: str
    keyboard: str = "schedule"
