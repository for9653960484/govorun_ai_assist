from __future__ import annotations


def normalize_user_text(text: str) -> str:
    """Нормализует пользовательский ввод."""
    return " ".join(text.strip().split())
