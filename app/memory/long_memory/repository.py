from __future__ import annotations

import sqlite3
from pathlib import Path


class LongMemoryRepository:
    """Репозиторий тем, заметок и сохраненных поисков одного пользователя."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def list_topics(self, user_id: str) -> list[dict]:
        with self._conn() as con:
            cur = con.execute(
                "SELECT id, name, tag FROM topics WHERE user_id = ? ORDER BY id",
                (user_id,),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def create_topic(self, user_id: str, name: str, tag: str) -> int:
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO topics(user_id, name, tag) VALUES(?, ?, ?)",
                (user_id, name, tag),
            )
            return int(cur.lastrowid)

    def rename_topic_tag(self, user_id: str, old_tag: str, new_tag: str) -> bool:
        with self._conn() as con:
            cur = con.execute(
                "UPDATE topics SET tag = ? WHERE user_id = ? AND tag = ?",
                (new_tag, user_id, old_tag),
            )
            return cur.rowcount > 0

    def delete_topic_by_tag(self, user_id: str, tag: str) -> bool:
        with self._conn() as con:
            cur = con.execute(
                "SELECT id FROM topics WHERE user_id = ? AND tag = ?",
                (user_id, tag),
            )
            row = cur.fetchone()
            if not row:
                return False
            topic_id = int(row[0])
            con.execute("DELETE FROM notes WHERE topic_id = ?", (topic_id,))
            con.execute("DELETE FROM saved_searches WHERE topic_id = ?", (topic_id,))
            cur = con.execute(
                "DELETE FROM topics WHERE id = ? AND user_id = ?",
                (topic_id, user_id),
            )
            return cur.rowcount > 0

    def get_topic_by_tag(self, user_id: str, tag: str) -> dict | None:
        with self._conn() as con:
            cur = con.execute(
                "SELECT id, name, tag FROM topics WHERE user_id = ? AND tag = ?",
                (user_id, tag),
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip([c[0] for c in cur.description], row))

    def add_note(self, user_id: str, topic_id: int, content: str) -> int | None:
        with self._conn() as con:
            owned = con.execute(
                "SELECT 1 FROM topics WHERE id = ? AND user_id = ?",
                (topic_id, user_id),
            ).fetchone()
            if owned is None:
                return None
            cur = con.execute(
                "INSERT INTO notes(topic_id, content) VALUES(?, ?)",
                (topic_id, content),
            )
            return int(cur.lastrowid)

    def list_notes(self, user_id: str, topic_id: int) -> list[dict]:
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT n.content, n.created_at
                FROM notes AS n
                JOIN topics AS t ON t.id = n.topic_id
                WHERE t.user_id = ? AND n.topic_id = ?
                ORDER BY n.id ASC
                """,
                (user_id, topic_id),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def list_saved_searches(self, user_id: str, topic_id: int) -> list[dict]:
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT s.query, s.result, s.created_at
                FROM saved_searches AS s
                JOIN topics AS t ON t.id = s.topic_id
                WHERE t.user_id = ? AND s.topic_id = ?
                ORDER BY s.id ASC
                """,
                (user_id, topic_id),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def search_notes(self, user_id: str, topic_id: int, query: str) -> list[dict]:
        like = f"%{query}%"
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT n.id, n.content, n.created_at
                FROM notes AS n
                JOIN topics AS t ON t.id = n.topic_id
                WHERE t.user_id = ? AND n.topic_id = ? AND n.content LIKE ?
                ORDER BY n.created_at DESC
                """,
                (user_id, topic_id, like),
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def save_search_result(self, user_id: str, topic_id: int, query: str, result: str) -> int | None:
        with self._conn() as con:
            owned = con.execute(
                "SELECT 1 FROM topics WHERE id = ? AND user_id = ?",
                (topic_id, user_id),
            ).fetchone()
            if owned is None:
                return None
            cur = con.execute(
                "INSERT INTO saved_searches(topic_id, query, result) VALUES(?, ?, ?)",
                (topic_id, query, result),
            )
            return int(cur.lastrowid)
