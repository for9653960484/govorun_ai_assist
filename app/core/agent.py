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
from app.tools.crypto_stub import CryptoStubTool
from app.tools.image_gen_tool import ImageGenTool
from app.tools.stocks_stub import StocksStubTool
from app.tools.travel_expenses_stub import TravelExpensesStubTool
from app.tools.weather_stub import WeatherStubTool


class Agent:
    """Ядро AI-агента: маршрутизация и оркестрация подсистем."""

    def __init__(self) -> None:
        self.short_memory = ShortMemory(limit=5)
        self.registry = ToolRegistry()
        self._register_tools()

        self.doc_service = DocumentService()
        self.long_repo = LongMemoryRepository(settings.sqlite_path)
        self.tag_service = TagService(self.long_repo)
        self.user_service = UserService(UserRepository(settings.sqlite_path))
        self.calendar_service = CalendarService(CalendarRepository(settings.sqlite_path))
        self.chat_service = ChatService(self.short_memory, self.registry)

        self.router = Router(known_tools=self.registry.list_names())

    def _register_tools(self) -> None:
        self.registry.register(WeatherStubTool())
        self.registry.register(StocksStubTool())
        self.registry.register(CryptoStubTool())
        self.registry.register(TravelExpensesStubTool())
        self.registry.register(ImageGenTool())

    def topics_text(self) -> str:
        topics = self.tag_service.list_topics()
        lines = ["Доступные темы:"] + [f"- #{x['tag']} ({x['name']})" for x in topics]
        lines += [
            "",
            "Редактирование:",
            "- удалить #тег",
            "- переименовать #старый_тег #новый_тег",
        ]
        return "\n".join(lines)

    def rename_topic_tag(self, old_tag: str, new_tag: str) -> tuple[bool, str]:
        return self.tag_service.rename_topic_tag(old_tag, new_tag)

    def delete_topic_by_tag(self, tag: str) -> tuple[bool, str]:
        return self.tag_service.delete_topic_by_tag(tag)

    async def handle(self, incoming: IncomingMessage) -> str:
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
            topic = self.tag_service.switch_topic(decision.tag)
            if not topic:
                return f"Тег #{decision.tag} не найден.\n\n{self.topics_text()}"
            self.user_service.set_active_tag(incoming.user_id, decision.tag)
            return f"Активная тема переключена на #{decision.tag} ({topic['name']})."

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

        if decision.route == RouteType.TOOL:
            return await self.chat_service.ask(incoming.user_id, incoming.text)

        if decision.route == RouteType.CLARIFY:
            return (
                CLARIFY_PROMPT
                + "1) Ответить по файлу\n"
                + "2) Просто сохранить и индексировать файл\n"
                + "3) Обычный чат"
            )

        return await self.chat_service.ask(incoming.user_id, incoming.text)
