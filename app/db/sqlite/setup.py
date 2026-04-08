from __future__ import annotations

from app.config import settings
from app.memory.long_memory.store import LongMemoryStore
from app.tools.calendar.repository import CalendarRepository
from app.db.repositories import UserRepository


def init_all_sqlite() -> None:
    """Создает все необходимые SQLite-таблицы."""
    LongMemoryStore(settings.sqlite_path)
    CalendarRepository(settings.sqlite_path)
    UserRepository(settings.sqlite_path)
