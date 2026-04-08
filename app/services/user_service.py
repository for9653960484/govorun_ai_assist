from __future__ import annotations

from app.db.repositories import UserRepository


class UserService:
    """Сервис пользовательских состояний."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    def get_active_tag(self, user_id: str) -> str | None:
        return self.repo.get_active_tag(user_id)

    def set_active_tag(self, user_id: str, tag: str | None) -> None:
        self.repo.set_active_tag(user_id, tag)
