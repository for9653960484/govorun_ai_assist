from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class RouteType(str, Enum):
    CHAT = "chat"
    DOCUMENT_QA = "document_qa"
    FILE_ONLY = "file_only"
    TOOL = "tool"
    TAG_SWITCH = "tag_switch"
    CLARIFY = "clarify"


@dataclass(slots=True)
class IncomingMessage:
    """Входное сообщение пользователя."""

    user_id: str
    text: str = ""
    file_path: str | None = None
    file_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RouteDecision:
    """Результат маршрутизации сообщения."""

    route: RouteType
    reason: str
    tag: str | None = None
    tool_name: str | None = None


@dataclass(slots=True)
class RetrievedChunk:
    """Фрагмент документа для ответа."""

    source: Path
    chunk_id: str
    text: str
    score: float
