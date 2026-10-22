from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.tools.schedule.service import ScheduleService, _format_event
from app.tools.schedule.schemas import CalendarEvent

logger = logging.getLogger(__name__)


async def run_schedule_reminders(bot: Bot, service: ScheduleService) -> None:
    """Отправляет напоминание тому пользователю, которому принадлежит событие."""
    while True:
        try:
            await _send_due(bot, service)
        except Exception:
            logger.exception("Не удалось отправить напоминания расписания")
        await asyncio.sleep(30)


async def _send_due(bot: Bot, service: ScheduleService) -> None:
    now = datetime.now(service.tz)
    for item in service.due_reminders(now):
        recipient = str(item.get("user_id") or "")
        if not recipient.isdigit():
            continue
        text = _message(item, service)
        try:
            await bot.send_message(int(recipient), text)
        except (TelegramBadRequest, TelegramForbiddenError):
            logger.info("Напоминание расписания не доставлено")
            continue
        except Exception:
            logger.exception("Ошибка отправки напоминания расписания")
            continue
        service.mark_reminder_sent(str(item["event_uid"]), item["remind_at"])


def _message(item: dict, service: ScheduleService) -> str:
    if item.get("starts_at") and item.get("ends_at"):
        event = CalendarEvent(
            uid=str(item["event_uid"]),
            href="",
            etag="",
            summary=str(item.get("summary") or "Событие"),
            description="",
            location=str(item.get("location") or ""),
            starts_at=item["starts_at"],
            ends_at=item["ends_at"],
        )
        body = _format_event(event, service.tz)
    else:
        body = str(item.get("summary") or "Событие")
    return f"Напоминание\n{body}"
