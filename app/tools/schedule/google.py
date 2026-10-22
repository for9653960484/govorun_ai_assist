from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import requests

from app.config import settings
from app.tools.schedule.parse import load_timezone
from app.tools.schedule.schemas import CalendarEvent, ScheduleError

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API = "https://www.googleapis.com/calendar/v3"
_TIMEOUT = 20
BIRTHDAY_COLOR_ID = "10"
BIRTHDAY_PREFIX = "День рождения:"
_token = ""
_token_until = datetime.min.replace(tzinfo=timezone.utc)


class GoogleCalendar:
    """Клиент Google Calendar API. События живут в календаре владельца."""

    def __init__(self, calendar_id: str = "primary") -> None:
        self.calendar_id = calendar_id or "primary"

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        page = ""
        while True:
            params = {
                "timeMin": _rfc3339(start),
                "timeMax": _rfc3339(end),
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": "250",
                "showDeleted": "false",
            }
            if page:
                params["pageToken"] = page
            payload = self._json("GET", self._url(""), params=params)
            for item in payload.get("items") or []:
                event = _from_item(item)
                if event is not None:
                    events.append(event)
            page = str(payload.get("nextPageToken") or "")
            if not page:
                break
        return events

    def create_yearly_all_day(
        self,
        summary: str,
        start_on: date,
        description: str = "",
        reminder_minutes: int = 1440,
        marker: str = "",
    ) -> CalendarEvent:
        """Событие на весь день, каждый год, с уведомлением Google Календаря."""
        end_on = start_on + timedelta(days=1)
        zone = settings.schedule_timezone
        body: dict = {
            "summary": summary,
            "description": description,
            "start": {"date": start_on.isoformat(), "timeZone": zone},
            "end": {"date": end_on.isoformat(), "timeZone": zone},
            "recurrence": ["RRULE:FREQ=YEARLY"],
            "colorId": BIRTHDAY_COLOR_ID,
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": reminder_minutes}],
            },
        }
        if marker:
            body["extendedProperties"] = {"private": {"govorunBirthday": marker}}
        created = self._json("POST", self._url(""), json=body)
        parsed = _from_item(created)
        if parsed is None:
            raise ScheduleError("Google Календарь не подтвердил день рождения.")
        return parsed

    def find_birthday(self, marker: str) -> str:
        """Идентификатор уже созданного дня рождения или пустая строка."""
        if not marker:
            return ""
        payload = self._json(
            "GET",
            self._url(""),
            params={"privateExtendedProperty": f"govorunBirthday={marker}", "maxResults": "2"},
        )
        for item in payload.get("items") or []:
            if item.get("status") == "cancelled":
                continue
            event_id = str(item.get("id") or "").strip()
            if event_id:
                return event_id
        return ""

    def paint_birthday(self, event_id: str) -> None:
        """Красит серию дня рождения в зелёный цвет Google Календаря."""
        if not event_id:
            return
        self._json(
            "PATCH",
            self._url(f"/{quote(event_id, safe='')}"),
            json={"colorId": BIRTHDAY_COLOR_ID},
        )

    def delete_id(self, event_id: str) -> None:
        if not event_id:
            return
        try:
            self._request("DELETE", self._url(f"/{quote(event_id, safe='')}"))
        except ScheduleError as exc:
            if "не найдено" not in exc.message:
                raise

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        created = self._json("POST", self._url(""), json=_body(event))
        parsed = _from_item(created)
        if parsed is None:
            raise ScheduleError("Google Календарь не подтвердил новое событие.")
        return parsed

    def update_event(self, event: CalendarEvent) -> CalendarEvent:
        current = self._get(event.uid or event.href)
        event.uid = current.uid
        event.etag = current.etag
        updated = self._json(
            "PATCH",
            self._url(f"/{quote(event.uid, safe='')}"),
            json=_body(event),
            headers={"If-Match": event.etag} if event.etag else None,
        )
        parsed = _from_item(updated)
        if parsed is None:
            raise ScheduleError("Google Календарь не подтвердил изменение.")
        return parsed

    def delete_event(self, event: CalendarEvent) -> None:
        event_id = event.uid or event.href
        try:
            self._request("DELETE", self._url(f"/{quote(event_id, safe='')}"))
        except ScheduleError as exc:
            if "не найдено" not in exc.message:
                raise

    def _get(self, event_id: str) -> CalendarEvent:
        payload = self._json("GET", self._url(f"/{quote(event_id, safe='')}"))
        event = _from_item(payload)
        if event is None:
            raise ScheduleError("Google Календарь вернул событие без даты или названия.")
        return event

    def _url(self, suffix: str) -> str:
        calendar_id = quote(self.calendar_id, safe="@")
        return f"{_API}/calendars/{calendar_id}/events{suffix}"

    def _json(self, method: str, url: str, params: dict | None = None, json: dict | None = None, headers: dict | None = None) -> dict:
        response = self._request(method, url, params=params, json=json, headers=headers)
        if not response.content:
            return {}
        try:
            payload = response.json()
        except ValueError as exc:
            raise ScheduleError("Google Календарь прислал непонятный ответ.") from exc
        return payload if isinstance(payload, dict) else {}

    def _request(self, method: str, url: str, params: dict | None = None, json: dict | None = None, headers: dict | None = None) -> requests.Response:
        sent = {"Authorization": f"Bearer {_access_token()}", "Accept": "application/json"}
        if headers:
            sent.update(headers)
        try:
            response = requests.request(method, url, params=params, json=json, headers=sent, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            raise ScheduleError("Нет связи с Google Календарём.") from exc
        if response.status_code == 401:
            _clear_token()
            sent["Authorization"] = f"Bearer {_access_token()}"
            try:
                response = requests.request(method, url, params=params, json=json, headers=sent, timeout=_TIMEOUT)
            except requests.RequestException as exc:
                raise ScheduleError("Нет связи с Google Календарём.") from exc
        if response.status_code in {401, 403}:
            raise ScheduleError("Google отклонил доступ к календарю. Проверьте токен и права календаря.")
        if response.status_code in {404, 410}:
            raise ScheduleError("Событие в Google Календаре не найдено.")
        if response.status_code == 412:
            raise ScheduleError("Событие в Google Календаре уже изменилось. Откройте список ещё раз.")
        if response.status_code not in {200, 201, 204}:
            detail = _error_detail(response)
            suffix = f": {detail}" if detail else ""
            raise ScheduleError(f"Google Календарь ответил {response.status_code}{suffix}.")
        return response


def _access_token() -> str:
    global _token, _token_until
    now = datetime.now(timezone.utc)
    if _token and now < _token_until:
        return _token
    if not settings.google_calendar_client_id or not settings.google_calendar_client_secret or not settings.google_calendar_refresh_token:
        raise ScheduleError("Не задан доступ к Google Календарю.")
    try:
        response = requests.post(
            _TOKEN_URL,
            data={
                "client_id": settings.google_calendar_client_id,
                "client_secret": settings.google_calendar_client_secret,
                "refresh_token": settings.google_calendar_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ScheduleError("Нет связи с Google.") from exc
    if response.status_code != 200:
        raise ScheduleError("Google не обновил доступ. Проверьте GOOGLE_CALENDAR_REFRESH_TOKEN.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ScheduleError("Google прислал непонятный ответ доступа.") from exc
    token = str(payload.get("access_token") or "")
    if not token:
        raise ScheduleError("Google не выдал доступ к календарю.")
    expires = int(payload.get("expires_in") or 3600)
    _token = token
    _token_until = now + timedelta(seconds=max(expires - 60, 30))
    return token


def _error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or "")[:180]
    return ""


def _clear_token() -> None:
    global _token, _token_until
    _token = ""
    _token_until = datetime.min.replace(tzinfo=timezone.utc)


def _body(event: CalendarEvent) -> dict:
    zone = settings.schedule_timezone
    if event.all_day:
        start_on = event.starts_at.astimezone(load_timezone(zone)).date()
        end_on = event.ends_at.astimezone(load_timezone(zone)).date()
        if end_on <= start_on:
            end_on = start_on + timedelta(days=1)
        return {
            "summary": event.summary,
            "description": event.description,
            "location": event.location,
            "start": {"date": start_on.isoformat(), "timeZone": zone},
            "end": {"date": end_on.isoformat(), "timeZone": zone},
        }
    return {
        "summary": event.summary,
        "description": event.description,
        "location": event.location,
        "start": {"dateTime": _rfc3339(event.starts_at), "timeZone": zone},
        "end": {"dateTime": _rfc3339(event.ends_at), "timeZone": zone},
    }


def _from_item(item: dict) -> CalendarEvent | None:
    if item.get("status") == "cancelled":
        return None
    summary = str(item.get("summary") or "").strip()
    event_id = str(item.get("id") or "").strip()
    if not summary or not event_id:
        return None
    start_raw = item.get("start") or {}
    end_raw = item.get("end") or {}
    all_day = "date" in start_raw and "dateTime" not in start_raw
    start = _parse_point(start_raw, all_day)
    end = _parse_point(end_raw, all_day)
    if start is None:
        return None
    if end is None:
        end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
    return CalendarEvent(
        uid=event_id,
        href=event_id,
        etag=str(item.get("etag") or ""),
        summary=summary,
        description=str(item.get("description") or ""),
        location=str(item.get("location") or ""),
        starts_at=start,
        ends_at=end,
        all_day=all_day,
        sequence=int(item.get("sequence") or 0),
        birthday=_is_birthday(item, summary),
    )


def _is_birthday(item: dict, summary: str) -> bool:
    private = (item.get("extendedProperties") or {}).get("private") or {}
    if str(private.get("govorunBirthday") or "").strip():
        return True
    return summary.startswith(BIRTHDAY_PREFIX)


def _parse_point(value: dict, all_day: bool) -> datetime | None:
    if all_day or "date" in value and "dateTime" not in value:
        raw = str(value.get("date") or "")
        try:
            day = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return None
        return day.replace(tzinfo=load_timezone(settings.schedule_timezone))
    raw = str(value.get("dateTime") or "")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=load_timezone(settings.schedule_timezone))
    return parsed


def _rfc3339(value: datetime) -> str:
    current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return current.isoformat()
