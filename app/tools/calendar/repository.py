from __future__ import annotations

import sqlite3
from pathlib import Path

from app.tools.calendar.schemas import PersonBirthday


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

    def add_person(self, person: PersonBirthday) -> int:
        with self._conn() as con:
            cur = con.execute(
                """
                INSERT INTO birthdays(last_name, first_name, middle_name, birth_day, birth_month, birth_year)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (person.last_name, person.first_name, person.middle_name, person.day, person.month, person.year),
            )
            return int(cur.lastrowid)

    def find_by_fio(self, q: str) -> list[dict]:
        like = f"%{q}%"
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT id, last_name, first_name, middle_name, birth_day, birth_month, birth_year
                FROM birthdays
                WHERE last_name LIKE ? OR first_name LIKE ? OR middle_name LIKE ?
                ORDER BY last_name, first_name
                """,
                (like, like, like),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def by_month(self, month: int) -> list[dict]:
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT id, last_name, first_name, middle_name, birth_day, birth_month, birth_year
                FROM birthdays
                WHERE birth_month = ?
                ORDER BY birth_day
                """,
                (month,),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
