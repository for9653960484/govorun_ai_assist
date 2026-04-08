from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(slots=True)
class MessageEntry:
    """Одна запись короткой памяти."""

    role: str
    content: str


class ShortMemory:
    """Короткая память в оперативной памяти процесса."""

    def __init__(self, limit: int = 5) -> None:
        self._limit = limit
        self._store: dict[str, deque[MessageEntry]] = defaultdict(lambda: deque(maxlen=self._limit))

    def add(self, user_id: str, role: str, content: str) -> None:
        self._store[user_id].append(MessageEntry(role=role, content=content))

    def get(self, user_id: str) -> list[dict[str, str]]:
        return [{"role": x.role, "content": x.content} for x in self._store.get(user_id, deque())]

    def clear(self, user_id: str) -> None:
        self._store.pop(user_id, None)
