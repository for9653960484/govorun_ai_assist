from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolResult:
    """Результат выполнения инструмента."""

    ok: bool
    message: str
    data: dict[str, Any] | None = None


class BaseTool(ABC):
    """Единый интерфейс инструмента."""

    name: str
    description: str

    @abstractmethod
    def schema(self) -> dict[str, Any]:
        """Возвращает JSON-схему аргументов для tool calling."""

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        """Выполняет инструмент безопасным способом."""
