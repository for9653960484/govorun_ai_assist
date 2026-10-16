from __future__ import annotations

import sqlite3
from pathlib import Path

from app.tools.habits.schemas import Habit


class HabitsRepository:
    """Хранилище привычек и отметок за день."""

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
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    position INTEGER NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS habit_marks (
                    habit_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    PRIMARY KEY (habit_id, day),
                    FOREIGN KEY(habit_id) REFERENCES habits(id)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS habit_reminders (
                    user_id TEXT NOT NULL,
                    day TEXT NOT NULL,
                    PRIMARY KEY (user_id, day)
                )
                """
            )

    def list_habits(self, user_id: str) -> list[Habit]:
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT id, user_id, title, position
                FROM habits
                WHERE user_id = ?
                ORDER BY position, id
                """,
                (user_id,),
            )
            return [Habit(int(row[0]), str(row[1]), str(row[2]), int(row[3])) for row in cur.fetchall()]

    def add_habit(self, user_id: str, title: str) -> int:
        with self._conn() as con:
            cur = con.execute(
                "SELECT COALESCE(MAX(position), 0) FROM habits WHERE user_id = ?",
                (user_id,),
            )
            position = int(cur.fetchone()[0]) + 1
            inserted = con.execute(
                "INSERT INTO habits(user_id, title, position) VALUES(?, ?, ?)",
                (user_id, title, position),
            )
            return int(inserted.lastrowid)

    def rename_habit(self, habit_id: int, title: str) -> None:
        with self._conn() as con:
            con.execute("UPDATE habits SET title = ? WHERE id = ?", (title, habit_id))

    def delete_habit(self, habit_id: int) -> None:
        with self._conn() as con:
            con.execute("DELETE FROM habit_marks WHERE habit_id = ?", (habit_id,))
            con.execute("DELETE FROM habits WHERE id = ?", (habit_id,))

    def mark(self, habit_id: int, day: str) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR IGNORE INTO habit_marks(habit_id, day) VALUES(?, ?)",
                (habit_id, day),
            )

    def marks_between(self, user_id: str, start_day: str, end_day: str) -> set[tuple[int, str]]:
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT m.habit_id, m.day
                FROM habit_marks AS m
                JOIN habits AS h ON h.id = m.habit_id
                WHERE h.user_id = ? AND m.day >= ? AND m.day <= ?
                """,
                (user_id, start_day, end_day),
            )
            return {(int(row[0]), str(row[1])) for row in cur.fetchall()}

    def list_user_ids(self) -> list[str]:
        with self._conn() as con:
            cur = con.execute("SELECT DISTINCT user_id FROM habits")
            return [str(row[0]) for row in cur.fetchall()]

    def reminder_sent(self, user_id: str, day: str) -> bool:
        with self._conn() as con:
            cur = con.execute(
                "SELECT 1 FROM habit_reminders WHERE user_id = ? AND day = ?",
                (user_id, day),
            )
            return cur.fetchone() is not None

    def mark_reminder_sent(self, user_id: str, day: str) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR IGNORE INTO habit_reminders(user_id, day) VALUES(?, ?)",
                (user_id, day),
            )
