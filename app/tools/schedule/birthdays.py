"""Дни рождения из локальной базы становятся событиями Google Календаря."""

from __future__ import annotations

from datetime import date

from app.config import settings
from app.tools.calendar.repository import CalendarRepository
from app.tools.schedule.google import GoogleCalendar
from app.tools.schedule.schemas import ScheduleError
from app.utils.logger import get_logger

_REMIND_MINUTES = 24 * 60
_logger = get_logger(__name__)


def sync_birthdays() -> str | None:
    """Отправляет в календарь записи, у которых ещё нет события. None — всё уже на месте."""
    if not _google_ready():
        return None
    repo = CalendarRepository(settings.sqlite_path)
    pending = [row for row in repo.all_people() if not str(row.get("google_event_id") or "").strip()]
    if not pending:
        return None
    failed = 0
    reason = ""
    for row in pending:
        error = publish_birthday(repo, int(row["id"]))
        if error:
            failed += 1
            reason = error
    if not failed:
        return None
    return f"В Google Календарь не отправлено дней рождения: {failed}. {reason}"


def publish_birthday(repo: CalendarRepository, person_id: int) -> str | None:
    """Создаёт ежегодное событие на весь день. None — событие есть."""
    row = repo.get_person(person_id)
    if row is None:
        return None
    if not _google_ready():
        return "Не задан доступ к Google Календарю."
    existing = str(row.get("google_event_id") or "").strip()
    if existing:
        return None
    summary = _summary(row)
    if not summary:
        return None
    marker = str(person_id)
    try:
        calendar = GoogleCalendar(settings.google_calendar_id)
        event_id = calendar.find_birthday(marker)
        if not event_id:
            created = calendar.create_yearly_all_day(
                summary=summary,
                start_on=birthday_start(
                    int(row["birth_day"]),
                    int(row["birth_month"]),
                    int(row["birth_year"] or 0),
                ),
                description=_description(row),
                reminder_minutes=_REMIND_MINUTES,
                marker=marker,
            )
            event_id = created.uid
        calendar.paint_birthday(event_id)
        repo.set_google_event_id(person_id, event_id)
    except ScheduleError as exc:
        _logger.warning("День рождения %s не записан в Google Календарь: %s", person_id, exc.message)
        return exc.message
    return None


def paint_birthdays() -> None:
    """Красит уже созданные дни рождения в зелёный."""
    if not _google_ready():
        return
    repo = CalendarRepository(settings.sqlite_path)
    calendar = GoogleCalendar(settings.google_calendar_id)
    for row in repo.all_people():
        event_id = str(row.get("google_event_id") or "").strip()
        if not event_id:
            continue
        try:
            calendar.paint_birthday(event_id)
        except ScheduleError as exc:
            _logger.warning("День рождения %s не перекрашен: %s", row.get("id"), exc.message)


def withdraw_birthday(event_id: str) -> str | None:
    """Удаляет серию дня рождения из Google Календаря. None — удалено или его не было."""
    if not event_id:
        return None
    if not _google_ready():
        return "Не задан доступ к Google Календарю."
    try:
        GoogleCalendar(settings.google_calendar_id).delete_id(event_id)
    except ScheduleError as exc:
        _logger.warning("Событие дня рождения не удалено из Google Календаря: %s", exc.message)
        return exc.message
    return None


def birthday_start(day: int, month: int, year: int, today: date | None = None) -> date:
    """Первый день серии: год рождения или ближайшая такая дата."""
    current = today or date.today()
    if year and _exists(year, month, day):
        return date(year, month, day)
    probe = current.year
    for _ in range(8):
        try:
            candidate = date(probe, month, day)
        except ValueError:
            probe += 1
            continue
        if candidate >= current:
            return candidate
        probe += 1
    return date(probe, month, min(day, 28))


def _summary(row: dict) -> str:
    last_name = str(row.get("last_name") or "").strip()
    first_name = str(row.get("first_name") or "").strip()
    if not last_name or not first_name:
        return ""
    return f"День рождения: {last_name} {first_name}"


def _description(row: dict) -> str:
    day = int(row["birth_day"])
    month = int(row["birth_month"])
    year = int(row.get("birth_year") or 0)
    if year:
        return f"{day:02d}.{month:02d}.{year}"
    return f"{day:02d}.{month:02d}"


def _exists(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _google_ready() -> bool:
    return bool(
        settings.google_calendar_client_id
        and settings.google_calendar_client_secret
        and settings.google_calendar_refresh_token
    )
