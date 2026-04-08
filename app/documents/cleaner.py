from __future__ import annotations

import re


class TextCleaner:
    """Очистка и нормализация текста документа."""

    def clean(self, raw_text: str) -> str:
        text = raw_text.replace("\x00", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()
