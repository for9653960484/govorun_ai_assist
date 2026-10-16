from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TravelRepository:
    """Поездки, курсы и расходы в общей базе проекта."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_users (
                    user_id TEXT PRIMARY KEY,
                    active_trip_id INTEGER,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    home_country TEXT,
                    dest_country TEXT,
                    home_currency TEXT NOT NULL,
                    dest_currency TEXT NOT NULL,
                    rate REAL NOT NULL,
                    rate_source TEXT NOT NULL,
                    balance_home REAL NOT NULL,
                    balance_dest REAL NOT NULL,
                    status TEXT NOT NULL,
                    completed_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    amount_dest REAL NOT NULL,
                    amount_home REAL NOT NULL,
                    comment TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_state (
                    user_id TEXT PRIMARY KEY,
                    state TEXT,
                    data TEXT
                )
                """
            )

    def ensure_user(self, user_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO travel_users (user_id, active_trip_id, created_at)
                VALUES (?, NULL, ?)
                """,
                (user_id, _now()),
            )

    def get_state(self, user_id: str) -> tuple[str | None, dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT state, data FROM travel_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row or not row["state"]:
            return None, {}
        data = json.loads(row["data"]) if row["data"] else {}
        return str(row["state"]), data

    def set_state(self, user_id: str, state: str | None, data: dict | None = None) -> None:
        self.ensure_user(user_id)
        with self._conn() as conn:
            if state is None:
                conn.execute("DELETE FROM travel_state WHERE user_id = ?", (user_id,))
                return
            payload = json.dumps(data or {}, ensure_ascii=False)
            conn.execute(
                """
                INSERT INTO travel_state (user_id, state, data)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET state = excluded.state, data = excluded.data
                """,
                (user_id, state, payload),
            )

    def list_active(self, user_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM travel_trips
                WHERE user_id = ? AND status = 'active'
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active(self, user_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT t.* FROM travel_trips t
                JOIN travel_users u ON u.active_trip_id = t.id
                WHERE u.user_id = ? AND t.status = 'active'
                """,
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def set_active(self, user_id: str, trip_id: int) -> None:
        self.ensure_user(user_id)
        with self._conn() as conn:
            conn.execute(
                "UPDATE travel_users SET active_trip_id = ? WHERE user_id = ?",
                (trip_id, user_id),
            )

    def create_trip(self, user_id: str, fields: dict) -> int:
        self.ensure_user(user_id)
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO travel_trips (
                    user_id, name, home_country, dest_country, home_currency, dest_currency,
                    rate, rate_source, balance_home, balance_dest, status, completed_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', NULL, ?)
                """,
                (
                    user_id,
                    fields["name"],
                    fields.get("home_country", ""),
                    fields.get("dest_country", ""),
                    fields["home_currency"],
                    fields["dest_currency"],
                    fields["rate"],
                    fields["rate_source"],
                    fields["balance_home"],
                    fields["balance_dest"],
                    _now(),
                ),
            )
            trip_id = int(cursor.lastrowid)
        self.set_active(user_id, trip_id)
        return trip_id

    def update_rate(self, trip_id: int, rate: float, source: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE travel_trips SET rate = ?, rate_source = ? WHERE id = ?",
                (rate, source, trip_id),
            )

    def update_balance(self, trip_id: int, balance_home: float, balance_dest: float) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE travel_trips SET balance_home = ?, balance_dest = ? WHERE id = ?",
                (balance_home, balance_dest, trip_id),
            )

    def finish(self, user_id: str, trip_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE travel_trips SET status = 'completed', completed_at = ? WHERE id = ?",
                (_now(), trip_id),
            )
            conn.execute(
                "UPDATE travel_users SET active_trip_id = NULL WHERE user_id = ?",
                (user_id,),
            )

    def add_expense(self, trip_id: int, amount_dest: float, amount_home: float, comment: str | None) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO travel_expenses (trip_id, amount_dest, amount_home, comment, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (trip_id, amount_dest, amount_home, comment, _now()),
            )

    def list_expenses(self, trip_id: int, limit: int = 8) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM travel_expenses
                WHERE trip_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (trip_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
