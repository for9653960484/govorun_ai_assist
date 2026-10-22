"""Команды владельца и участника: список, удаление и своя отвязка."""

from __future__ import annotations

from app.access.purge import purge_user_data
from app.access.repository import AccessRegistry, normalize_username
from app.config import settings

_YES = {"да", "yes", "ок", "+"}
_NO = {"нет", "no", "отмена", "назад"}


class AccessService:
    """Подтверждение перед удалением участника и его данных."""

    def __init__(self, pending: dict[str, str], registry: AccessRegistry | None = None) -> None:
        self._pending = pending
        self.registry = registry or AccessRegistry(settings.sqlite_path)

    def is_owner(self, telegram_id: str) -> bool:
        owner = settings.telegram_allowed_user_id
        return bool(owner) and telegram_id == owner

    def has_pending(self, actor_id: str) -> bool:
        return actor_id in self._pending

    def list_text(self, actor_id: str) -> str:
        if not self.is_owner(actor_id):
            return "Список пользователей доступен владельцу."
        rows = self.registry.list_members()
        if not rows:
            lines = ["Список пользователей пуст."]
        else:
            lines = ["Пользователи:"]
            for row in rows:
                state = "привязан" if row["telegram_id"] else "ещё не входил"
                lines.append(f"- @{row['username']} — {state}")
        lines += [
            "",
            "Добавить: добавить пользователя @имя",
            "Удалить: удалить пользователя @имя",
        ]
        return "\n".join(lines)

    def add_text(self, actor_id: str, username: str) -> str:
        if not self.is_owner(actor_id):
            return "Добавлять пользователей может только владелец."
        if not self.registry.add_member(username):
            return "Укажите имя: добавить пользователя @имя"
        return f"Пользователь @{normalize_username(username)} добавлен. Он войдёт, когда напишет боту."

    def ask_remove(self, actor_id: str, username: str) -> str:
        if not self.is_owner(actor_id):
            return "Удалять пользователей может только владелец."
        member = self.registry.get_member(username)
        if member is None:
            shown = normalize_username(username) or username.strip()
            return f"Пользователь @{shown} не найден."
        self._pending[actor_id] = member["username"]
        return _confirm_text(member["username"])

    def ask_leave(self, actor_id: str) -> str:
        if self.is_owner(actor_id):
            return "Владелец не может отвязаться от бота."
        username = self.registry.username_of(actor_id)
        if not username:
            return "Привязка к боту не найдена."
        self._pending[actor_id] = username
        return _confirm_text(username, own=True)

    def take_answer(self, actor_id: str, text: str) -> tuple[str, str, bool] | None:
        """Ответ на подтверждение: текст, id стёртого пользователя, ушёл ли сам актор."""
        username = self._pending.get(actor_id, "")
        if not username:
            return None
        folded = " ".join(text.replace("ё", "е").split()).casefold()
        if folded in _NO:
            self._pending.pop(actor_id, None)
            return "Удаление отменено.", "", False
        if folded not in _YES:
            own = username == self.registry.username_of(actor_id)
            return _confirm_text(username, own=own), "", False
        self._pending.pop(actor_id, None)
        telegram_id = self.registry.remove_member(username)
        if telegram_id is None:
            return f"Пользователь @{username} уже удалён.", "", False
        if telegram_id == settings.telegram_allowed_user_id:
            return f"Пользователь @{username} удалён из списка. Данные владельца сохранены.", "", False
        if telegram_id:
            purge_user_data(telegram_id, db_path=self.registry.db_path)
        left = bool(telegram_id) and telegram_id == actor_id
        if left:
            return "Привязка удалена, данные стерты. Доступа к боту больше нет.", telegram_id, True
        if telegram_id:
            return f"Пользователь @{username} удалён вместе с данными.", telegram_id, False
        return f"Пользователь @{username} удалён из списка. Данных ещё не было.", "", False


def _confirm_text(username: str, *, own: bool = False) -> str:
    if own:
        return (
            "Удалить вашу привязку и все ваши данные?\n"
            "Напишите «да» или «нет»."
        )
    return (
        f"Удалить @{username} и все его данные?\n"
        "Напишите «да» или «нет»."
    )
