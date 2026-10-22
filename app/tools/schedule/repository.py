from __future__ import annotations

from datetime import datetime

from app.tools.schedule.schemas import CalendarEvent, ScheduleError


class ScheduleRepository:
    """Настройки, диалог, кэш событий и напоминания в PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._ready = False

    def ensure(self) -> None:
        if self._ready:
            return
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_settings (
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (user_id, key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_dialog (
                    user_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_events (
                    uid TEXT PRIMARY KEY,
                    href TEXT NOT NULL,
                    etag TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    starts_at TIMESTAMPTZ NOT NULL,
                    ends_at TIMESTAMPTZ NOT NULL,
                    all_day BOOLEAN NOT NULL DEFAULT FALSE,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_reminders (
                    event_uid TEXT PRIMARY KEY,
                    minutes_before INTEGER NOT NULL,
                    remind_at TIMESTAMPTZ NOT NULL,
                    sent_at TIMESTAMPTZ
                )
                """
            )
        self._ready = True

    def get_dialog(self, user_id: str) -> tuple[str, dict]:
        self.ensure()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT state, payload FROM schedule_dialog WHERE user_id = %s",
                (user_id,),
            ).fetchone()
        if row is None:
            return "", {}
        payload = row["payload"] if isinstance(row["payload"], dict) else {}
        return str(row["state"]), payload

    def set_dialog(self, user_id: str, state: str, payload: dict) -> None:
        self.ensure()
        from psycopg.types.json import Json

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO schedule_dialog (user_id, state, payload, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (user_id) DO UPDATE
                SET state = EXCLUDED.state, payload = EXCLUDED.payload, updated_at = now()
                """,
                (user_id, state, Json(payload)),
            )

    def clear_dialog(self, user_id: str) -> None:
        if not self.database_url:
            return
        self.ensure()
        with self._connect() as conn:
            conn.execute("DELETE FROM schedule_dialog WHERE user_id = %s", (user_id,))

    def save_window(self, start: datetime, end: datetime, events: list[CalendarEvent]) -> None:
        self.ensure()
        with self._connect() as conn:
            uids = [event.uid for event in events]
            if uids:
                conn.execute(
                    """
                    DELETE FROM schedule_events
                    WHERE starts_at < %s AND ends_at > %s AND NOT (uid = ANY(%s))
                    """,
                    (end, start, uids),
                )
            else:
                conn.execute(
                    "DELETE FROM schedule_events WHERE starts_at < %s AND ends_at > %s",
                    (end, start),
                )
            for event in events:
                _upsert(conn, event)

    def save_event(self, event: CalendarEvent) -> None:
        self.ensure()
        with self._connect() as conn:
            _upsert(conn, event)

    def delete_event(self, uid: str) -> None:
        self.ensure()
        with self._connect() as conn:
            conn.execute("DELETE FROM schedule_reminders WHERE event_uid = %s", (uid,))
            conn.execute("DELETE FROM schedule_events WHERE uid = %s", (uid,))

    def load_window(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        self.ensure()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT uid, href, etag, summary, description, location, starts_at, ends_at, all_day
                FROM schedule_events
                WHERE starts_at < %s AND ends_at > %s
                ORDER BY starts_at, summary
                """,
                (end, start),
            ).fetchall()
        return [_from_row(row) for row in rows]

    def set_reminder(self, event_uid: str, minutes_before: int, remind_at: datetime | None) -> None:
        self.ensure()
        with self._connect() as conn:
            if minutes_before <= 0 or remind_at is None:
                conn.execute("DELETE FROM schedule_reminders WHERE event_uid = %s", (event_uid,))
                return
            conn.execute(
                """
                INSERT INTO schedule_reminders (event_uid, minutes_before, remind_at, sent_at)
                VALUES (%s, %s, %s, NULL)
                ON CONFLICT (event_uid) DO UPDATE
                SET minutes_before = EXCLUDED.minutes_before, remind_at = EXCLUDED.remind_at, sent_at = NULL
                """,
                (event_uid, minutes_before, remind_at),
            )

    def shift_reminder(self, event_uid: str, starts_at: datetime) -> None:
        self.ensure()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE schedule_reminders
                SET remind_at = %s - make_interval(mins => minutes_before), sent_at = NULL
                WHERE event_uid = %s
                """,
                (starts_at, event_uid),
            )

    def due_reminders(self, now: datetime) -> list[dict]:
        self.ensure()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.event_uid, r.remind_at, e.summary, e.location, e.starts_at, e.ends_at
                FROM schedule_reminders AS r
                LEFT JOIN schedule_events AS e ON e.uid = r.event_uid
                WHERE r.sent_at IS NULL AND r.remind_at <= %s
                ORDER BY r.remind_at
                """,
                (now,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_reminder_sent(self, event_uid: str, remind_at: datetime) -> None:
        self.ensure()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE schedule_reminders SET sent_at = now()
                WHERE event_uid = %s AND remind_at = %s
                """,
                (event_uid, remind_at),
            )

    def _connect(self):
        if not self.database_url:
            raise ScheduleError("Не задан SCHEDULE_DATABASE_URL.")
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise ScheduleError("Не установлен пакет psycopg.") from exc
        try:
            return psycopg.connect(self.database_url, connect_timeout=5, row_factory=dict_row)
        except Exception as exc:
            raise ScheduleError("Нет соединения с PostgreSQL.") from exc


def _upsert(conn, event: CalendarEvent) -> None:
    conn.execute(
        """
        INSERT INTO schedule_events (
            uid, href, etag, summary, description, location, starts_at, ends_at, all_day, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (uid) DO UPDATE SET
            href = EXCLUDED.href,
            etag = EXCLUDED.etag,
            summary = EXCLUDED.summary,
            description = EXCLUDED.description,
            location = EXCLUDED.location,
            starts_at = EXCLUDED.starts_at,
            ends_at = EXCLUDED.ends_at,
            all_day = EXCLUDED.all_day,
            updated_at = now()
        """,
        (
            event.uid,
            event.href,
            event.etag,
            event.summary,
            event.description,
            event.location,
            event.starts_at,
            event.ends_at,
            event.all_day,
        ),
    )


def _from_row(row: dict) -> CalendarEvent:
    return CalendarEvent(
        uid=str(row["uid"]),
        href=str(row["href"]),
        etag=str(row["etag"] or ""),
        summary=str(row["summary"]),
        description=str(row["description"] or ""),
        location=str(row["location"] or ""),
        starts_at=row["starts_at"],
        ends_at=row["ends_at"],
        all_day=bool(row["all_day"]),
        birthday=str(row["summary"] or "").startswith("День рождения:"),
    )
