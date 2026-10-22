from __future__ import annotations

import re
from datetime import datetime, timedelta
from datetime import time as clock
from datetime import timezone
from zoneinfo import ZoneInfo

_START = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\s+(\d{1,2}):(\d{2})$")
_DURATION = re.compile(
    r"^(?:(\d+)\s*ч(?:ас(?:а|ов)?)?)?\s*(?:(\d+)\s*м(?:ин(?:ут(?:а|ы)?)?)?)?$"
)
_REMIND = re.compile(r"^(?:за\s+)?(?:(\d+)\s*ч(?:ас(?:а|ов)?)?)?\s*(?:(\d+)\s*м(?:ин(?:ут(?:а|ы)?)?)?)?$")


def load_timezone(name: str) -> timezone | ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone(timedelta(hours=3))


def parse_start(text: str, tz: timezone | ZoneInfo, today: datetime) -> datetime | None:
    """Дата и время: 21.10 15:00 или 21.10.2026 15:00."""
    match = _START.fullmatch(" ".join(text.replace("ё", "е").split()))
    if match is None:
        return None
    year_raw = match.group(3)
    year = int(year_raw) if year_raw else today.year
    try:
        parsed = datetime(
            year,
            int(match.group(2)),
            int(match.group(1)),
            int(match.group(4)),
            int(match.group(5)),
            tzinfo=tz,
        )
    except ValueError:
        return None
    if not year_raw and parsed < today - timedelta(days=1):
        try:
            parsed = parsed.replace(year=parsed.year + 1)
        except ValueError:
            return None
    return parsed


def parse_duration(text: str) -> timedelta | None:
    """Длительность в минутах, часах или парой «1ч 30мин»."""
    raw = " ".join(text.replace("ё", "е").casefold().split())
    if raw.isdigit():
        minutes = int(raw)
        return timedelta(minutes=minutes) if 5 <= minutes <= 48 * 60 else None
    match = _DURATION.fullmatch(raw)
    if match is None or not (match.group(1) or match.group(2)):
        return None
    minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    if not 5 <= minutes <= 48 * 60:
        return None
    return timedelta(minutes=minutes)


def parse_remind_minutes(text: str) -> int | None:
    """За сколько минут напомнить. 0 или «нет» — без напоминания."""
    raw = " ".join(text.replace("ё", "е").casefold().split())
    if raw in {"0", "нет", "без", "-", "не надо"}:
        return 0
    if raw.isdigit():
        minutes = int(raw)
        return minutes if 0 <= minutes <= 7 * 24 * 60 else None
    match = _REMIND.fullmatch(raw)
    if match is None or not (match.group(1) or match.group(2)):
        return None
    minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    return minutes if 0 <= minutes <= 7 * 24 * 60 else None


def day_bounds(day: datetime, tz: timezone | ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day.date(), clock.min, tzinfo=tz)
    return start, start + timedelta(days=1)


def week_bounds(day: datetime, tz: timezone | ZoneInfo) -> tuple[datetime, datetime]:
    monday = day.date() - timedelta(days=day.date().weekday())
    start = datetime.combine(monday, clock.min, tzinfo=tz)
    return start, start + timedelta(days=7)


def month_bounds(day: datetime, tz: timezone | ZoneInfo) -> tuple[datetime, datetime]:
    first = day.date().replace(day=1)
    start = datetime.combine(first, clock.min, tzinfo=tz)
    if first.month == 12:
        nxt = first.replace(year=first.year + 1, month=1)
    else:
        nxt = first.replace(month=first.month + 1)
    return start, datetime.combine(nxt, clock.min, tzinfo=tz)
