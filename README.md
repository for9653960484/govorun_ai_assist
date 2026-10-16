# AI-секретарь и советник

Стартовый каркас масштабируемого AI-агента на Python 3.11+.

## Что реализовано

- Модульная архитектура с разделением ядра, памяти, документов, инструментов и UI.
- Два канала UI: Telegram и Web (FastAPI).
- Общий роутер сценариев: чат, вопросы по документам, загрузка файла, вызов инструмента, переключение по тегу.
- Короткая память в RAM: хранение последних сообщений по `user_id`.
- Долгая память в SQLite: темы, теги, заметки, сохраненные результаты поиска.
- Календарь в SQLite: дни рождения за месяц в формате `ДД.ММ - ФИО`, по возрастанию даты, без напоминаний.
- Котировки: текущая цена по тикеру (криптовалюта через CoinGecko, акция через Yahoo Finance).
- Путешествие: поездка, курс валют и учёт расходов.
- Привычки: до 5 действий, отметка за сегодня, неделя со статусом сделано/не сделано. Если к 15:00 по Москве привычка не отмечена, Telegram присылает короткое напоминание.
- Погода через OpenWeather (ключ в `.env`, локальный кэш на 3 часа).
- Генерация изображений `image_gen` (OpenAI Images API, модель по умолчанию `gpt-image-1`).
- Меню Telegram «Показать темы» собирается из зарегистрированных инструментов. Кнопка даёт короткую подсказку; «Котировки», «Привычки» и «Путешествие» сразу открывают свой сценарий.
- Ответы агента короткие: суть в нескольких фразах.
- Интеграция LLM через [LangChain](https://docs.langchain.com/oss/python/langchain/quickstart): `create_agent`, инструменты из реестра, память по `thread_id` (LangGraph `InMemorySaver`).

## Что пока заглушки

- Модули `app/tools/search/service.py` и `app/tools/memory_tools/service.py` не подключены к агенту.

## Переменные окружения (`.env`)

- `OPENAI_API_KEY` - ключ OpenAI.
- `OPENWEATHER_API_KEY` - ключ OpenWeather (для погоды).
- `EXCHANGE_API_KEY` - необязательно, курс валют в поездке. Без ключа берётся открытый курс.
- `OPENAI_MODEL` - по умолчанию `gpt-5-mini-2025-08-07`.
- `OPENAI_IMAGE_MODEL` - по умолчанию `gpt-image-1` (для инструмента `image_gen`).
- `OPENAI_BASE_URL` - опционально, если нужен кастомный endpoint.
- `LANGCHAIN_TEMPERATURE` - температура модели для LangChain-агента (по умолчанию `0.3`).
- `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` - опционально, трассировка агента в [LangSmith](https://smith.langchain.com).
- `TELEGRAM_BOT_TOKEN` - опционально, для Telegram-канала.
- `WEB_HOST` - по умолчанию `127.0.0.1`.
- `WEB_PORT` - по умолчанию `8000`.

Приложение автоматически загружает `.env` из корня репозитория через `python-dotenv`.

Пример `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
OPENAI_MODEL=gpt-5-mini-2025-08-07
OPENAI_IMAGE_MODEL=gpt-image-1
WEB_HOST=127.0.0.1
WEB_PORT=8000
# TELEGRAM_BOT_TOKEN=your_telegram_token
```

## Запуск

Нужен Python 3.11 или 3.12. На Windows по умолчанию может стоять 3.14: LangChain на нём стартует, но пишет предупреждение о несовместимости Pydantic V1. Для окружения лучше явно выбрать 3.12: `py -3.12 -m venv .venv`.

Команды ниже выполняются из корня репозитория. В PowerShell их нужно вводить без обратных кавычек из этого файла.

1. Создать виртуальное окружение и установить зависимости.

   Windows (PowerShell):

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

   На Windows ставьте пакеты через `python.exe -m pip`, а не через `pip` или `pip.exe`. Лаунчер `pip.exe` записывает абсолютный путь к интерпретатору и перестает находить его, если в пути есть кириллица или каталог проекта перенесли. После переноса папки окружение нужно создать заново.

2. Положить файл `.env` в корень репозитория и заполнить его по примеру выше.
3. Запустить интерпретатором из окружения, а не системным `py` (`py` не видит активированное `.venv`):

   Windows:

   ```powershell
   .\.venv\Scripts\python.exe -m app.main
   ```

   Linux:

   ```bash
   python -m app.main
   ```

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

В репозиторий добавлены два workflow:

- `.github/workflows/build-image.yml` - собирает Docker-образ и публикует его в GHCR (`ghcr.io`).
- `.github/workflows/deploy.yml` - после успешной сборки образа выполняет деплой на VPS.

Схема работы:

1. Подключается к серверу по SSH.
2. Клонирует репозиторий (если его еще нет на сервере).
3. Обновляет код до `origin/main`.
4. Создает/обновляет `.env` на сервере из секрета GitHub.
5. Выполняет вход в GHCR, затем `docker compose -f docker-compose.prod.yml pull`.
6. Запускает `docker compose -f docker-compose.prod.yml up -d --remove-orphans`.

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
- `GHCR_USER` - GitHub-логин, у которого есть доступ к пакетам
- `GHCR_TOKEN` - Personal Access Token с правом `read:packages`

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
Рекомендуемый порядок:

1. `Build and push Docker image`
2. `Deploy to production` (автоматически после успешной сборки, либо вручную)

После успешного деплоя приложение будет доступно на:

- `http://<SERVER_HOST>:8000`