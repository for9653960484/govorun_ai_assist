# AI-секретарь и советник

Стартовый каркас масштабируемого AI-агента на Python 3.11+.

## Что реализовано

- Модульная архитектура с разделением ядра, памяти, документов, инструментов и UI.
- Два канала UI: Telegram и Web (FastAPI).
- Общий роутер сценариев: чат, вопросы по документам, загрузка файла, вызов инструмента, переключение по тегу.
- Короткая память в RAM: хранение последних сообщений по `user_id`.
- Долгая память в SQLite: темы, теги, заметки, сохраненные результаты поиска.
- Календарь в SQLite: ФИО, день/месяц/год рождения, поиск по ФИО, выборка по месяцу.
- Реестр инструментов и заглушки: `weather_stub`, `stocks_stub`, `crypto_stub`, `travel_expenses_stub`.
- Добавлен инструмент генерации изображений `image_gen` (OpenAI Images API, модель по умолчанию `gpt-image-1`).
- Интеграция OpenAI через Responses API с конфигурацией модели/ключа из `.env`.

## Что пока заглушки

- Инструменты `weather_stub`, `stocks_stub`, `crypto_stub`, `travel_expenses_stub` содержат TODO для реальных API.
- Модули `app/tools/search/service.py` и `app/tools/memory_tools/service.py` оставлены как расширяемые заготовки.
- Telegram-обработчик загрузки файлов требует доработки скачивания файла по `file_id`.

## Переменные окружения (`.env`)

- `OPENAI_API_KEY` - ключ OpenAI.
- `OPENAI_MODEL` - по умолчанию `gpt-5-mini-2025-08-07`.
- `OPENAI_IMAGE_MODEL` - по умолчанию `gpt-image-1` (для инструмента `image_gen`).
- `OPENAI_BASE_URL` - опционально, если нужен кастомный endpoint.
- `TELEGRAM_BOT_TOKEN` - опционально, для Telegram-канала.
- `WEB_HOST` - по умолчанию `127.0.0.1`.
- `WEB_PORT` - по умолчанию `8000`.

Приложение автоматически загружает `project/.env` через `python-dotenv`.

Пример `project/.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini-2025-08-07
OPENAI_IMAGE_MODEL=gpt-image-1
WEB_HOST=127.0.0.1
WEB_PORT=8000
# TELEGRAM_BOT_TOKEN=your_telegram_token
```

## Запуск

1. Создать виртуальное окружение и установить зависимости:
   - `py -m venv .venv`
   - Windows: `.venv\Scripts\activate`
   - Linux: `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Создать и настроить файл `.env` в корне `project/`.
3. Запустить:
   - `py -m app.main`
4. Web UI: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Пример запроса на генерацию изображения

Пример фразы, которую можно отправить агенту в Telegram или Web UI:

```text
Сгенерируй изображение: минималистичный постер с неоновым городом ночью, формат 1024x1024.
```

Агент при необходимости вызовет инструмент `image_gen` и вернет ссылку на результат.

## Структура

См. каталоги `app/` (логика) и `data/` (данные). Бизнес-логика не дублируется в UI-слое.