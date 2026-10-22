from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import settings


class LongMemoryStore:
    """Инициализация SQLite-хранилища долгой памяти."""

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
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    UNIQUE(user_id, name),
                    UNIQUE(user_id, tag)
                )
                """
            )
            _own_topics(con)
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(topic_id) REFERENCES topics(id)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(topic_id) REFERENCES topics(id)
                )
                """
            )


def _own_topics(con: sqlite3.Connection) -> None:
    """Старые общие темы закрепляет за владельцем и даёт каждой теме своего пользователя."""
    columns = {row[1] for row in con.execute("PRAGMA table_info(topics)")}
    if not columns:
        return
    owner = settings.telegram_allowed_user_id or ""
    if "user_id" not in columns:
        con.execute(
            """
            CREATE TABLE topics_owned (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                tag TEXT NOT NULL,
                UNIQUE(user_id, name),
                UNIQUE(user_id, tag)
            )
            """
        )
        con.execute(
            "INSERT INTO topics_owned (id, user_id, name, tag) SELECT id, ?, name, tag FROM topics",
            (owner,),
        )
        con.execute("DROP TABLE topics")
        con.execute("ALTER TABLE topics_owned RENAME TO topics")
        return
    if owner:
        con.execute("UPDATE topics SET user_id = ? WHERE user_id = ''", (owner,))
