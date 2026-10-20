from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from app.tools.base import BaseTool, ToolResult

_TICKER = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,14}$")
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_NEXT = "Что сделать дальше?"
_FAIL_PREFIXES = ("Курс ", "Нужен ", "Выберите ", "Для доллара")

GROUP_BY_LABEL = {
    "Валюты": "currency",
    "Криптовалюты": "crypto",
    "Акции": "stock",
    "Акции (RU)": "stock_ru",
}
_GROUP_HINT = "Выберите группу: валюты, криптовалюты, акции или акции (RU)."
_ASSET_ALIASES = {
    "currency": "currency",
    "fx": "currency",
    "валюты": "currency",
    "валюта": "currency",
    "crypto": "crypto",
    "cryptocurrency": "crypto",
    "криптовалюты": "crypto",
    "криптовалюта": "crypto",
    "stock": "stock",
    "stocks": "stock",
    "акции": "stock",
    "акция": "stock",
    "stock_ru": "stock_ru",
    "moex": "stock_ru",
    "акции (ru)": "stock_ru",
    "акция (ru)": "stock_ru",
    "акции ru": "stock_ru",
}
_PROMPTS = {
    "currency": "Тикер валютной пары, например EURUSD или USDRUB.",
    "crypto": "Тикер криптовалюты, например BTC.",
    "stock": "Тикер акции, например AAPL.",
    "stock_ru": "Тикер акции Московской биржи, например SBER или VTBR.",
}
_MOEX_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{secid}.json"
_MOEX_CURRENCY = {"SUR": "RUB", "RUB": "RUB"}
_FIAT = frozenset(
    """
    AED AFN ALL AMD ANG AOA ARS AUD AWG AZN
    BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD
    CAD CDF CHF CLP CNY COP CRC CUP CVE CZK
    DJF DKK DOP DZD
    EGP ERN ETB EUR
    FJD FKP
    GBP GEL GHS GIP GMD GNF GTQ GYD
    HKD HNL HTG HUF
    IDR ILS INR IQD IRR ISK
    JMD JOD JPY
    KES KGS KHR KMF KPW KRW KWD KYD KZT
    LAK LBP LKR LRD LSL LYD
    MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN
    NAD NGN NIO NOK NPR NZD
    OMR
    PAB PEN PGK PHP PKR PLN PYG
    QAR
    RON RSD RUB RWF
    SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD STN SVC SYP SZL
    THB TJS TMT TND TOP TRY TTD TWD TZS
    UAH UGX USD UYU UZS
    VES VND VUV
    WST
    XAF XCD XOF XPF
    YER
    ZAR ZMW ZWG
    """.split()
)


@dataclass(slots=True)
class _CryptoQuote:
    price: float
    rank: int | None


@dataclass(slots=True)
class _MarketQuote:
    price: float
    currency: str
    symbol: str


def asset_by_label(value: str) -> str | None:
    """Группа по подписи кнопки, без английских кодов вроде fx и stock."""
    folded = value.strip().casefold().replace("ё", "е")
    for label, asset in GROUP_BY_LABEL.items():
        if label.casefold() == folded:
            return asset
    return {
        "валюта": "currency",
        "криптовалюта": "crypto",
        "акция": "stock",
        "акция (ru)": "stock_ru",
        "акции ru": "stock_ru",
    }.get(folded)


def normalize_asset(value: str) -> str | None:
    """Код группы: currency, crypto или stock."""
    return _ASSET_ALIASES.get(value.strip().casefold().replace("ё", "е"))


def prompt_for(asset: str) -> str:
    return _PROMPTS.get(asset, _GROUP_HINT)


def _moex_secid(raw: str) -> str | None:
    symbol = raw.strip().upper()
    if symbol.endswith(".ME"):
        symbol = symbol[:-3]
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,11}", symbol):
        return None
    return symbol


def accepts_query(raw: str, asset: str) -> bool:
    """Подходит ли текст как тикер выбранной группы."""
    text = raw.strip()
    if asset == "currency":
        compact = text.upper().replace("/", "").replace("-", "").replace(" ", "")
        return bool(re.fullmatch(r"[A-Z]{3,6}", compact))
    if asset == "stock_ru":
        return _moex_secid(text) is not None
    return bool(_TICKER.fullmatch(text))


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


def _yahoo_quote(symbol: str) -> _MarketQuote | None:
    try:
        response = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1d"},
            headers=_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        result = (response.json().get("chart") or {}).get("result") or []
    except (requests.RequestException, ValueError):
        return None
    if not result:
        return None
    meta = result[0].get("meta") or {}
    price = meta.get("regularMarketPrice")
    if price is None:
        return None
    currency = str(meta.get("currency") or "").upper()
    shown = str(meta.get("symbol") or symbol).upper()
    return _MarketQuote(price=float(price), currency=currency, symbol=shown)


def _iss_rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    columns = table.get("columns") or []
    return [dict(zip(columns, row)) for row in table.get("data") or []]


def _moex_quote(secid: str) -> _MarketQuote | None:
    try:
        response = requests.get(
            _MOEX_URL.format(secid=secid),
            params={"iss.meta": "off", "iss.only": "marketdata,securities"},
            headers=_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return None
    market_rows = _iss_rows(payload.get("marketdata") or {})
    security_rows = _iss_rows(payload.get("securities") or {})
    if not market_rows and not security_rows:
        return None
    market = market_rows[0] if market_rows else {}
    security = security_rows[0] if security_rows else {}
    price = market.get("LAST")
    if price is None:
        price = security.get("PREVPRICE")
    if price is None:
        return None
    code = str(security.get("CURRENCYID") or "SUR").upper()
    currency = _MOEX_CURRENCY.get(code, code)
    return _MarketQuote(price=float(price), currency=currency, symbol=secid)


def _moex_text(symbol: str) -> str:
    secid = _moex_secid(symbol)
    if not secid:
        return f"Нужен тикер, например SBER или VTBR.\n{_NEXT}"
    quote = _moex_quote(secid)
    if not quote:
        return f"Курс акции {secid} не найден.\n{_NEXT}"
    currency = f" {quote.currency}" if quote.currency else ""
    return f"{secid}: {_format_price(quote.price)}{currency}\n{_NEXT}"


def _stock_quote(symbol: str) -> _MarketQuote | None:
    candidates = [symbol] if "." in symbol else [symbol, f"{symbol}.ME"]
    for candidate in candidates:
        quote = _yahoo_quote(candidate)
        if quote:
            return quote
    return None


def _fx_pair(symbol: str) -> tuple[str, str] | None:
    compact = symbol.upper().replace("/", "").replace("-", "").replace(" ", "")
    if re.fullmatch(r"[A-Z]{3}", compact):
        if compact not in _FIAT:
            return None
        if compact == "USD":
            return ("USD", "")
        return (compact, "USD")
    if re.fullmatch(r"[A-Z]{6}", compact):
        base, quote = compact[:3], compact[3:]
        if base in _FIAT and quote in _FIAT and base != quote:
            return (base, quote)
    return None


def _currency_text(symbol: str) -> str:
    pair = _fx_pair(symbol)
    if pair == ("USD", ""):
        return f"Для доллара укажите пару, например USDRUB.\n{_NEXT}"
    if not pair:
        compact = symbol.upper().replace("/", "").replace("-", "").replace(" ", "")
        if re.fullmatch(r"[A-Z]{3,6}", compact):
            return f"Курс валюты {compact} не найден.\n{_NEXT}"
        return f"Нужен тикер пары, например EURUSD или USDRUB.\n{_NEXT}"
    base, quote = pair
    market = _yahoo_quote(f"{base}{quote}=X")
    if not market:
        return f"Курс валюты {base}{quote} не найден.\n{_NEXT}"
    currency = f" {market.currency}" if market.currency else ""
    return f"{base}{quote}: {_format_price(market.price)}{currency}\n{_NEXT}"


def quote_text(raw: str, asset: str) -> str:
    """Текущий курс по тикеру внутри выбранной группы активов."""
    kind = normalize_asset(asset)
    if not kind:
        return f"{_GROUP_HINT}\n{_NEXT}"
    symbol = raw.strip().upper()
    if kind == "currency":
        return _currency_text(symbol)
    if kind == "stock_ru":
        return _moex_text(symbol)
    if not _TICKER.fullmatch(symbol):
        example = "BTC" if kind == "crypto" else "AAPL"
        return f"Нужен тикер, например {example}.\n{_NEXT}"
    if kind == "crypto":
        crypto = _crypto_quote(symbol)
        if not crypto:
            return f"Курс криптовалюты {symbol} не найден.\n{_NEXT}"
        return f"{symbol}: {_format_price(crypto.price)} USD\n{_NEXT}"
    stock = _stock_quote(symbol)
    if not stock:
        return f"Курс акции {symbol} не найден.\n{_NEXT}"
    currency = f" {stock.currency}" if stock.currency else ""
    shown = stock.symbol if stock.symbol != symbol else symbol
    return f"{shown}: {_format_price(stock.price)}{currency}\n{_NEXT}"


class QuotesTool(BaseTool):
    name = "quotes"
    description = (
        "Текущий курс по одному тикеру в выбранной группе активов: "
        "currency (валютная пара, например EURUSD), crypto (криптовалюта, например BTC), "
        "stock (акция, например AAPL) или stock_ru (акция Московской биржи, например SBER). "
        "Одинаковый тикер в разных группах — разные инструменты."
    )
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
                    "asset": {
                        "type": "string",
                        "enum": ["currency", "crypto", "stock", "stock_ru"],
                        "description": "Группа: currency — валюты, crypto — криптовалюты, stock — акции, stock_ru — акции Московской биржи",
                    },
                    "ticker": {"type": "string", "description": "Тикер внутри выбранной группы"},
                },
                "required": ["asset", "ticker"],
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        ticker = str(kwargs.get("ticker") or kwargs.get("symbol") or "")
        asset = str(kwargs.get("asset") or kwargs.get("group") or "")
        text = quote_text(ticker, asset)
        return ToolResult(ok=not text.startswith(_FAIL_PREFIXES), message=text)
