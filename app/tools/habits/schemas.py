from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Habit:
    """Регулярное действие пользователя."""

    id: int
    user_id: str
    title: str
    position: int
