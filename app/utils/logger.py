from __future__ import annotations

import logging
import sys


def setup_logger(level: str = "INFO") -> None:
    """Настраивает единый формат логирования."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    """Возвращает логгер по имени модуля."""
    return logging.getLogger(name)
