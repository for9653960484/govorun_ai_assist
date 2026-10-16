from __future__ import annotations

import re

import pycountry
from babel import Locale
from babel.numbers import get_territory_currencies

_TERRITORIES: dict[str, str] | None = None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().replace("ё", "е"))


def _territories() -> dict[str, str]:
    global _TERRITORIES
    if _TERRITORIES is None:
        mapping: dict[str, str] = {}
        for locale_code in ("ru", "en"):
            locale = Locale(locale_code)
            for code, name in locale.territories.items():
                mapping[_normalize(str(name))] = code
        _TERRITORIES = mapping
    return _TERRITORIES


def resolve_country_code(country_name: str) -> str | None:
    try:
        return pycountry.countries.lookup(country_name).alpha_2
    except LookupError:
        pass
    return _territories().get(_normalize(country_name))


def resolve_country_currencies(country_name: str) -> list[str]:
    territory = resolve_country_code(country_name)
    if not territory:
        return []
    try:
        currencies = get_territory_currencies(territory, tender=True)
    except Exception:
        return []
    return sorted(set(currencies))
