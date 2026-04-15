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

## Автодеплой через Docker (GitHub Actions -> VPS)

В репозиторий добавлен workflow `.github/workflows/deploy.yml`.
Он запускается при каждом пуше в `main` (и вручную через `workflow_dispatch`) и делает следующее:

1. Подключается к серверу по SSH.
2. Клонирует репозиторий (если его еще нет на сервере).
3. Обновляет код до `origin/main`.
4. Создает/обновляет `.env` на сервере из секрета GitHub.
5. Выполняет `docker compose -f docker-compose.prod.yml up -d --build`.

### 1) Подготовка сервера

Подключитесь к серверу и установите Docker + Compose plugin:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

После `usermod` переподключитесь по SSH.

### 2) Секреты в GitHub

В `Settings -> Secrets and variables -> Actions` добавьте:

- `SERVER_HOST` - IP сервера (например `95.163.223.66`)
- `SERVER_PORT` - обычно `22`
- `SERVER_USER` - пользователь на сервере (например `root` или `ubuntu`)
- `SERVER_SSH_KEY` - приватный SSH-ключ (который имеет доступ к серверу)
- `APP_DIR` - путь проекта на сервере (например `/opt/govorun_ai_assist`)
- `APP_ENV_FILE` - полный текст вашего `.env` (многострочный секрет)

Пример значения `APP_ENV_FILE`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini-2025-08-07
OPENAI_IMAGE_MODEL=gpt-image-1
WEB_HOST=0.0.0.0
WEB_PORT=8000
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### 3) Первый запуск

Сделайте пуш в `main` или запустите workflow вручную во вкладке `Actions`.
После успешного деплоя приложение будет доступно на:

- `http://<SERVER_HOST>:8000`