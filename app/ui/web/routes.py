from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.agent import Agent
from app.core.types import IncomingMessage
from app.config import settings


def build_routes(agent: Agent) -> APIRouter:
    router = APIRouter()
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"request": request, "title": "AI Секретарь"},
        )

    @router.post("/chat")
    async def chat(
        user_id: str = Form(...),
        text: str = Form(""),
        file: UploadFile | None = File(None),
    ):
        file_path = None
        if file is not None:
            dst = settings.documents_raw_dir / file.filename
            dst.parent.mkdir(parents=True, exist_ok=True)
            content = await file.read()
            dst.write_bytes(content)
            file_path = str(dst)

        response = await agent.handle(IncomingMessage(user_id=user_id, text=text, file_path=file_path, file_name=file.filename if file else None))
        return {"ok": True, "response": response}

    return router
