from __future__ import annotations

import asyncio

import uvicorn

from app.config import settings
from app.core.agent import Agent
from app.db.sqlite.setup import init_all_sqlite
from app.ui.telegram.bot import run_telegram
from app.ui.web.app import create_web_app
from app.utils.logger import setup_logger


def main() -> None:
    """Точка входа: инициализация и запуск UI-каналов."""
    setup_logger(settings.log_level)
    init_all_sqlite()
    agent = Agent()

    web = create_web_app(agent)

    async def run_all() -> None:
        config = uvicorn.Config(web, host=settings.web_host, port=settings.web_port, log_level="info")
        server = uvicorn.Server(config)

        if settings.telegram_bot_token:
            await asyncio.gather(server.serve(), run_telegram(agent))
        else:
            await server.serve()

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
