from __future__ import annotations

import sqlite3
from pathlib import Path

from app.memory.long_memory.tags import DEFAULT_TOPICS


class LongMemoryRepository:
    """Репозиторий тем, заметок и сохраненных поисков."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._seed_defaults()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _seed_defaults(self) -> None:
        with self._conn() as con:
            for item in DEFAULT_TOPICS:
                con.execute(
                    "INSERT OR IGNORE INTO topics(name, tag) VALUES(?, ?)",
                    (item["name"], item["tag"]),
                )

    def list_topics(self) -> list[dict]:
        with self._conn() as con:
            cur = con.execute("SELECT id, name, tag FROM topics ORDER BY id")
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def create_topic(self, name: str, tag: str) -> int:
        with self._conn() as con:
            cur = con.execute("INSERT INTO topics(name, tag) VALUES(?, ?)", (name, tag))
            return int(cur.lastrowid)

    def rename_topic_tag(self, old_tag: str, new_tag: str) -> bool:
        with self._conn() as con:
            cur = con.execute("UPDATE topics SET tag = ? WHERE tag = ?", (new_tag, old_tag))
            return cur.rowcount > 0

    def delete_topic_by_tag(self, tag: str) -> bool:
        with self._conn() as con:
            cur = con.execute("SELECT id FROM topics WHERE tag = ?", (tag,))
            row = cur.fetchone()
            if not row:
                return False
            topic_id = int(row[0])
            con.execute("DELETE FROM notes WHERE topic_id = ?", (topic_id,))
            con.execute("DELETE FROM saved_searches WHERE topic_id = ?", (topic_id,))
            cur = con.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
            return cur.rowcount > 0

    def get_topic_by_tag(self, tag: str) -> dict | None:
        with self._conn() as con:
            cur = con.execute("SELECT id, name, tag FROM topics WHERE tag = ?", (tag,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip([c[0] for c in cur.description], row))

    def add_note(self, topic_id: int, content: str) -> int:
        with self._conn() as con:
            cur = con.execute("INSERT INTO notes(topic_id, content) VALUES(?, ?)", (topic_id, content))
            return int(cur.lastrowid)

    def search_notes(self, topic_id: int, query: str) -> list[dict]:
        like = f"%{query}%"
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT id, content, created_at
                FROM notes
                WHERE topic_id = ? AND content LIKE ?
                ORDER BY created_at DESC
                """,
                (topic_id, like),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def save_search_result(self, topic_id: int, query: str, result: str) -> int:
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO saved_searches(topic_id, query, result) VALUES(?, ?, ?)",
                (topic_id, query, result),
            )
            return int(cur.lastrowid)
