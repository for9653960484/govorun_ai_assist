"""Одноразовое подключение календаря владельца.

Запуск из корня репозитория, когда в .env уже есть
GOOGLE_CALENDAR_CLIENT_ID и GOOGLE_CALENDAR_CLIENT_SECRET:

    .\\.venv\\Scripts\\python.exe -m app.tools.schedule.google_auth

В клиенте OAuth должен быть разрешён адрес http://127.0.0.1:8765/
"""

from __future__ import annotations

import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from app.config import settings

_REDIRECT = "http://127.0.0.1:8765/"
_SCOPE = "https://www.googleapis.com/auth/calendar"


def main() -> None:
    client_id = settings.google_calendar_client_id
    client_secret = settings.google_calendar_client_secret
    if not client_id or not client_secret:
        print("Задайте GOOGLE_CALENDAR_CLIENT_ID и GOOGLE_CALENDAR_CLIENT_SECRET в .env")
        return
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": _REDIRECT,
            "response_type": "code",
            "scope": _SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    webbrowser.open(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    code = _wait_for_code()
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": _REDIRECT,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    if response.status_code != 200:
        print("Google не выдал токен. Проверьте клиента OAuth и адрес перенаправления.")
        return
    refresh = str(response.json().get("refresh_token") or "")
    if not refresh:
        print("Google не прислал долгоживущий токен. Повторите вход с согласием.")
        return
    print("Добавьте в .env строку:")
    print(f"GOOGLE_CALENDAR_REFRESH_TOKEN={refresh}")


def _wait_for_code() -> str:
    holder: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            query = parse_qs(urlparse(self.path).query)
            holder["code"] = (query.get("code") or [""])[0]
            body = "Можно закрыть это окно и вернуться в терминал.".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 8765), Handler)
    server.handle_request()
    code = holder.get("code", "")
    if not code:
        raise SystemExit("Google не вернул код подтверждения.")
    return code


if __name__ == "__main__":
    main()
