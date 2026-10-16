from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import settings
from app.core.agent import Agent
from app.core.types import IncomingMessage
from app.ui.telegram.keyboards import main_keyboard, topics_keyboard

router = Router()
TELEGRAM_MESSAGE_LIMIT = 4096


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
    for idx, part in enumerate(parts):
        if idx == 0:
            await message.answer(part, **kwargs)
        else:
            await message.answer(part)


def setup_handlers(agent: Agent) -> Router:
    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await _answer_safe(message, agent.topics_text(), reply_markup=main_keyboard())

    @router.message()
    async def any_message(message: Message) -> None:
        # For documents Telegram puts user text into caption, not text.
        text = (message.text or message.caption or "").strip()

        user_id = str(message.from_user.id) if message.from_user else ""

        if text == "Показать темы":
            agent.disarm_quotes(user_id)
            titles = [title for title, _hint in agent.registry.menu_entries()]
            await _answer_safe(message, agent.topics_text(), reply_markup=topics_keyboard(titles))
            return

        if text == "Назад":
            agent.disarm_quotes(user_id)
            agent.travel_service.cancel(user_id)
            await _answer_safe(message, "Главное меню.", reply_markup=main_keyboard())
            return

        if text == agent.quotes_tool.menu_title:
            await _answer_safe(message, agent.arm_quotes(user_id))
            return

        if text == agent.habits_tool.menu_title:
            agent.disarm_quotes(user_id)
            await _answer_safe(message, agent.habits_service.week_board(user_id))
            return

        if text == agent.travel_tool.menu_title:
            agent.disarm_quotes(user_id)
            await _answer_safe(message, agent.travel_service.menu_text(user_id))
            return

        hint = agent.menu_hint(text)
        if hint:
            agent.disarm_quotes(user_id)
            await _answer_safe(message, hint)
            return

        travel_state, _travel_data = agent.travel_service.repo.get_state(user_id)
        if travel_state:
            await _answer_safe(message, agent.travel_service.answer(user_id, text) or "Ок.")
            return

        if user_id and agent.quotes_waiting(user_id) and re.fullmatch(r"[A-Za-z][A-Za-z0-9.\-]{0,14}", text):
            result = await agent.quotes_tool.run(ticker=text)
            await _answer_safe(message, result.message)
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

        delete_match = re.fullmatch(r"удалить\s+#?([^\s#]+)", text, flags=re.IGNORECASE)
        if delete_match:
            ok, info = agent.delete_topic_by_tag(delete_match.group(1))
            answer = info if ok else f"{info}\n\n{agent.topics_text()}"
            await _answer_safe(message, answer)
            return

        rename_match = re.fullmatch(
            r"переименовать\s+#?([^\s#]+)\s+#?([^\s#]+)",
            text,
            flags=re.IGNORECASE,
        )
        if rename_match:
            ok, info = agent.rename_topic_tag(rename_match.group(1), rename_match.group(2))
            answer = info if ok else f"{info}\n\n{agent.topics_text()}"
            await _answer_safe(message, answer)
            return

        file_path = None
        file_name = None
        if message.document:
            file_name = message.document.file_name
            if file_name:
                dst = settings.documents_raw_dir / file_name
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
