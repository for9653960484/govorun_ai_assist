from __future__ import annotations

from pathlib import Path


SUPPORTED_EXT = {".txt", ".md", ".pdf", ".docx"}


def validate_document_path(path: Path) -> None:
    """Проверяет, что файл поддерживается документным конвейером."""
    if path.suffix.lower() not in SUPPORTED_EXT:
        raise ValueError(f"Неподдерживаемый формат: {path.suffix}")
