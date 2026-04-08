from __future__ import annotations

from app.core.types import IncomingMessage, RouteDecision, RouteType


KNOWN_DOC_HINTS = ("документ", "файл", "по документу")


class Router:
    """Маршрутизатор пользовательских входов."""

    def __init__(self, known_tools: list[str]) -> None:
        self._known_tools = known_tools

    def detect_tag(self, text: str) -> str | None:
        txt = text.strip()
        if txt.startswith("#") and len(txt) > 1:
            return txt.split()[0][1:]
        return None

    def is_document_question(self, text: str) -> bool:
        low = text.lower()
        return any(x in low for x in KNOWN_DOC_HINTS)

    def detect_tool(self, text: str) -> str | None:
        low = text.lower()
        for name in self._known_tools:
            if name.replace("_stub", "") in low or name in low:
                return name
        return None

    def route(self, msg: IncomingMessage) -> RouteDecision:
        has_file = bool(msg.file_path)
        has_text = bool(msg.text.strip())
        tag = self.detect_tag(msg.text)

        if has_file and not has_text:
            return RouteDecision(route=RouteType.FILE_ONLY, reason="Получен только файл")

        if tag:
            return RouteDecision(route=RouteType.TAG_SWITCH, reason="Найден тег темы", tag=tag)

        if has_text and self.is_document_question(msg.text):
            return RouteDecision(route=RouteType.DOCUMENT_QA, reason="Вопрос по документу")

        tool_name = self.detect_tool(msg.text)
        if tool_name:
            return RouteDecision(route=RouteType.TOOL, reason="Обнаружен запрос к инструменту", tool_name=tool_name)

        if has_file and has_text:
            return RouteDecision(
                route=RouteType.CLARIFY,
                reason="Неоднозначный запрос",
            )

        return RouteDecision(route=RouteType.CHAT, reason="Обычный чат")
