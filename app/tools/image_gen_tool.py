from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import settings
from app.tools.base import BaseTool, ToolResult


class ImageGenTool(BaseTool):
    name = "image_gen"
    description = "Генерация изображения по текстовому описанию через OpenAI Images API"

    def __init__(self) -> None:
        client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self.client = OpenAI(**client_kwargs)

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Подробное описание желаемого изображения",
                    },
                    "size": {
                        "type": "string",
                        "description": "Размер изображения",
                        "enum": ["1024x1024", "1024x1536", "1536x1024"],
                    },
                },
                "required": ["prompt"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        if not settings.openai_api_key:
            return ToolResult(ok=False, message="OPENAI_API_KEY не задан.")

        prompt = str(kwargs.get("prompt", "")).strip()
        size = str(kwargs.get("size", "1024x1024")).strip() or "1024x1024"
        if not prompt:
            return ToolResult(ok=False, message="Пустой prompt для генерации изображения.")

        try:
            result = self.client.images.generate(
                model=settings.openai_image_model,
                prompt=prompt,
                size=size,
            )
        except Exception as exc:
            return ToolResult(ok=False, message=f"Ошибка генерации изображения: {exc}")

        image_url = ""
        data = getattr(result, "data", None) or []
        if data:
            image_url = getattr(data[0], "url", "") or ""

        if image_url:
            return ToolResult(
                ok=True,
                message=f"Изображение готово: {image_url}",
                data={"url": image_url},
            )

        return ToolResult(
            ok=False,
            message="Изображение создано, но API не вернул URL. Проверьте формат ответа/настройки модели.",
        )
