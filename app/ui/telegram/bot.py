from __future__ import annotations

from aiogram import Bot, Dispatcher

from app.config import settings
from app.core.agent import Agent
from app.ui.telegram.handlers import setup_handlers


async def run_telegram(agent: Agent) -> None:
    """Запускает Telegram-бота."""
    if not settings.telegram_bot_token:
        return

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(setup_handlers(agent))
    await dp.start_polling(bot)
