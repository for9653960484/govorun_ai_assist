from __future__ import annotations

import re
from pathlib import Path

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message, ReplyKeyboardRemove

from app.access.repository import AccessRegistry
from app.access.service import AccessService
from app.config import settings
from app.core.agent import Agent
from app.core.types import IncomingMessage
from app.tools.quotes_tool import accepts_query, asset_by_label
from app.ui.telegram.keyboards import (
    main_keyboard,
    projects_keyboard,
    quotes_keyboard,
    schedule_confirm_keyboard,
    schedule_fields_keyboard,
    schedule_keyboard,
)

router = Router()
TELEGRAM_MESSAGE_LIMIT = 4096
_REMOVE_USER = re.compile(r"^удалить\s+пользователя\s+@?(\S+)$", re.IGNORECASE)
_ADD_USER = re.compile(r"^добавить\s+пользователя\s+@?(\S+)$", re.IGNORECASE)


def _schedule_markup(name: str):
    boards = {
        "fields": schedule_fields_keyboard,
        "confirm": schedule_confirm_keyboard,
    }
    return boards.get(name, schedule_keyboard)()


def _split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            split_at = text.rfind("\n", start, end)
            if split_at > start:
                end = split_at
        chunks.append(text[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


async def _answer_safe(message: Message, text: str, **kwargs: object) -> None:
    parts = _split_for_telegram(text)
    if "parse_mode" not in kwargs and "<b>" in text:
        kwargs["parse_mode"] = "HTML"
    for idx, part in enumerate(parts):
        if idx == 0:
            await message.answer(part, **kwargs)
        else:
            follow = {"parse_mode": kwargs["parse_mode"]} if "parse_mode" in kwargs else {}
            await message.answer(part, **follow)


_DENIED_TEXT = "Нет доступа к боту."


def _main_menu(agent: Agent):
    titles = [title for title, _hint in agent.registry.menu_entries()]
    return main_keyboard(titles)


def _close_sections(agent: Agent, user_id: str) -> None:
    agent.disarm_quotes(user_id)
    agent.disarm_habits(user_id)
    agent.disarm_calendar(user_id)
    agent.disarm_schedule(user_id)


async def _handle_access(message: Message, agent: Agent, user_id: str, text: str) -> bool:
    """Удаление пользователя и своя отвязка. True — сообщение уже обработано."""
    service = AccessService(agent.access_pending)
    if service.has_pending(user_id):
        answer, removed_id, left = service.take_answer(user_id, text) or ("", "", False)
        if removed_id:
            agent.release_user(removed_id)
        if left:
            await _answer_safe(message, answer, reply_markup=ReplyKeyboardRemove())
        elif answer.startswith("Удалить"):
            await _answer_safe(message, answer, reply_markup=schedule_confirm_keyboard())
        else:
            await _answer_safe(message, answer, reply_markup=_main_menu(agent))
        return True

    folded = " ".join(text.replace("ё", "е").split()).casefold()
    if folded == "пользователи":
        await _answer_safe(message, service.list_text(user_id), reply_markup=_main_menu(agent))
        return True
    if folded == "отвязаться":
        _close_sections(agent, user_id)
        answer = service.ask_leave(user_id)
        markup = schedule_confirm_keyboard() if service.has_pending(user_id) else _main_menu(agent)
        await _answer_safe(message, answer, reply_markup=markup)
        return True
    remove_match = _REMOVE_USER.fullmatch(text.strip())
    if remove_match:
        _close_sections(agent, user_id)
        answer = service.ask_remove(user_id, remove_match.group(1))
        markup = schedule_confirm_keyboard() if service.has_pending(user_id) else _main_menu(agent)
        await _answer_safe(message, answer, reply_markup=markup)
        return True
    add_match = _ADD_USER.fullmatch(text.strip())
    if add_match:
        await _answer_safe(message, service.add_text(user_id, add_match.group(1)), reply_markup=_main_menu(agent))
        return True
    return False


async def _admit(message: Message) -> str:
    """«yes» — уже впущен, «new» — привязка только что создана, пусто — отказано."""
    user = message.from_user
    if user is None:
        return ""
    user_id = str(user.id)
    access = AccessRegistry(settings.sqlite_path)
    if access.is_allowed(user_id):
        return "yes"
    bound = access.bind(user_id, user.username or "")
    if bound:
        return bound
    await _answer_safe(message, _DENIED_TEXT, reply_markup=ReplyKeyboardRemove())
    return ""


def setup_handlers(agent: Agent) -> Router:
    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        if not await _admit(message):
            return
        await _answer_safe(message, "Главное меню.", reply_markup=_main_menu(agent))

    @router.message()
    async def any_message(message: Message) -> None:
        admission = await _admit(message)
        if not admission:
            return
        # For documents Telegram puts user text into caption, not text.
        text = (message.text or message.caption or "").strip()

        user_id = str(message.from_user.id) if message.from_user else ""

        if admission == "new":
            await _answer_safe(message, "Главное меню.", reply_markup=_main_menu(agent))
            return

        if await _handle_access(message, agent, user_id, text):
            return

        if text == "Помощь":
            agent.disarm_quotes(user_id)
            agent.disarm_habits(user_id)
            agent.disarm_calendar(user_id)
            agent.disarm_schedule(user_id)
            agent.travel_service.cancel(user_id)
            await _answer_safe(message, agent.help_text(user_id), reply_markup=_main_menu(agent))
            return

        if text == "Проекты":
            agent.disarm_quotes(user_id)
            agent.disarm_habits(user_id)
            agent.disarm_calendar(user_id)
            agent.disarm_schedule(user_id)
            agent.travel_service.cancel(user_id)
            await _answer_safe(message, agent.projects_text(user_id), reply_markup=projects_keyboard())
            return

        if text == "Назад":
            agent.disarm_quotes(user_id)
            agent.disarm_habits(user_id)
            agent.disarm_calendar(user_id)
            agent.disarm_schedule(user_id)
            agent.travel_service.cancel(user_id)
            await _answer_safe(message, "Главное меню.", reply_markup=_main_menu(agent))
            return

        if text == agent.quotes_tool.menu_title:
            agent.disarm_habits(user_id)
            agent.disarm_calendar(user_id)
            agent.disarm_schedule(user_id)
            await _answer_safe(message, agent.arm_quotes(user_id), reply_markup=quotes_keyboard())
            return

        if text == agent.habits_tool.menu_title:
            agent.disarm_quotes(user_id)
            agent.disarm_calendar(user_id)
            agent.disarm_schedule(user_id)
            agent.travel_service.cancel(user_id)
            await _answer_safe(message, agent.arm_habits(user_id))
            return

        if text == agent.calendar_tool.menu_title:
            agent.disarm_quotes(user_id)
            agent.disarm_habits(user_id)
            agent.disarm_schedule(user_id)
            agent.travel_service.cancel(user_id)
            await _answer_safe(message, agent.arm_calendar(user_id))
            return

        if text == agent.schedule_tool.menu_title:
            agent.disarm_quotes(user_id)
            agent.disarm_habits(user_id)
            agent.disarm_calendar(user_id)
            agent.travel_service.cancel(user_id)
            if not agent.schedule_service.allowed(user_id):
                await _answer_safe(message, agent.schedule_service.deny_text())
                return
            await _answer_safe(message, agent.arm_schedule(user_id), reply_markup=schedule_keyboard())
            return

        if text == agent.travel_tool.menu_title:
            agent.disarm_quotes(user_id)
            agent.disarm_habits(user_id)
            agent.disarm_calendar(user_id)
            agent.disarm_schedule(user_id)
            await _answer_safe(message, agent.travel_service.menu_text(user_id))
            return

        hint = agent.menu_hint(text)
        if hint:
            agent.disarm_quotes(user_id)
            agent.disarm_habits(user_id)
            agent.disarm_calendar(user_id)
            agent.disarm_schedule(user_id)
            await _answer_safe(message, hint)
            return

        travel_state, _travel_data = agent.travel_service.repo.get_state(user_id)
        if travel_state:
            await _answer_safe(message, agent.travel_service.answer(user_id, text) or "Ок.")
            return

        if user_id and agent.quotes_waiting(user_id):
            picked = asset_by_label(text)
            if picked:
                await _answer_safe(message, agent.select_quote_asset(user_id, picked), reply_markup=quotes_keyboard())
                return
            asset = agent.quote_asset(user_id)
            if asset and accepts_query(text, asset):
                result = await agent.quotes_tool.run(ticker=text, asset=asset)
                await _answer_safe(message, result.message, reply_markup=quotes_keyboard())
                return

        if user_id and agent.habits_waiting(user_id):
            habit_answer = agent.habits_service.answer_request(user_id, text)
            if habit_answer is None:
                habit_answer = agent.habits_service.section_hint(user_id)
            await _answer_safe(message, habit_answer)
            return

        if user_id and agent.calendar_waiting(user_id):
            birthday = agent.calendar_service.answer_request(user_id, text, capture=True)
            if birthday is None:
                birthday = agent.calendar_service.section_hint()
            await _answer_safe(message, birthday)
            return

        if user_id and agent.schedule_waiting(user_id):
            reply = agent.schedule_service.answer(user_id, text)
            await _answer_safe(message, reply.text, reply_markup=_schedule_markup(reply.keyboard))
            return

        agent.disarm_quotes(user_id)

        habit_answer = agent.habits_service.answer_request(user_id, text)
        if habit_answer is not None:
            await _answer_safe(message, habit_answer)
            return

        travel_answer = agent.travel_service.answer(user_id, text)
        if travel_answer is not None:
            await _answer_safe(message, travel_answer)
            return

        file_match = re.fullmatch(r"(?:файл|сохранить)\s+#?([^\s#]+)", text, flags=re.IGNORECASE)
        if file_match:
            prepared = agent.project_file(user_id, file_match.group(1))
            if isinstance(prepared, str):
                await _answer_safe(message, prepared, reply_markup=projects_keyboard())
                return
            shown = agent.tag_service.normalize_tag(file_match.group(1))
            await message.answer_document(
                FSInputFile(prepared, filename=f"{shown}.txt"),
                caption=f"Обсуждение #{shown}. Файл можно сохранить, переслать или отправить почтой.",
                reply_markup=projects_keyboard(),
            )
            return

        create_match = re.fullmatch(r"(?:добавить|создать)\s+проект\s+(.+)", text, flags=re.IGNORECASE)
        if create_match:
            ok, info = agent.create_project(user_id, create_match.group(1))
            answer = f"{info}\n\n{agent.projects_text(user_id)}" if ok else info
            await _answer_safe(message, answer, reply_markup=projects_keyboard())
            return

        delete_match = re.fullmatch(r"удалить\s+#?([^\s#]+)", text, flags=re.IGNORECASE)
        if delete_match:
            ok, info = agent.delete_topic_by_tag(user_id, delete_match.group(1))
            answer = info if ok else f"{info}\n\n{agent.projects_text(user_id)}"
            await _answer_safe(message, answer)
            return

        rename_match = re.fullmatch(
            r"переименовать\s+#?([^\s#]+)\s+#?([^\s#]+)",
            text,
            flags=re.IGNORECASE,
        )
        if rename_match:
            ok, info = agent.rename_topic_tag(user_id, rename_match.group(1), rename_match.group(2))
            answer = info if ok else f"{info}\n\n{agent.projects_text(user_id)}"
            await _answer_safe(message, answer)
            return

        file_path = None
        file_name = None
        if message.document:
            file_name = message.document.file_name
            if file_name:
                dst = settings.documents_raw_dir / user_id / Path(file_name).name
                dst.parent.mkdir(parents=True, exist_ok=True)
                file_obj = await message.bot.get_file(message.document.file_id)
                await message.bot.download(file_obj, destination=dst)
                file_path = str(dst)

        incoming = IncomingMessage(
            user_id=str(message.from_user.id),
            text=text,
            file_path=file_path,
            file_name=file_name,
        )
        answer = await agent.handle(incoming)
        await _answer_safe(message, answer)

    return router
