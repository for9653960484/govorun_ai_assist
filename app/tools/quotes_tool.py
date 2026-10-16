from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from app.tools.base import BaseTool, ToolResult

_TICKER = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,14}$")
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_NEXT = "Что сделать дальше?"


@dataclass(slots=True)
class _CryptoQuote:
    price: float
    rank: int | None


@dataclass(slots=True)
class _StockQuote:
    price: float
    currency: str
    symbol: str


def _format_price(value: float) -> str:
    if value >= 1:
        return f"{value:.2f}"
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _crypto_quote(symbol: str) -> _CryptoQuote | None:
    try:
        found = requests.get(
            "https://api.coingecko.com/api/v3/search",
            params={"query": symbol},
            headers=_HEADERS,
            timeout=10,
        )
        found.raise_for_status()
        coins = found.json().get("coins") or []
    except (requests.RequestException, ValueError):
        return None
    matches = [coin for coin in coins if str(coin.get("symbol", "")).upper() == symbol and coin.get("id")]
    if not matches:
        return None
    matches.sort(key=lambda coin: coin.get("market_cap_rank") or 10**9)
    coin = matches[0]
    coin_id = str(coin["id"])
    rank = coin.get("market_cap_rank")
    try:
        priced = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd"},
            headers=_HEADERS,
            timeout=10,
        )
        priced.raise_for_status()
        value = priced.json().get(coin_id, {}).get("usd")
    except (requests.RequestException, ValueError):
        return None
    if value is None:
        return None
    return _CryptoQuote(price=float(value), rank=int(rank) if isinstance(rank, int) else None)


def _stock_quote(symbol: str) -> _StockQuote | None:
    candidates = [symbol] if "." in symbol else [symbol, f"{symbol}.ME"]
    for candidate in candidates:
        try:
            response = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{candidate}",
                params={"interval": "1d", "range": "1d"},
                headers=_HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            result = (response.json().get("chart") or {}).get("result") or []
        except (requests.RequestException, ValueError):
            continue
        if not result:
            continue
        meta = result[0].get("meta") or {}
        price = meta.get("regularMarketPrice")
        if price is None:
            continue
        currency = str(meta.get("currency") or "").upper()
        return _StockQuote(price=float(price), currency=currency, symbol=candidate.upper())
    return None


def quote_text(raw: str) -> str:
    """Текущий курс по тикеру и вопрос о следующем действии."""
    symbol = raw.strip().upper()
    if not _TICKER.fullmatch(symbol):
        return f"Нужен тикер, например BTC или AAPL.\n{_NEXT}"
    crypto = _crypto_quote(symbol)
    if crypto and crypto.rank is not None and crypto.rank <= 100:
        return f"{symbol}: {_format_price(crypto.price)} USD\n{_NEXT}"
    stock = _stock_quote(symbol)
    if stock:
        currency = f" {stock.currency}" if stock.currency else ""
        shown = stock.symbol if stock.symbol != symbol else symbol
        return f"{shown}: {_format_price(stock.price)}{currency}\n{_NEXT}"
    if crypto:
        return f"{symbol}: {_format_price(crypto.price)} USD\n{_NEXT}"
    return f"Курс {symbol} не найден.\n{_NEXT}"


class QuotesTool(BaseTool):
    name = "quotes"
    description = "Текущий курс акции, валюты или криптовалюты по одному тикеру."
    menu_title = "Котировки"
    menu_hint = ""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Тикер, например BTC или AAPL"},
                },
                "required": ["ticker"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        ticker = str(kwargs.get("ticker") or kwargs.get("symbol") or "")
        text = quote_text(ticker)
        return ToolResult(ok=not text.startswith("Курс ") and not text.startswith("Нужен тикер"), message=text)
