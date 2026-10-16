from __future__ import annotations

import os

import requests

_PLACEHOLDERS = {"your_api_key", "change_me", "changeme", "placeholder"}


def _api_key() -> str:
    value = (os.getenv("EXCHANGE_API_KEY") or os.getenv("API_KEY") or "").strip()
    if not value or value.lower() in _PLACEHOLDERS:
        return ""
    return value


def _fetch_rate_no_key(from_currency: str, to_currency: str) -> float:
    response = requests.get(f"https://open.er-api.com/v6/latest/{from_currency}", timeout=15)
    response.raise_for_status()
    data = response.json()
    if data.get("result") != "success":
        raise RuntimeError(data.get("error-type") or "Курс недоступен.")
    rate = (data.get("rates") or {}).get(to_currency)
    if rate is None:
        raise RuntimeError(f"Нет курса {from_currency}->{to_currency}.")
    return float(rate)


def get_rate(from_currency: str, to_currency: str) -> float:
    if from_currency == to_currency:
        return 1.0
    key = _api_key()
    if not key:
        return _fetch_rate_no_key(from_currency, to_currency)
    try:
        response = requests.get(
            "https://api.exchangerate.host/convert",
            params={"access_key": key, "from": from_currency, "to": to_currency, "amount": 1},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success") is False:
            raise RuntimeError("Курс недоступен.")
        rate = (data.get("info") or {}).get("rate")
        if rate is None:
            raise RuntimeError("Курс недоступен.")
        return float(rate)
    except (requests.RequestException, RuntimeError, ValueError, TypeError):
        return _fetch_rate_no_key(from_currency, to_currency)


def convert_amount(amount: float, from_currency: str, to_currency: str) -> float:
    return amount * get_rate(from_currency, to_currency)
