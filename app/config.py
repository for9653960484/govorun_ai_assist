from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(slots=True)
class Settings:
    """Глобальные настройки приложения."""

    app_name: str = os.getenv("APP_NAME", "AI Секретарь")
    env: str = os.getenv("APP_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini-2025-08-07")
    openai_image_model: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL") or None

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    web_host: str = os.getenv("WEB_HOST", "127.0.0.1")
    web_port: int = int(os.getenv("WEB_PORT", "8000"))

    project_root: Path = PROJECT_ROOT
    data_root: Path = project_root / "data"
    documents_raw_dir: Path = data_root / "documents" / "raw"
    documents_parsed_dir: Path = data_root / "documents" / "parsed"
    documents_index_dir: Path = data_root / "documents" / "index"
    sqlite_path: Path = data_root / "db" / "assistant.sqlite3"


settings = Settings()
