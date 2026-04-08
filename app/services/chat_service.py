from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.core.prompts import SYSTEM_PROMPT
from app.core.registry import ToolRegistry
from app.memory.short_memory import ShortMemory


class ChatService:
    """Сервис общения с OpenAI Responses API."""

    def __init__(self, short_memory: ShortMemory, registry: ToolRegistry) -> None:
        client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self.client = OpenAI(**client_kwargs)
        self.short_memory = short_memory
        self.registry = registry

    def _build_input(self, user_id: str, user_text: str, extra_context: str | None = None) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.short_memory.get(user_id))
        if extra_context:
            messages.append({"role": "system", "content": f"Контекст документа:\n{extra_context}"})
        messages.append({"role": "user", "content": user_text})
        return messages

    async def ask(self, user_id: str, user_text: str, extra_context: str | None = None) -> str:
        if not settings.openai_api_key:
            return "OpenAI API key не задан. Укажите переменную окружения OPENAI_API_KEY."

        response = self.client.responses.create(
            model=settings.openai_model,
            input=self._build_input(user_id, user_text, extra_context=extra_context),
            tools=self.registry.schemas(),
        )

        output_text = getattr(response, "output_text", "") or ""

        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "function_call":
                args = json.loads(getattr(item, "arguments", "{}") or "{}")
                result = await self.registry.execute(getattr(item, "name", ""), args)
                output_text += f"\n\nРезультат инструмента: {result.message}"

        safe_text = output_text.strip() or "Не удалось сформировать ответ."
        self.short_memory.add(user_id, "user", user_text)
        self.short_memory.add(user_id, "assistant", safe_text)
        return safe_text
