from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.agent import Agent
from app.ui.web.routes import build_routes


def create_web_app(agent: Agent) -> FastAPI:
    """Создает FastAPI-приложение веб-интерфейса."""
    app = FastAPI(title="AI Секретарь")
    app.mount("/static", StaticFiles(directory="app/ui/web/static"), name="static")
    app.include_router(build_routes(agent))
    return app
