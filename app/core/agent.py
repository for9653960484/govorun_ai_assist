from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.core.prompts import CLARIFY_PROMPT
from app.core.registry import ToolRegistry
from app.core.router import Router
from app.core.types import IncomingMessage, RouteType
from app.db.repositories import UserRepository
from app.memory.long_memory.repository import LongMemoryRepository
from app.memory.short_memory import ShortMemory
from app.services.chat_service import ChatService
from app.services.doc_service import DocumentService
from app.services.tag_service import TagService
from app.services.user_service import UserService
from app.tools.calendar.repository import CalendarRepository
from app.tools.calendar.service import CalendarService
from app.tools.calendar.tool import CalendarTool
from app.tools.habits.repository import HabitsRepository
from app.tools.habits.service import HabitsService
from app.tools.habits.tool import HabitsTool
from app.tools.image_gen_tool import ImageGenTool
from app.tools.quotes_tool import QuotesTool, prompt_for
from app.tools.schedule.birthdays import paint_birthdays, sync_birthdays
from app.tools.schedule.service import ScheduleService
from app.utils.logger import get_logger
from app.tools.schedule.tool import ScheduleTool
from app.tools.travel.repository import TravelRepository
from app.tools.travel.service import TravelService
from app.tools.travel.tool import TravelTool
from app.tools.weather_stub import WeatherStubTool


class Agent:
    """Ядро AI-агента: маршрутизация и оркестрация подсистем."""

    def __init__(self) -> None:
        self.short_memory = ShortMemory(limit=5)
        self.registry = ToolRegistry()
        self.calendar_service = CalendarService(CalendarRepository(settings.sqlite_path))
        self.habits_service = HabitsService(HabitsRepository(settings.sqlite_path))
        self.habits_tool = HabitsTool(self.habits_service)
        self.travel_service = TravelService(TravelRepository(settings.sqlite_path))
        self.travel_tool = TravelTool(self.travel_service)
        self.quotes_tool = QuotesTool()
        self.calendar_tool = CalendarTool(self.calendar_service)
        self.schedule_service = ScheduleService()
        self.schedule_tool = ScheduleTool(self.schedule_service)
        try:
            sync_birthdays()
            paint_birthdays()
        except Exception:
            get_logger(__name__).exception("Не удалось передать дни рождения в Google Календарь")
        self._quote_assets: dict[str, str] = {}
        self._habits_open: set[str] = set()
        self._calendar_open: set[str] = set()
        self._schedule_open: set[str] = set()
        self.access_pending: dict[str, str] = {}
        self._register_tools()

        self.doc_service = DocumentService()
        self.long_repo = LongMemoryRepository(settings.sqlite_path)
        self.tag_service = TagService(self.long_repo)
        self.user_service = UserService(UserRepository(settings.sqlite_path))
        self.chat_service = ChatService(self.short_memory, self.registry)

        self.router = Router(known_tools=self.registry.list_names())

    def _register_tools(self) -> None:
        self.registry.register(WeatherStubTool())
        self.registry.register(self.quotes_tool)
        self.registry.register(self.travel_tool)
        self.registry.register(self.calendar_tool)
        self.registry.register(self.habits_tool)
        self.registry.register(self.schedule_tool)
        self.registry.register(ImageGenTool())

    def projects_text(self, user_id: str) -> str:
        topics = self.tag_service.list_topics(user_id)
        lines = ["Текущие проекты:"]
        lines += [f"- #{item['tag']} ({item['name']})" for item in topics] or ["Пока нет."]
        lines += [
            "",
            "Редактирование:",
            "- добавить проект название",
            "- удалить #тег",
            "- переименовать #старый_тег #новый_тег",
            "- файл #тег",
        ]
        return "\n".join(lines)

    def help_text(self, user_id: str) -> str:
        items = [
            "Добавить проект: добавить проект название",
            "Сменить проект: #тег",
            "Удалить проект: удалить #тег",
            "Переименовать проект: переименовать #старый_тег #новый_тег",
            "Файл обсуждения: файл #тег",
        ]
        if user_id == settings.telegram_allowed_user_id:
            items += [
                "Пользователи: пользователи",
                "Удалить пользователя: удалить пользователя @имя",
            ]
        else:
            items.append("Отвязаться от бота: отвязаться")
        return "Помощь\n\n" + "\n\n".join(items)

    def arm_quotes(self, user_id: str) -> str:
        self._quote_assets[user_id] = ""
        return (
            "Команды боту:\n"
            "<b>выберите</b> группу: валюты, криптовалюты, акции или акции (RU)"
        )

    def select_quote_asset(self, user_id: str, asset: str) -> str:
        self._quote_assets[user_id] = asset
        return prompt_for(asset)

    def quote_asset(self, user_id: str) -> str:
        return self._quote_assets.get(user_id, "")

    def disarm_quotes(self, user_id: str) -> None:
        self._quote_assets.pop(user_id, None)

    def quotes_waiting(self, user_id: str) -> bool:
        return user_id in self._quote_assets

    def arm_habits(self, user_id: str) -> str:
        self._habits_open.add(user_id)
        return self.habits_service.open_text(user_id)

    def disarm_habits(self, user_id: str) -> None:
        self._habits_open.discard(user_id)

    def habits_waiting(self, user_id: str) -> bool:
        return user_id in self._habits_open

    def arm_calendar(self, user_id: str) -> str:
        self._calendar_open.add(user_id)
        return self.calendar_service.section_text()

    def disarm_calendar(self, user_id: str) -> None:
        self._calendar_open.discard(user_id)

    def calendar_waiting(self, user_id: str) -> bool:
        return user_id in self._calendar_open

    def arm_schedule(self, user_id: str) -> str:
        self._schedule_open.add(user_id)
        return self.schedule_service.open_text()

    def disarm_schedule(self, user_id: str) -> None:
        self._schedule_open.discard(user_id)
        self.schedule_service.clear_dialog(user_id)

    def schedule_waiting(self, user_id: str) -> bool:
        return user_id in self._schedule_open

    def release_user(self, user_id: str) -> None:
        """Сбрасывает память и открытые разделы удалённого пользователя."""
        if not user_id:
            return
        self.short_memory.clear(user_id)
        self.disarm_quotes(user_id)
        self.disarm_habits(user_id)
        self.disarm_calendar(user_id)
        self.disarm_schedule(user_id)
        self.doc_service.drop_user(user_id)

    def menu_hint(self, title: str) -> str | None:
        for menu_title, hint in self.registry.menu_entries():
            if menu_title == title:
                return hint
        return None

    def create_project(self, user_id: str, name: str) -> tuple[bool, str]:
        return self.tag_service.create_project(user_id, name)

    def project_file(self, user_id: str, tag: str) -> Path | str:
        """Путь к текстовому файлу обсуждения. Строка — почему файла нет."""
        prepared = self.tag_service.discussion_letter(user_id, tag)
        if isinstance(prepared, str):
            return prepared
        _subject, body = prepared
        shown = self.tag_service.normalize_tag(tag)
        folder = settings.data_root / "projects" / user_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{shown}.txt"
        path.write_text(body, encoding="utf-8")
        return path

    def _remember_project(self, user_id: str, question: str, answer: str) -> None:
        tag = self.user_service.get_active_tag(user_id) or ""
        if not tag:
            return
        self.tag_service.remember_discussion(user_id, tag, question, answer)

    def rename_topic_tag(self, user_id: str, old_tag: str, new_tag: str) -> tuple[bool, str]:
        return self.tag_service.rename_topic_tag(user_id, old_tag, new_tag)

    def delete_topic_by_tag(self, user_id: str, tag: str) -> tuple[bool, str]:
        return self.tag_service.delete_topic_by_tag(user_id, tag)

    async def handle(self, incoming: IncomingMessage) -> str:
        self.habits_tool.bind(incoming.user_id)
        self.travel_tool.bind(incoming.user_id)
        self.calendar_tool.bind(incoming.user_id)
        self.schedule_tool.bind(incoming.user_id)
        decision = self.router.route(incoming)

        if decision.route == RouteType.FILE_ONLY and incoming.file_path:
            src = Path(incoming.file_path)
            status = self.doc_service.ingest(incoming.user_id, src)
            return (
                "Файл обработан. "
                f"Документ: {status['doc_id']}, чанков: {status['chunks']}. "
                f"Индекс: {status['index_path']}"
            )

        if decision.route == RouteType.TAG_SWITCH and decision.tag:
            topic = self.tag_service.switch_topic(incoming.user_id, decision.tag)
            if not topic:
                return f"Тег #{decision.tag} не найден.\n\n{self.projects_text(incoming.user_id)}"
            active = self.tag_service.normalize_tag(decision.tag)
            self.user_service.set_active_tag(incoming.user_id, active)
            return f"Активный проект: #{active} ({topic['name']}). Дальше диалог сохранится в нём."

        if decision.route == RouteType.DOCUMENT_QA:
            if incoming.file_path:
                src = Path(incoming.file_path)
                status = self.doc_service.ingest(incoming.user_id, src)
                index_path = Path(status["index_path"])
            else:
                index_path = self.doc_service.get_last_index_path(incoming.user_id)
                if not index_path:
                    return (
                        "Нет загруженного документа для ответа. "
                        "Сначала отправьте файл (txt/md/pdf/docx)."
                    )
            context_chunks = self.doc_service.answer_with_doc(index_path, incoming.text)
            context = "\n\n".join([x["text"] for x in context_chunks])
            return await self.chat_service.ask(incoming.user_id, incoming.text, extra_context=context)

        if incoming.text.strip():
            habit_answer = self.habits_service.answer_request(incoming.user_id, incoming.text)
            if habit_answer is not None:
                return habit_answer
            travel_answer = self.travel_service.answer(incoming.user_id, incoming.text)
            if travel_answer is not None:
                return travel_answer
            birthday = self.calendar_service.answer_request(
                incoming.user_id,
                incoming.text,
                capture=self.calendar_waiting(incoming.user_id),
            )
            if birthday is not None:
                return birthday

        if decision.route == RouteType.TOOL:
            return await self.chat_service.ask(incoming.user_id, incoming.text)

        if decision.route == RouteType.CLARIFY:
            return (
                CLARIFY_PROMPT
                + "1) Ответить по файлу\n"
                + "2) Просто сохранить и индексировать файл\n"
                + "3) Обычный чат"
            )

        answer = await self.chat_service.ask(incoming.user_id, incoming.text)
        self._remember_project(incoming.user_id, incoming.text, answer)
        return answer
