from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from app.config import settings
from app.core.agent import Agent
from app.tools.habits.reminders import run_habit_reminders
from app.tools.schedule.reminders import run_schedule_reminders
from app.ui.telegram.handlers import setup_handlers


async def run_telegram(agent: Agent) -> None:
    """Запускает Telegram-бота."""
    if not settings.telegram_bot_token:
        return

    proxy = settings.telegram_proxy.strip()
    session = AiohttpSession(proxy=proxy) if proxy else None
    bot = Bot(token=settings.telegram_bot_token, session=session)
    dp = Dispatcher()
    dp.include_router(setup_handlers(agent))
    reminders = asyncio.create_task(run_habit_reminders(bot, agent.habits_service))
    schedule_reminders = asyncio.create_task(run_schedule_reminders(bot, agent.schedule_service))
    try:
        await dp.start_polling(bot)
    finally:
        reminders.cancel()
        schedule_reminders.cancel()
