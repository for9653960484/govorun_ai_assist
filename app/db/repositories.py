from __future__ import annotations

import sqlite3
from pathlib import Path


class UserRepository:
    """Репозиторий пользовательских настроек."""

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
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    active_tag TEXT
                )
                """
            )

    def get_active_tag(self, user_id: str) -> str | None:
        with self._conn() as con:
            cur = con.execute("SELECT active_tag FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def set_active_tag(self, user_id: str, tag: str | None) -> None:
        with self._conn() as con:
            con.execute(
                """
                INSERT INTO users(user_id, active_tag) VALUES(?, ?)
                ON CONFLICT(user_id) DO UPDATE SET active_tag=excluded.active_tag
                """,
                (user_id, tag),
            )
