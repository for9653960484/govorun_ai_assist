from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.config import settings
from app.tools.base import BaseTool, ToolResult

CACHE_MAX_AGE_SECONDS = 3 * 60 * 60
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AIR_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"


def _api_key() -> str:
    # Backward compatibility: accept both old API_KEY and explicit OPENWEATHER_API_KEY.
    return os.getenv("OPENWEATHER_API_KEY") or os.getenv("API_KEY", "")


def _cache_file() -> Path:
    return settings.data_root / "weather_cache.json"


def _request_json(url: str, params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    delays = [1, 2, 4]
    for attempt in range(len(delays) + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
        except requests.RequestException:
            if attempt < len(delays):
                time.sleep(delays[attempt])
                continue
            return None, "Сетевая ошибка: не удалось связаться с OpenWeather."
        if response.status_code == 429 and attempt < len(delays):
            time.sleep(delays[attempt])
            continue
        if response.status_code != 200:
            try:
                message = response.json().get("message", "unknown error")
            except ValueError:
                message = "unknown error"
            return None, f"OpenWeather: {response.status_code} ({_localize_api_message(message, response.status_code)})"
        try:
            return response.json(), None
        except ValueError:
            return None, "Ошибка обработки ответа OpenWeather."
    return None, "Сетевая ошибка."


def _load_cache() -> dict[str, Any]:
    path = _cache_file()
    if not path.exists():
        return {"entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"entries": []}
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return data
    return {"entries": []}


def _save_cache(cache: dict[str, Any]) -> None:
    path = _cache_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _cache_key(latitude: float, longitude: float) -> str:
    return f"{latitude:.4f},{longitude:.4f}"


def _cache_get(latitude: float, longitude: float) -> dict[str, Any] | None:
    cache = _load_cache()
    key = _cache_key(latitude, longitude)
    for entry in cache["entries"]:
        if entry.get("key") != key:
            continue
        fetched_at = entry.get("fetched_at")
        if not fetched_at:
            continue
        try:
            ts = datetime.fromisoformat(fetched_at)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age <= CACHE_MAX_AGE_SECONDS:
            return entry.get("current")
    return None


def _cache_put(latitude: float, longitude: float, current: dict[str, Any]) -> None:
    cache = _load_cache()
    key = _cache_key(latitude, longitude)
    now = datetime.now(timezone.utc).isoformat()
    entries: list[dict[str, Any]] = cache["entries"]
    for entry in entries:
        if entry.get("key") == key:
            entry.update({"fetched_at": now, "current": current})
            _save_cache(cache)
            return
    entries.append({"key": key, "fetched_at": now, "current": current})
    cache["entries"] = entries[-50:]
    _save_cache(cache)


def _resolve_location(city: str, country_code: str | None, api_key: str) -> tuple[tuple[float, float] | None, str | None]:
    locations, err = _request_json(
        GEOCODE_URL,
        {"q": city, "limit": 5, "appid": api_key},
    )
    if err:
        return None, err
    if not locations:
        return None, "Город не найден."
    if country_code:
        for loc in locations:
            if str(loc.get("country", "")).lower() == country_code.lower():
                return (float(loc["lat"]), float(loc["lon"])), None
    first = locations[0]
    return (float(first["lat"]), float(first["lon"])), None


def _format_temperature(value: float | int | str | None) -> str:
    if value is None:
        return "н/д"
    try:
        return str(round(float(value)))
    except (TypeError, ValueError):
        return "н/д"


def _format_precipitation(data: dict[str, Any]) -> str:
    rain = data.get("rain", {})
    snow = data.get("snow", {})
    rain_amount = rain.get("1h") or rain.get("3h")
    snow_amount = snow.get("1h") or snow.get("3h")
    if rain_amount:
        return f"дождь {rain_amount} мм"
    if snow_amount:
        return f"снег {snow_amount} мм"
    return "без осадков"


def _format_weather(data: dict[str, Any]) -> str:
    name = data.get("name", "Неизвестно")
    country = data.get("sys", {}).get("country", "")
    description = (data.get("weather") or [{}])[0].get("description", "нет данных")
    main = data.get("main", {})
    wind_speed = data.get("wind", {}).get("speed", "н/д")
    return (
        f"Город: {name}{f' ({country})' if country else ''}\n"
        f"Погода: {description}\n"
        f"Температура: {_format_temperature(main.get('temp'))} °C\n"
        f"Ощущается как: {_format_temperature(main.get('feels_like'))} °C\n"
        f"Влажность: {main.get('humidity', 'н/д')}%\n"
        f"Осадки: {_format_precipitation(data)}\n"
        f"Ветер: {wind_speed} м/с"
    )


def _format_forecast(data: dict[str, Any]) -> str:
    city = data.get("city", {})
    lines = [f"Прогноз на 5 дней: {city.get('name', 'Неизвестно')}"]
    daily: dict[str, list[dict[str, Any]]] = {}
    for item in data.get("list", []):
        dt = datetime.fromtimestamp(item.get("dt", 0), tz=timezone.utc).strftime("%d.%m")
        daily.setdefault(dt, []).append(item)
    for day, items in list(daily.items())[:5]:
        temps = [x.get("main", {}).get("temp") for x in items if x.get("main", {}).get("temp") is not None]
        descriptions = [(x.get("weather") or [{}])[0].get("description", "нет данных") for x in items]
        if temps:
            row = f"{day}: {_format_temperature(min(temps))}…{_format_temperature(max(temps))} °C, {descriptions[0]}"
        else:
            row = f"{day}: нет данных"
        lines.append(row)
    return "\n".join(lines)


def _format_air(air_data: dict[str, Any]) -> str:
    items = air_data.get("list") or []
    if not items:
        return "Качество воздуха: н/д"
    aqi = items[0].get("main", {}).get("aqi")
    labels = {1: "Хорошо", 2: "Приемлемо", 3: "Умеренно", 4: "Плохо", 5: "Очень плохо"}
    return f"Качество воздуха (AQI): {aqi} ({labels.get(aqi, 'н/д')})"


def _localize_api_message(message: str, status_code: int) -> str:
    normalized = (message or "").strip().lower()
    mapping = {
        "city not found": "город не найден",
        "nothing to geocode": "пустой запрос",
        "invalid api key": "неверный API ключ",
        "too many requests": "слишком много запросов, попробуйте позже",
    }
    if normalized in mapping:
        return mapping[normalized]
    if status_code == 401:
        return "неверный API ключ"
    if status_code == 404:
        return "город не найден"
    if status_code == 429:
        return "слишком много запросов, попробуйте позже"
    if status_code >= 500:
        return "ошибка сервера, попробуйте позже"
    return message


class WeatherStubTool(BaseTool):
    name = "weather_stub"
    description = "Погода по городу или координатам через OpenWeather."

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Название города, например Moscow"},
                    "country_code": {"type": "string", "description": "Код страны ISO-2, например RU"},
                    "latitude": {"type": "number", "description": "Широта"},
                    "longitude": {"type": "number", "description": "Долгота"},
                    "include_forecast": {"type": "boolean", "description": "Добавить прогноз на 5 дней"},
                    "include_air_quality": {"type": "boolean", "description": "Добавить индекс качества воздуха"},
                },
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        api_key = _api_key()
        if not api_key:
            return ToolResult(ok=False, message="Не задан ключ OpenWeather (`OPENWEATHER_API_KEY`).")

        city = str(kwargs.get("city", "")).strip()
        country_code = str(kwargs.get("country_code", "")).strip() or None
        lat = kwargs.get("latitude")
        lon = kwargs.get("longitude")
        include_forecast = bool(kwargs.get("include_forecast", False))
        include_air = bool(kwargs.get("include_air_quality", False))

        if lat is None or lon is None:
            if not city:
                return ToolResult(ok=False, message="Передайте либо `city`, либо `latitude` и `longitude`.")
            coords, err = _resolve_location(city, country_code, api_key)
            if err:
                return ToolResult(ok=False, message=err)
            assert coords is not None
            latitude, longitude = coords
        else:
            latitude, longitude = float(lat), float(lon)

        current_data, err = _request_json(
            WEATHER_URL,
            {"lat": latitude, "lon": longitude, "appid": api_key, "units": "metric", "lang": "ru"},
        )
        if err:
            cached = _cache_get(latitude, longitude)
            if cached:
                body = _format_weather(cached) + "\n\n(Показаны свежие данные из локального кэша.)"
                return ToolResult(ok=True, message=body, data={"current": cached, "source": "cache"})
            return ToolResult(ok=False, message=err)
        assert current_data is not None
        _cache_put(latitude, longitude, current_data)

        parts = [_format_weather(current_data)]
        raw_data: dict[str, Any] = {"current": current_data, "source": "openweather"}

        if include_forecast:
            forecast_data, forecast_err = _request_json(
                FORECAST_URL,
                {"lat": latitude, "lon": longitude, "appid": api_key, "units": "metric", "lang": "ru"},
            )
            if forecast_data:
                parts.append(_format_forecast(forecast_data))
                raw_data["forecast"] = forecast_data
            elif forecast_err:
                parts.append(f"Прогноз недоступен: {forecast_err}")

        if include_air:
            air_data, air_err = _request_json(
                AIR_URL,
                {"lat": latitude, "lon": longitude, "appid": api_key},
            )
            if air_data:
                parts.append(_format_air(air_data))
                raw_data["air_quality"] = air_data
            elif air_err:
                parts.append(f"Качество воздуха недоступно: {air_err}")

        return ToolResult(ok=True, message="\n\n".join(parts), data=raw_data)

