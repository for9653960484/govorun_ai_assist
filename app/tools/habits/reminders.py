from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.tools.habits.service import HabitsService

REMINDER_HOUR = 15
MOSCOW = timezone(timedelta(hours=3))
logger = logging.getLogger(__name__)


def reminder_is_due(now: datetime) -> bool:
    local = now.astimezone(MOSCOW)
    return (local.hour, local.minute) >= (REMINDER_HOUR, 0)


async def run_habit_reminders(bot: Bot, service: HabitsService) -> None:
    """После 15:00 по Москве один раз напоминает о неотмеченных привычках."""
    while True:
        try:
            await _send_due(bot, service)
        except Exception:
            logger.exception("Не удалось отправить напоминания о привычках")
        await asyncio.sleep(30)


async def _send_due(bot: Bot, service: HabitsService) -> None:
    now = datetime.now(MOSCOW)
    if not reminder_is_due(now):
        return
    today = now.date()
    for user_id in service.repo.list_user_ids():
        if not user_id.isdigit():
            continue
        text = service.reminder_text(user_id, today)
        if not text:
            continue
        try:
            await bot.send_message(int(user_id), text)
        except (TelegramBadRequest, TelegramForbiddenError):
            logger.info("Напоминание о привычках не доставлено пользователю %s", user_id)
        except Exception:
            logger.exception("Ошибка отправки напоминания пользователю %s", user_id)
            continue
        service.remember_reminder(user_id, today)
