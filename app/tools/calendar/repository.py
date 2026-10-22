from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import settings
from app.tools.calendar.schemas import PersonBirthday

_PERSON_COLUMNS = (
    "id, last_name, first_name, middle_name, birth_day, birth_month, birth_year, google_event_id, user_id"
)


class CalendarRepository:
    """Репозиторий календаря и напоминаний."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._conn() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS birthdays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_name TEXT NOT NULL,
                    first_name TEXT NOT NULL,
                    middle_name TEXT NOT NULL,
                    birth_day INTEGER NOT NULL,
                    birth_month INTEGER NOT NULL,
                    birth_year INTEGER NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER,
                    remind_at TEXT NOT NULL,
                    note TEXT,
                    FOREIGN KEY(person_id) REFERENCES birthdays(id)
                )
                """
            )
            columns = {row[1] for row in con.execute("PRAGMA table_info(birthdays)")}
            if "google_event_id" not in columns:
                con.execute("ALTER TABLE birthdays ADD COLUMN google_event_id TEXT")
            if "user_id" not in columns:
                con.execute("ALTER TABLE birthdays ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
            owner = settings.telegram_allowed_user_id
            if owner:
                con.execute("UPDATE birthdays SET user_id = ? WHERE user_id = ''", (owner,))

    def add_person(self, user_id: str, person: PersonBirthday) -> int:
        with self._conn() as con:
            cur = con.execute(
                """
                INSERT INTO birthdays(
                    last_name, first_name, middle_name, birth_day, birth_month, birth_year, user_id
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    person.last_name,
                    person.first_name,
                    person.middle_name,
                    person.day,
                    person.month,
                    person.year,
                    user_id,
                ),
            )
            return int(cur.lastrowid)

    def find_by_fio(self, user_id: str, q: str) -> list[dict]:
        like = f"%{q}%"
        with self._conn() as con:
            cur = con.execute(
                f"""
                SELECT {_PERSON_COLUMNS}
                FROM birthdays
                WHERE user_id = ?
                  AND (last_name LIKE ? OR first_name LIKE ? OR middle_name LIKE ?)
                ORDER BY last_name, first_name
                """,
                (user_id, like, like, like),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def all_people(self, user_id: str) -> list[dict]:
        with self._conn() as con:
            cur = con.execute(
                f"""
                SELECT {_PERSON_COLUMNS}
                FROM birthdays
                WHERE user_id = ?
                ORDER BY birth_month ASC, birth_day ASC, last_name, first_name
                """,
                (user_id,),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def get_person(self, user_id: str, person_id: int) -> dict | None:
        with self._conn() as con:
            cur = con.execute(
                f"""
                SELECT {_PERSON_COLUMNS}
                FROM birthdays
                WHERE id = ? AND user_id = ?
                """,
                (person_id, user_id),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return dict(zip([c[0] for c in cur.description], row))

    def set_google_event_id(self, user_id: str, person_id: int, event_id: str) -> None:
        with self._conn() as con:
            con.execute(
                "UPDATE birthdays SET google_event_id = ? WHERE id = ? AND user_id = ?",
                (event_id, person_id, user_id),
            )

    def delete_person(self, user_id: str, person_id: int) -> None:
        with self._conn() as con:
            owned = con.execute(
                "SELECT 1 FROM birthdays WHERE id = ? AND user_id = ?",
                (person_id, user_id),
            ).fetchone()
            if owned is None:
                return
            con.execute("DELETE FROM reminders WHERE person_id = ?", (person_id,))
            con.execute("DELETE FROM birthdays WHERE id = ? AND user_id = ?", (person_id, user_id))

    def by_month(self, user_id: str, month: int) -> list[dict]:
        with self._conn() as con:
            cur = con.execute(
                f"""
                SELECT {_PERSON_COLUMNS}
                FROM birthdays
                WHERE user_id = ? AND birth_month = ?
                ORDER BY birth_day ASC, last_name, first_name
                """,
                (user_id, month),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
