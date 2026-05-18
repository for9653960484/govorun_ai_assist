from __future__ import annotations

import os
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from app.config import settings
from app.core.langchain_bridge import registry_to_langchain_tools
from app.core.prompts import SYSTEM_PROMPT
from app.core.registry import ToolRegistry


def _model_id() -> str:
    model = settings.openai_model.strip()
    if ":" in model:
        return model
    return f"openai:{model}"


def _configure_langsmith() -> None:
    if settings.langsmith_tracing:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
    if settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)


def _build_chat_model():
    kwargs: dict[str, Any] = {
        "api_key": settings.openai_api_key,
        "temperature": settings.langchain_temperature,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return init_chat_model(_model_id(), **kwargs)


def extract_agent_text(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    if not messages:
        return "Не удалось сформировать ответ."

    last = messages[-1]
    content = getattr(last, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()

    blocks = getattr(last, "content_blocks", None) or []
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        elif isinstance(block, str):
            parts.append(block)
        else:
            text = getattr(block, "text", None)
            if text:
                parts.append(str(text))

    joined = "".join(parts).strip()
    return joined or "Не удалось сформировать ответ."


class LangChainAgentRuntime:
    """LangChain-агент (create_agent) с памятью по thread_id."""

    def __init__(self, registry: ToolRegistry) -> None:
        _configure_langsmith()
        tools = registry_to_langchain_tools(registry.all_tools())
        self._checkpointer = InMemorySaver()
        self._agent = create_agent(
            model=_build_chat_model(),
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
        )

    async def invoke(
        self,
        user_id: str,
        user_text: str,
        *,
        extra_context: str | None = None,
    ) -> str:
        messages: list[dict[str, str]] = []
        if extra_context:
            messages.append({"role": "system", "content": f"Контекст документа:\n{extra_context}"})
        messages.append({"role": "user", "content": user_text})

        result = await self._agent.ainvoke(
            {"messages": messages},
            config={"configurable": {"thread_id": user_id}},
        )
        return extract_agent_text(result)
