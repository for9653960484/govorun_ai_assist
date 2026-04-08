from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UserProfile:
    """Профиль пользователя для служебных операций."""

    user_id: str
    active_tag: str | None = None
