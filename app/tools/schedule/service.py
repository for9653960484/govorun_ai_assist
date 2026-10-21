from __future__ import annotations

from datetime import datetime, timedelta

from app.config import settings
from app.tools.schedule.parse import (
    day_bounds,
    load_timezone,
    parse_duration,
    parse_remind_minutes,
    parse_start,
    week_bounds,
)
from app.tools.schedule.repository import ScheduleRepository
from app.tools.schedule.schemas import CalendarEvent, ScheduleError, ScheduleReply
from app.tools.schedule.google import GoogleCalendar

_COMMANDS = (
    "Команды боту:\n"
    "<b>сегодня</b>\n"
    "<b>неделя</b>\n"
    "<b>создать</b>\n"
    "<b>изменить</b>\n"
    "<b>перенести</b>\n"
    "<b>удалить</b>\n"
    "<b>напоминание</b>"
)
_WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
_FIELDS = {
    "название": "summary",
    "описание": "description",
    "место": "location",
    "длительность": "duration",
}
_COMMAND_NAMES = {
    "сегодня": "day",
    "день": "day",
    "неделя": "week",
    "создать": "create",
    "изменить": "edit",
    "перенести": "move",
    "удалить": "delete",
    "напоминание": "remind",
}


class ScheduleService:
    """Личное расписание одного владельца. События читаются и пишутся в Google Календарь."""

    def __init__(self) -> None:
        self.repo = ScheduleRepository(settings.schedule_database_url)
        self.tz = load_timezone(settings.schedule_timezone)

    def allowed(self, user_id: str) -> bool:
        owner = settings.telegram_allowed_user_id
        return bool(owner) and user_id == owner

    def deny_text(self) -> str:
        return "Раздел «Расписание» доступен только владельцу."

    def open_text(self) -> str:
        gaps = self._gaps()
        if not gaps:
            return _COMMANDS
        return f"{_COMMANDS}\n\nДля работы задайте: {', '.join(gaps)}."

    def clear_dialog(self, user_id: str) -> None:
        if not settings.schedule_database_url:
            return
        try:
            self.repo.clear_dialog(user_id)
        except ScheduleError:
            return

    def answer(self, user_id: str, text: str) -> ScheduleReply:
        blocked = self._blocked(user_id)
        if blocked:
            return ScheduleReply(blocked)
        raw = " ".join((text or "").split())
        folded = raw.casefold().replace("ё", "е")
        if folded in {"отмена", "назад"}:
            self.repo.clear_dialog(user_id)
            return ScheduleReply(_COMMANDS)
        command = _COMMAND_NAMES.get(folded)
        if command:
            return self._start_command(user_id, command)
        try:
            state, payload = self.repo.get_dialog(user_id)
        except ScheduleError as exc:
            return ScheduleReply(exc.message)
        if not state:
            return ScheduleReply(_COMMANDS)
        try:
            return self._continue(user_id, state, payload, raw)
        except ScheduleError as exc:
            return ScheduleReply(exc.message)

    def due_reminders(self, now: datetime) -> list[dict]:
        if not settings.schedule_database_url or not settings.telegram_allowed_user_id:
            return []
        return self.repo.due_reminders(now)

    def mark_reminder_sent(self, event_uid: str, remind_at: datetime) -> None:
        self.repo.mark_reminder_sent(event_uid, remind_at)

    def _start_command(self, user_id: str, command: str) -> ScheduleReply:
        now = datetime.now(self.tz)
        if command == "day":
            start, end = day_bounds(now, self.tz)
            return ScheduleReply(self._show(start, end, "Сегодня"))
        if command == "week":
            start, end = week_bounds(now, self.tz)
            title = f"Неделя {start:%d.%m}–{(end - timedelta(days=1)):%d.%m}"
            return ScheduleReply(self._show(start, end, title))
        if command == "create":
            self.repo.set_dialog(user_id, "create_title", {})
            return ScheduleReply("Название события:")
        return self._ask_pick(user_id, command)

    def _continue(self, user_id: str, state: str, payload: dict, text: str) -> ScheduleReply:
        if state == "create_title":
            title = _clip(text, 200)
            if len(title) < 2:
                return ScheduleReply("Название слишком короткое.")
            payload["summary"] = title
            self.repo.set_dialog(user_id, "create_start", payload)
            return ScheduleReply("Дата и время начала: 21.10 15:00")
        if state == "create_start":
            start = parse_start(text, self.tz, datetime.now(self.tz))
            if start is None:
                return ScheduleReply("Нужна дата и время, например 21.10 15:00")
            payload["starts_at"] = start.isoformat()
            self.repo.set_dialog(user_id, "create_duration", payload)
            return ScheduleReply("Длительность: 60 или 1ч 30мин")
        if state == "create_duration":
            duration = parse_duration(text)
            if duration is None:
                return ScheduleReply("Нужна длительность от 5 минут до 48 часов.")
            payload["duration_minutes"] = int(duration.total_seconds() // 60)
            self.repo.set_dialog(user_id, "create_place", payload)
            return ScheduleReply("Место. Если его нет, напишите «-».")
        if state == "create_place":
            payload["location"] = "" if _blank(text) else _clip(text, 200)
            self.repo.set_dialog(user_id, "create_description", payload)
            return ScheduleReply("Описание. Если его нет, напишите «-».")
        if state == "create_description":
            payload["description"] = "" if _blank(text) else _clip(text, 2000)
            self.repo.set_dialog(user_id, "create_remind", payload)
            return ScheduleReply("За сколько минут напомнить? 0 — без напоминания.")
        if state == "create_remind":
            return self._finish_create(user_id, payload, text)
        if state == "pick":
            return self._picked(user_id, payload, text)
        if state == "edit_field":
            field = _FIELDS.get(text.casefold().replace("ё", "е"))
            if field is None:
                return ScheduleReply("Выберите: название, описание, место или длительность.", "fields")
            payload["field"] = field
            self.repo.set_dialog(user_id, "edit_value", payload)
            return ScheduleReply(_field_prompt(field))
        if state == "edit_value":
            return self._apply_edit(user_id, payload, text)
        if state == "move_start":
            return self._apply_move(user_id, payload, text)
        if state == "delete_confirm":
            return self._apply_delete(user_id, payload, text)
        if state == "remind_offset":
            return self._apply_remind(user_id, payload, text)
        self.repo.clear_dialog(user_id)
        return ScheduleReply(_COMMANDS)

    def _finish_create(self, user_id: str, payload: dict, text: str) -> ScheduleReply:
        minutes = parse_remind_minutes(text)
        if minutes is None:
            return ScheduleReply("Напишите число минут, например 30, или 0.")
        start = datetime.fromisoformat(payload["starts_at"])
        end = start + timedelta(minutes=int(payload["duration_minutes"]))
        event = CalendarEvent(
            uid="",
            href="",
            etag="",
            summary=payload["summary"],
            description=payload.get("description", ""),
            location=payload.get("location", ""),
            starts_at=start,
            ends_at=end,
        )
        saved = self._google().create_event(event)
        self.repo.save_event(saved)
        self._store_reminder(saved, minutes)
        self.repo.clear_dialog(user_id)
        tail = "Напоминание не задано." if minutes == 0 else f"Напоминание: за {minutes} мин."
        return ScheduleReply(f"Событие записано в Google Календарь.\n{_format_event(saved, self.tz)}\n{tail}")

    def _ask_pick(self, user_id: str, action: str) -> ScheduleReply:
        now = datetime.now(self.tz)
        start, _day_end = day_bounds(now, self.tz)
        events, cached = self._events_between(start, start + timedelta(days=14))
        if not events:
            return ScheduleReply("На ближайшие две недели событий нет.")
        items = [_dump(event) for event in events]
        self.repo.set_dialog(user_id, "pick", {"action": action, "items": items})
        lines = [_format_event(event, self.tz, index) for index, event in enumerate(events, start=1)]
        note = "\n\nПоказан локальный кэш: Google Календарь сейчас недоступен." if cached else ""
        return ScheduleReply("Выберите номер:\n" + "\n".join(lines) + note)

    def _picked(self, user_id: str, payload: dict, text: str) -> ScheduleReply:
        items = payload.get("items") or []
        number = text[:-1] if text.endswith(".") else text
        if not number.isdigit() or not 1 <= int(number) <= len(items):
            return ScheduleReply("Нет события с таким номером.")
        item = items[int(number) - 1]
        action = str(payload.get("action") or "")
        self.repo.set_dialog(user_id, _next_state(action), {"action": action, "item": item})
        if action == "edit":
            return ScheduleReply("Что изменить?", "fields")
        if action == "move":
            return ScheduleReply("Новые дата и время начала: 21.10 15:00")
        if action == "delete":
            return ScheduleReply(f"Удалить событие?\n{_format_event(_load(item), self.tz)}", "confirm")
        return ScheduleReply("За сколько минут напомнить? 0 — убрать напоминание.")

    def _apply_edit(self, user_id: str, payload: dict, text: str) -> ScheduleReply:
        event = _load(payload["item"])
        field = str(payload.get("field") or "")
        if field == "summary":
            title = _clip(text, 200)
            if len(title) < 2:
                return ScheduleReply("Название слишком короткое.")
            event.summary = title
        elif field == "description":
            event.description = "" if _blank(text) else _clip(text, 2000)
        elif field == "location":
            event.location = "" if _blank(text) else _clip(text, 200)
        elif field == "duration":
            duration = parse_duration(text)
            if duration is None:
                return ScheduleReply("Нужна длительность от 5 минут до 48 часов.")
            event.ends_at = event.starts_at + duration
        else:
            return ScheduleReply("Выберите: название, описание, место или длительность.", "fields")
        saved = self._google().update_event(event)
        self.repo.save_event(saved)
        self.repo.clear_dialog(user_id)
        return ScheduleReply(f"Событие изменено.\n{_format_event(saved, self.tz)}")

    def _apply_move(self, user_id: str, payload: dict, text: str) -> ScheduleReply:
        start = parse_start(text, self.tz, datetime.now(self.tz))
        if start is None:
            return ScheduleReply("Нужна дата и время, например 21.10 15:00")
        event = _load(payload["item"])
        duration = event.ends_at - event.starts_at
        event.starts_at = start
        event.ends_at = start + duration
        saved = self._google().update_event(event)
        self.repo.save_event(saved)
        self.repo.shift_reminder(saved.uid, saved.starts_at)
        self.repo.clear_dialog(user_id)
        return ScheduleReply(f"Событие перенесено.\n{_format_event(saved, self.tz)}")

    def _apply_delete(self, user_id: str, payload: dict, text: str) -> ScheduleReply:
        answer = text.casefold().replace("ё", "е")
        if answer in {"нет", "no"}:
            self.repo.clear_dialog(user_id)
            return ScheduleReply("Удаление отменено.")
        if answer not in {"да", "yes", "ок", "+"}:
            return ScheduleReply("Напишите «да» или «нет».", "confirm")
        event = _load(payload["item"])
        self._google().delete_event(event)
        self.repo.delete_event(event.uid)
        self.repo.clear_dialog(user_id)
        return ScheduleReply(f"Событие удалено.\n{_format_event(event, self.tz)}")

    def _apply_remind(self, user_id: str, payload: dict, text: str) -> ScheduleReply:
        minutes = parse_remind_minutes(text)
        if minutes is None:
            return ScheduleReply("Напишите число минут, например 30, или 0.")
        event = _load(payload["item"])
        self._store_reminder(event, minutes)
        self.repo.clear_dialog(user_id)
        if minutes == 0:
            return ScheduleReply(f"Напоминание снято.\n{_format_event(event, self.tz)}")
        return ScheduleReply(f"Напоминание: за {minutes} мин.\n{_format_event(event, self.tz)}")

    def _show(self, start: datetime, end: datetime, title: str) -> str:
        events, cached = self._events_between(start, end)
        if not events:
            return f"{title}\nСобытий нет."
        lines = [title]
        current_day = None
        for event in events:
            local = event.starts_at.astimezone(self.tz)
            if local.date() != current_day:
                current_day = local.date()
                lines.append(f"{local:%d.%m}, {_WEEKDAYS[local.weekday()]}")
            lines.append(_format_event(event, self.tz))
        if cached:
            lines.append("Показан локальный кэш: Google Календарь сейчас недоступен.")
        return "\n".join(lines)

    def _events_between(self, start: datetime, end: datetime) -> tuple[list[CalendarEvent], bool]:
        try:
            events = self._google().list_events(start, end)
            self.repo.save_window(start, end, events)
            return events, False
        except ScheduleError as exc:
            cached = self.repo.load_window(start, end)
            if cached:
                return cached, True
            raise exc

    def _store_reminder(self, event: CalendarEvent, minutes: int) -> None:
        if minutes <= 0:
            self.repo.set_reminder(event.uid, 0, None)
            return
        remind_at = event.starts_at - timedelta(minutes=minutes)
        if remind_at <= datetime.now(event.starts_at.tzinfo):
            raise ScheduleError("Время напоминания уже прошло.")
        self.repo.set_reminder(event.uid, minutes, remind_at)

    def _google(self) -> GoogleCalendar:
        return GoogleCalendar(settings.google_calendar_id)

    def _blocked(self, user_id: str) -> str | None:
        if not self.allowed(user_id):
            return self.deny_text()
        gaps = self._gaps()
        if gaps:
            return "Для расписания задайте: " + ", ".join(gaps) + "."
        return None

    def _gaps(self) -> list[str]:
        missing: list[str] = []
        if not settings.schedule_database_url:
            missing.append("SCHEDULE_DATABASE_URL")
        if not settings.google_calendar_client_id or not settings.google_calendar_client_secret or not settings.google_calendar_refresh_token:
            missing.append("GOOGLE_CALENDAR_CLIENT_ID, GOOGLE_CALENDAR_CLIENT_SECRET и GOOGLE_CALENDAR_REFRESH_TOKEN")
        return missing


def _next_state(action: str) -> str:
    return {
        "edit": "edit_field",
        "move": "move_start",
        "delete": "delete_confirm",
        "remind": "remind_offset",
    }.get(action, "")


def _field_prompt(field: str) -> str:
    if field == "summary":
        return "Новое название:"
    if field == "description":
        return "Новое описание. «-» очистит его."
    if field == "location":
        return "Новое место. «-» очистит его."
    return "Новая длительность: 60 или 1ч 30мин"


def _blank(text: str) -> bool:
    return text.casefold().replace("ё", "е") in {"-", "нет", "пропустить", "пусто"}


def _clip(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit].strip()


def _dump(event: CalendarEvent) -> dict:
    return {
        "uid": event.uid,
        "href": event.href,
        "etag": event.etag,
        "summary": event.summary,
        "description": event.description,
        "location": event.location,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat(),
        "all_day": event.all_day,
        "sequence": event.sequence,
    }


def _load(data: dict) -> CalendarEvent:
    return CalendarEvent(
        uid=str(data.get("uid") or ""),
        href=str(data.get("href") or ""),
        etag=str(data.get("etag") or ""),
        summary=str(data.get("summary") or ""),
        description=str(data.get("description") or ""),
        location=str(data.get("location") or ""),
        starts_at=datetime.fromisoformat(str(data["starts_at"])),
        ends_at=datetime.fromisoformat(str(data["ends_at"])),
        all_day=bool(data.get("all_day")),
        sequence=int(data.get("sequence") or 0),
    )


def _format_event(event: CalendarEvent, tz, index: int | None = None) -> str:
    start = event.starts_at.astimezone(tz)
    end = event.ends_at.astimezone(tz)
    prefix = f"{index}. " if index else ""
    if event.all_day:
        when = f"{start:%d.%m} весь день"
    elif start.date() == end.date():
        when = f"{start:%d.%m %H:%M}–{end:%H:%M}"
    else:
        when = f"{start:%d.%m %H:%M}–{end:%d.%m %H:%M}"
    lines = [f"{prefix}{when}  {event.summary}"]
    if event.location:
        lines.append(f"место: {event.location}")
    if event.description:
        lines.append(event.description)
    return "\n".join(lines)
