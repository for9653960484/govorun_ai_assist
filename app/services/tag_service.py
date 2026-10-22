from __future__ import annotations

import re
import sqlite3

from app.memory.long_memory.repository import LongMemoryRepository


class TagService:
    """Сервис тем и тегов долгой памяти."""

    def __init__(self, repo: LongMemoryRepository) -> None:
        self.repo = repo

    def list_topics(self, user_id: str) -> list[dict]:
        return self.repo.list_topics(user_id)

    def create_project(self, user_id: str, name: str) -> tuple[bool, str]:
        title = " ".join((name or "").split())
        if len(title) < 2:
            return False, "Укажите название: добавить проект название"
        if len(title) > 80:
            return False, "Название проекта слишком длинное."
        tag = _tag_from_name(title)
        if not self._is_valid_tag(tag):
            return False, "Название проекта некорректно. Нужны буквы, цифры или пробелы."
        try:
            self.repo.create_topic(user_id, title, tag)
        except sqlite3.IntegrityError:
            return False, "Такой проект уже есть."
        return True, f"Проект добавлен: #{tag} ({title})."

    def discussion_letter(self, user_id: str, tag: str) -> tuple[str, str] | str:
        """Тема и текст письма. Строка — причина, почему письмо собирать не из чего."""
        tag_norm = self.normalize_tag(tag)
        topic = self.repo.get_topic_by_tag(user_id, tag_norm)
        if topic is None:
            return f"Проект #{tag_norm} не найден."
        notes = self.repo.list_notes(user_id, int(topic["id"]))
        searches = self.repo.list_saved_searches(user_id, int(topic["id"]))
        if not notes and not searches:
            return f"В проекте #{tag_norm} нет сохранённого обсуждения."
        return f"Проект: {topic['name']}", _letter_body(topic, notes, searches)

    def remember_discussion(self, user_id: str, tag: str, question: str, answer: str) -> None:
        topic = self.repo.get_topic_by_tag(user_id, self.normalize_tag(tag))
        if topic is None:
            return
        text = f"Вопрос: {question.strip()}\nОтвет: {answer.strip()}"
        if text == "Вопрос:\nОтвет:":
            return
        self.repo.add_note(user_id, int(topic["id"]), text)

    def switch_topic(self, user_id: str, tag: str) -> dict | None:
        return self.repo.get_topic_by_tag(user_id, self.normalize_tag(tag))

    def rename_topic_tag(self, user_id: str, old_tag: str, new_tag: str) -> tuple[bool, str]:
        old_norm = self.normalize_tag(old_tag)
        new_norm = self.normalize_tag(new_tag)
        if not self._is_valid_tag(new_norm):
            return False, "Новый тег некорректен. Разрешены буквы, цифры и '_'."
        if old_norm == new_norm:
            return False, "Старый и новый теги совпадают."
        try:
            renamed = self.repo.rename_topic_tag(user_id, old_norm, new_norm)
        except sqlite3.IntegrityError:
            return False, "Не удалось переименовать тег. Возможно, такой тег уже существует."
        if not renamed:
            return False, f"Тег #{old_norm} не найден."
        return True, f"Тег переименован: #{old_norm} -> #{new_norm}."

    def delete_topic_by_tag(self, user_id: str, tag: str) -> tuple[bool, str]:
        tag_norm = self.normalize_tag(tag)
        deleted = self.repo.delete_topic_by_tag(user_id, tag_norm)
        if not deleted:
            return False, f"Тег #{tag_norm} не найден."
        return True, f"Тег #{tag_norm} удален."

    @staticmethod
    def normalize_tag(tag: str) -> str:
        return tag.strip().lstrip("#").lower()

    @staticmethod
    def _is_valid_tag(tag: str) -> bool:
        return bool(re.fullmatch(r"[\w]+", tag, flags=re.UNICODE))


def _letter_body(topic: dict, notes: list[dict], searches: list[dict]) -> str:
    lines = [f"Проект: {topic['name']}", f"Тег: #{topic['tag']}", ""]
    if notes:
        lines.append("Обсуждение")
        lines.append("")
        for note in notes:
            when = str(note.get("created_at") or "").strip()
            if when:
                lines.append(when)
            lines.append(str(note.get("content") or "").strip())
            lines.append("")
    if searches:
        lines.append("Сохранённые поиски")
        lines.append("")
        for item in searches:
            when = str(item.get("created_at") or "").strip()
            if when:
                lines.append(when)
            lines.append(f"Запрос: {item.get('query') or ''}")
            lines.append(str(item.get("result") or "").strip())
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def _tag_from_name(name: str) -> str:
    cleaned = name.replace("ё", "е").replace("Ё", "е").replace("-", " ").replace("—", " ")
    return "_".join(cleaned.casefold().split())
