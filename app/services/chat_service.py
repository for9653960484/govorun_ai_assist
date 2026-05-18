from __future__ import annotations

from app.config import settings
from app.core.langchain_runtime import LangChainAgentRuntime
from app.core.registry import ToolRegistry
from app.memory.short_memory import ShortMemory


class ChatService:
    """Сервис общения через LangChain-агент."""

    def __init__(self, short_memory: ShortMemory, registry: ToolRegistry) -> None:
        self.short_memory = short_memory
        self.registry = registry
        self._runtime: LangChainAgentRuntime | None = None

    def _get_runtime(self) -> LangChainAgentRuntime:
        if self._runtime is None:
            self._runtime = LangChainAgentRuntime(self.registry)
        return self._runtime

    async def ask(self, user_id: str, user_text: str, extra_context: str | None = None) -> str:
        if not settings.openai_api_key:
            return "OpenAI API key не задан. Укажите переменную окружения OPENAI_API_KEY."

        runtime = self._get_runtime()
        safe_text = await runtime.invoke(user_id, user_text, extra_context=extra_context)

        self.short_memory.add(user_id, "user", user_text)
        self.short_memory.add(user_id, "assistant", safe_text)
        return safe_text
