"""Допуск к боту: владелец по id и участники по имени Telegram."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import settings


def normalize_username(value: str) -> str:
    """Имя без @ в нижнем регистре. Пустая строка, если имени нет."""
    name = (value or "").strip().lstrip("@").casefold()
    if not name or any(char.isspace() for char in name):
        return ""
    return name


class AccessRegistry:
    """Список владельца и участников. Участник входит под своим именем Telegram."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._conn() as con:
            columns = {row[1] for row in con.execute("PRAGMA table_info(bot_members)")}
            if columns and "username" not in columns:
                con.execute("DROP TABLE bot_members")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_members (
                    username TEXT PRIMARY KEY,
                    telegram_id TEXT,
                    role TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_revoked (
                    username TEXT PRIMARY KEY
                )
                """
            )
            revoked = {row[0] for row in con.execute("SELECT username FROM bot_revoked")}
            for username in _configured_usernames():
                if username in revoked:
                    continue
                con.execute(
                    """
                    INSERT OR IGNORE INTO bot_members (username, telegram_id, role)
                    VALUES (?, NULL, 'user')
                    """,
                    (username,),
                )

    def is_allowed(self, telegram_id: str) -> bool:
        if not telegram_id:
            return False
        owner = settings.telegram_allowed_user_id
        if owner and telegram_id == owner:
            return True
        with self._conn() as con:
            row = con.execute(
                "SELECT 1 FROM bot_members WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        return row is not None

    def bind(self, telegram_id: str, username: str) -> str:
        """Привязывает аккаунт. «new» — первая привязка, «keep» — уже был, пусто — отказ."""
        normalized = normalize_username(username)
        if not telegram_id or not normalized:
            return ""
        with self._conn() as con:
            row = con.execute(
                "SELECT telegram_id FROM bot_members WHERE username = ?",
                (normalized,),
            ).fetchone()
            if row is None:
                return ""
            current = str(row[0] or "")
            if current and current != telegram_id:
                return ""
            if current == telegram_id:
                return "keep"
            con.execute(
                "UPDATE bot_members SET telegram_id = ? WHERE username = ?",
                (telegram_id, normalized),
            )
        return "new"

    def list_members(self) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT username, telegram_id FROM bot_members ORDER BY username"
            ).fetchall()
        return [{"username": str(row[0]), "telegram_id": str(row[1] or "")} for row in rows]

    def get_member(self, username: str) -> dict | None:
        normalized = normalize_username(username)
        if not normalized:
            return None
        with self._conn() as con:
            row = con.execute(
                "SELECT username, telegram_id FROM bot_members WHERE username = ?",
                (normalized,),
            ).fetchone()
        if row is None:
            return None
        return {"username": str(row[0]), "telegram_id": str(row[1] or "")}

    def username_of(self, telegram_id: str) -> str:
        if not telegram_id:
            return ""
        with self._conn() as con:
            row = con.execute(
                "SELECT username FROM bot_members WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        return str(row[0]) if row else ""

    def remove_member(self, username: str) -> str | None:
        """Убирает участника из списка. None — имени нет. Иначе его telegram id, возможно пустой."""
        normalized = normalize_username(username)
        if not normalized:
            return None
        with self._conn() as con:
            row = con.execute(
                "SELECT telegram_id FROM bot_members WHERE username = ?",
                (normalized,),
            ).fetchone()
            if row is None:
                return None
            con.execute(
                "INSERT OR REPLACE INTO bot_revoked (username) VALUES (?)",
                (normalized,),
            )
            con.execute("DELETE FROM bot_members WHERE username = ?", (normalized,))
        return str(row[0] or "")

    def add_member(self, username: str) -> bool:
        """Возвращает имя в список. False — имя пустое."""
        normalized = normalize_username(username)
        if not normalized:
            return False
        with self._conn() as con:
            con.execute("DELETE FROM bot_revoked WHERE username = ?", (normalized,))
            con.execute(
                """
                INSERT OR IGNORE INTO bot_members (username, telegram_id, role)
                VALUES (?, NULL, 'user')
                """,
                (normalized,),
            )
        return True


def _configured_usernames() -> list[str]:
    names: list[str] = []
    for raw in settings.bot_member_usernames.split(","):
        username = normalize_username(raw)
        if username and username not in names:
            names.append(username)
    return names
