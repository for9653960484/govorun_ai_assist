from __future__ import annotations

import re
import sqlite3

from app.memory.long_memory.repository import LongMemoryRepository


class TagService:
    """Сервис тем и тегов долгой памяти."""

    def __init__(self, repo: LongMemoryRepository) -> None:
        self.repo = repo

    def list_topics(self) -> list[dict]:
        return self.repo.list_topics()

    def switch_topic(self, tag: str) -> dict | None:
        return self.repo.get_topic_by_tag(self.normalize_tag(tag))

    def rename_topic_tag(self, old_tag: str, new_tag: str) -> tuple[bool, str]:
        old_norm = self.normalize_tag(old_tag)
        new_norm = self.normalize_tag(new_tag)
        if not self._is_valid_tag(new_norm):
            return False, "Новый тег некорректен. Разрешены буквы, цифры и '_'."
        if old_norm == new_norm:
            return False, "Старый и новый теги совпадают."
        try:
            renamed = self.repo.rename_topic_tag(old_norm, new_norm)
        except sqlite3.IntegrityError:
            return False, "Не удалось переименовать тег. Возможно, такой тег уже существует."
        if not renamed:
            return False, f"Тег #{old_norm} не найден."
        return True, f"Тег переименован: #{old_norm} -> #{new_norm}."

    def delete_topic_by_tag(self, tag: str) -> tuple[bool, str]:
        tag_norm = self.normalize_tag(tag)
        deleted = self.repo.delete_topic_by_tag(tag_norm)
        if not deleted:
            return False, f"Тег #{tag_norm} не найден."
        return True, f"Тег #{tag_norm} удален."

    @staticmethod
    def normalize_tag(tag: str) -> str:
        return tag.strip().lstrip("#").lower()

    @staticmethod
    def _is_valid_tag(tag: str) -> bool:
        return bool(re.fullmatch(r"[\w]+", tag, flags=re.UNICODE))
