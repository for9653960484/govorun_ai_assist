"""Стирает данные одного пользователя Telegram из всех хранилищ бота."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.config import settings
from app.tools.schedule.repository import ScheduleRepository
from app.tools.schedule.schemas import ScheduleError
from app.utils.logger import get_logger

_logger = get_logger(__name__)


def purge_user_data(user_id: str, *, db_path: Path | None = None) -> None:
    """Удаляет записи пользователя. Данные владельца не трогает."""
    if not user_id or user_id == settings.telegram_allowed_user_id:
        return
    _purge_sqlite(user_id, db_path or settings.sqlite_path)
    _purge_files(user_id)
    _purge_schedule(user_id)


def _purge_sqlite(user_id: str, db_path: Path) -> None:
    if not db_path.exists():
        return
    with sqlite3.connect(db_path) as con:
        if _has_table(con, "habits"):
            habit_ids = [
                row[0] for row in con.execute("SELECT id FROM habits WHERE user_id = ?", (user_id,))
            ]
            if habit_ids and _has_table(con, "habit_marks"):
                con.executemany(
                    "DELETE FROM habit_marks WHERE habit_id = ?",
                    [(habit_id,) for habit_id in habit_ids],
                )
            con.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
        if _has_table(con, "habit_reminders"):
            con.execute("DELETE FROM habit_reminders WHERE user_id = ?", (user_id,))
        if _has_table(con, "birthdays"):
            person_ids = [
                row[0]
                for row in con.execute("SELECT id FROM birthdays WHERE user_id = ?", (user_id,))
            ]
            if person_ids and _has_table(con, "reminders"):
                con.executemany(
                    "DELETE FROM reminders WHERE person_id = ?",
                    [(person_id,) for person_id in person_ids],
                )
            con.execute("DELETE FROM birthdays WHERE user_id = ?", (user_id,))
        if _has_table(con, "topics"):
            topic_ids = [
                row[0] for row in con.execute("SELECT id FROM topics WHERE user_id = ?", (user_id,))
            ]
            if topic_ids and _has_table(con, "notes"):
                con.executemany(
                    "DELETE FROM notes WHERE topic_id = ?",
                    [(topic_id,) for topic_id in topic_ids],
                )
            if topic_ids and _has_table(con, "saved_searches"):
                con.executemany(
                    "DELETE FROM saved_searches WHERE topic_id = ?",
                    [(topic_id,) for topic_id in topic_ids],
                )
            con.execute("DELETE FROM topics WHERE user_id = ?", (user_id,))
        if _has_table(con, "travel_trips"):
            trip_ids = [
                row[0]
                for row in con.execute("SELECT id FROM travel_trips WHERE user_id = ?", (user_id,))
            ]
            if trip_ids and _has_table(con, "travel_expenses"):
                con.executemany(
                    "DELETE FROM travel_expenses WHERE trip_id = ?",
                    [(trip_id,) for trip_id in trip_ids],
                )
            con.execute("DELETE FROM travel_trips WHERE user_id = ?", (user_id,))
        if _has_table(con, "travel_users"):
            con.execute("DELETE FROM travel_users WHERE user_id = ?", (user_id,))
        if _has_table(con, "travel_state"):
            con.execute("DELETE FROM travel_state WHERE user_id = ?", (user_id,))
        if _has_table(con, "users"):
            con.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


def _purge_files(user_id: str) -> None:
    raw_dir = settings.documents_raw_dir / user_id
    projects_dir = settings.data_root / "projects" / user_id
    for folder in (raw_dir, projects_dir):
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
    prefix = f"{user_id}_"
    for folder in (settings.documents_parsed_dir, settings.documents_index_dir):
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.name.startswith(prefix):
                path.unlink(missing_ok=True)


def _purge_schedule(user_id: str) -> None:
    if not settings.schedule_database_url:
        return
    try:
        ScheduleRepository(settings.schedule_database_url).delete_user(user_id)
    except ScheduleError as exc:
        _logger.warning("Кэш расписания пользователя не очищен: %s", exc.message)


def _has_table(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None
