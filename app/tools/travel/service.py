from __future__ import annotations

import re

from app.tools.travel.countries import resolve_country_currencies
from app.tools.travel.rates import convert_amount, get_rate
from app.tools.travel.repository import TravelRepository

_HOME_COUNTRY = "home_country"
_HOME_CURRENCY = "home_currency"
_DEST_COUNTRY = "dest_country"
_DEST_CURRENCY = "dest_currency"
_RATE_CONFIRM = "rate_confirm"
_RATE_MANUAL = "rate_manual"
_INITIAL = "initial_amount"
_RATE_CHANGE = "rate_change"
_EXPENSE_CONFIRM = "expense_confirm"
_EXPENSE_COMMENT = "expense_comment"
_FINISH = "finish_confirm"

_NEW = re.compile(r"^(?:новая поездка|новое путешествие|создать путешествие)$", re.IGNORECASE)
_BALANCE = re.compile(r"^баланс$", re.IGNORECASE)
_HISTORY = re.compile(r"^история$", re.IGNORECASE)
_TRIPS = re.compile(r"^(?:поездки|мои путешествия)$", re.IGNORECASE)
_SWITCH = re.compile(r"^(?:поездка|переключить)\s+(\d+)$", re.IGNORECASE)
_SET_RATE = re.compile(r"^(?:изменить курс|курс)$", re.IGNORECASE)
_SET_RATE_VALUE = re.compile(r"^курс\s+(\d+(?:[.,]\d+)?)$", re.IGNORECASE)
_FINISH_CMD = re.compile(r"^(?:завершить|завершить поездку|завершить путешествие)$", re.IGNORECASE)
_EXPENSE = re.compile(r"^(?:расход|трата)\s+(\d+(?:[.,]\d+)?)(?:\s+(.{1,50}))?$", re.IGNORECASE)
_YES = {"да", "ок", "yes", "+"}
_NO = {"нет", "no", "-"}


def format_amount(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", " ")


def parse_amount(text: str) -> float | None:
    cleaned = text.strip().replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        return None
    value = float(cleaned)
    if value <= 0:
        return None
    return value


class TravelService:
    """Планирование поездки и учёт расходов."""

    def __init__(self, repo: TravelRepository) -> None:
        self.repo = repo

    def cancel(self, user_id: str) -> None:
        self.repo.set_state(user_id, None)

    def menu_text(self, user_id: str) -> str:
        self.repo.ensure_user(user_id)
        trip = self.repo.get_active(user_id)
        if not trip:
            return (
                "Путешествие\n"
                "Нет активной поездки.\n"
                "Создать: новая поездка"
            )
        return (
            f"{trip['name']}: {trip['home_currency']} → {trip['dest_currency']}\n"
            f"Курс: 1 {trip['home_currency']} = {format_amount(float(trip['rate']))} {trip['dest_currency']}\n"
            f"Остаток: {format_amount(float(trip['balance_dest']))} {trip['dest_currency']} = "
            f"{format_amount(float(trip['balance_home']))} {trip['home_currency']}\n"
            "Расход в валюте поездки: 1200 такси\n"
            "Ещё: баланс, история, курс, завершить"
        )

    def answer(self, user_id: str, text: str) -> str | None:
        raw = " ".join((text or "").split())
        if not raw:
            return None
        if raw.casefold() in {"отмена", "назад"}:
            state, _data = self.repo.get_state(user_id)
            if state:
                self.cancel(user_id)
                return "Ок."
            return None
        self.repo.ensure_user(user_id)
        state, data = self.repo.get_state(user_id)
        if state:
            return self._continue(user_id, state, data, raw)
        return self._command(user_id, raw)

    def _command(self, user_id: str, text: str) -> str | None:
        if _NEW.fullmatch(text):
            self.repo.set_state(user_id, _HOME_COUNTRY, {})
            return "Страна отправления:"
        if _BALANCE.fullmatch(text):
            return self._balance(user_id)
        if _HISTORY.fullmatch(text):
            return self._history(user_id)
        if _TRIPS.fullmatch(text):
            return self._trip_list(user_id)
        if match := _SWITCH.fullmatch(text):
            return self._switch(user_id, int(match.group(1)))
        if match := _SET_RATE_VALUE.fullmatch(text):
            return self._apply_rate(user_id, parse_amount(match.group(1)))
        if _SET_RATE.fullmatch(text):
            trip = self.repo.get_active(user_id)
            if not trip:
                return "Нет активной поездки. Создать: новая поездка"
            self.repo.set_state(
                user_id,
                _RATE_CHANGE,
                {
                    "trip_id": trip["id"],
                    "home_currency": trip["home_currency"],
                    "dest_currency": trip["dest_currency"],
                },
            )
            return f"Сколько {trip['dest_currency']} за 1 {trip['home_currency']}?"
        if _FINISH_CMD.fullmatch(text):
            trip = self.repo.get_active(user_id)
            if not trip:
                return "Нет активной поездки."
            self.repo.set_state(user_id, _FINISH, {"trip_id": trip["id"]})
            return f"Завершить «{trip['name']}»? да/нет"
        if match := _EXPENSE.fullmatch(text):
            amount = parse_amount(match.group(1))
            if amount is None:
                return "Введите сумму, например 1200."
            comment = (match.group(2) or "").strip()
            return self._store_expense(user_id, amount, comment or None)
        amount = parse_amount(text)
        if amount is not None and self.repo.get_active(user_id):
            return self._ask_expense(user_id, amount)
        return None

    def _continue(self, user_id: str, state: str, data: dict, text: str) -> str:
        if state == _HOME_COUNTRY:
            return self._take_country(user_id, data, text, home=True)
        if state == _DEST_COUNTRY:
            return self._take_country(user_id, data, text, home=False)
        if state in {_HOME_CURRENCY, _DEST_CURRENCY}:
            return self._take_currency(user_id, data, text, home=state == _HOME_CURRENCY)
        if state == _RATE_CONFIRM:
            return self._confirm_rate(user_id, data, text)
        if state == _RATE_MANUAL:
            rate = parse_amount(text)
            if rate is None:
                return "Введите курс числом, например 92.5."
            data["rate"] = rate
            data["rate_source"] = "manual"
            self.repo.set_state(user_id, _INITIAL, data)
            return f"Начальная сумма в {data['home_currency']}:"
        if state == _INITIAL:
            return self._take_initial(user_id, data, text)
        if state == _RATE_CHANGE:
            return self._apply_rate(user_id, parse_amount(text), clear_state=True)
        if state == _EXPENSE_CONFIRM:
            return self._confirm_expense(user_id, data, text)
        if state == _EXPENSE_COMMENT:
            return self._take_comment(user_id, data, text)
        if state == _FINISH:
            answer = text.casefold()
            self.repo.set_state(user_id, None)
            if answer not in _YES:
                return "Не завершаю."
            trip = self.repo.get_active(user_id)
            if not trip or trip["id"] != int(data.get("trip_id") or 0):
                return "Нет активной поездки."
            self.repo.finish(user_id, int(trip["id"]))
            return f"Поездка «{trip['name']}» завершена."
        self.repo.set_state(user_id, None)
        return "Ок."

    def _take_country(self, user_id: str, data: dict, text: str, *, home: bool) -> str:
        label = "home" if home else "dest"
        data[f"{label}_country"] = text.strip()
        currencies = resolve_country_currencies(text)
        data[f"{label}_currencies"] = currencies
        if len(currencies) == 1:
            data[f"{label}_currency"] = currencies[0]
            if home:
                self.repo.set_state(user_id, _DEST_COUNTRY, data)
                return f"Валюта: {currencies[0]}.\nСтрана назначения:"
            return self._offer_rate(user_id, data)
        self.repo.set_state(user_id, _HOME_CURRENCY if home else _DEST_CURRENCY, data)
        if currencies:
            return f"Валюты: {', '.join(currencies)}. Введите код."
        return "Введите код валюты из 3 букв, например USD."

    def _take_currency(self, user_id: str, data: dict, text: str, *, home: bool) -> str:
        code = text.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", code):
            return "Нужен код из 3 букв, например EUR."
        data["home_currency" if home else "dest_currency"] = code
        if "home_currency" in data and "dest_currency" in data:
            return self._offer_rate(user_id, data)
        next_state = _DEST_CURRENCY if home else _HOME_CURRENCY
        self.repo.set_state(user_id, next_state, data)
        return "Код второй валюты:"

    def _offer_rate(self, user_id: str, data: dict) -> str:
        try:
            rate = get_rate(data["home_currency"], data["dest_currency"])
        except Exception:
            self.repo.set_state(user_id, _RATE_MANUAL, data)
            return (
                f"Курс не получен. Сколько {data['dest_currency']} "
                f"за 1 {data['home_currency']}?"
            )
        data["rate"] = rate
        data["rate_source"] = "api"
        self.repo.set_state(user_id, _RATE_CONFIRM, data)
        return (
            f"1 {data['home_currency']} = {format_amount(rate)} {data['dest_currency']}.\n"
            "Подходит? да/нет"
        )

    def _confirm_rate(self, user_id: str, data: dict, text: str) -> str:
        answer = text.casefold()
        if answer in _YES:
            data["rate_source"] = "api"
            self.repo.set_state(user_id, _INITIAL, data)
            return f"Начальная сумма в {data['home_currency']}:"
        if answer in _NO:
            self.repo.set_state(user_id, _RATE_MANUAL, data)
            return f"Свой курс: сколько {data['dest_currency']} за 1 {data['home_currency']}?"
        return "Ответьте да или нет."

    def _take_initial(self, user_id: str, data: dict, text: str) -> str:
        amount = parse_amount(text)
        if amount is None:
            return "Введите сумму, например 50000."
        rate = float(data["rate"])
        if data.get("rate_source") == "api":
            try:
                balance_dest = convert_amount(amount, data["home_currency"], data["dest_currency"])
            except Exception:
                balance_dest = amount * rate
        else:
            balance_dest = amount * rate
        self.repo.create_trip(
            user_id,
            {
                "name": data.get("dest_country") or "Поездка",
                "home_country": data.get("home_country", ""),
                "dest_country": data.get("dest_country", ""),
                "home_currency": data["home_currency"],
                "dest_currency": data["dest_currency"],
                "rate": rate,
                "rate_source": data.get("rate_source", "api"),
                "balance_home": amount,
                "balance_dest": balance_dest,
            },
        )
        self.repo.set_state(user_id, None)
        return self.menu_text(user_id)

    def _apply_rate(self, user_id: str, rate: float | None, *, clear_state: bool = False) -> str:
        trip = self.repo.get_active(user_id)
        if not trip:
            self.repo.set_state(user_id, None)
            return "Нет активной поездки."
        if rate is None:
            return "Введите курс числом, например 92.5."
        self.repo.update_rate(int(trip["id"]), rate, "manual")
        if clear_state:
            self.repo.set_state(user_id, None)
        return f"Курс: 1 {trip['home_currency']} = {format_amount(rate)} {trip['dest_currency']}."

    def _ask_expense(self, user_id: str, amount_dest: float) -> str:
        trip = self.repo.get_active(user_id)
        if not trip:
            return "Нет активной поездки. Создать: новая поездка"
        rate = float(trip["rate"]) or 1.0
        amount_home = amount_dest / rate
        self.repo.set_state(
            user_id,
            _EXPENSE_CONFIRM,
            {"amount_dest": amount_dest, "amount_home": amount_home},
        )
        return (
            f"{format_amount(amount_dest)} {trip['dest_currency']} = "
            f"{format_amount(amount_home)} {trip['home_currency']}\n"
            "Учесть расход? да/нет"
        )

    def _confirm_expense(self, user_id: str, data: dict, text: str) -> str:
        answer = text.casefold()
        if answer in _NO:
            self.repo.set_state(user_id, None)
            return "Не учитываю."
        if answer not in _YES:
            return "Ответьте да или нет."
        self.repo.set_state(user_id, _EXPENSE_COMMENT, data)
        return "Комментарий до 50 символов или «-»."

    def _take_comment(self, user_id: str, data: dict, text: str) -> str:
        comment = "" if text.strip() == "-" else text.strip()
        if len(comment) > 50:
            return "Комментарий длиннее 50 символов."
        return self._store_expense(
            user_id,
            float(data["amount_dest"]),
            comment or None,
            amount_home=float(data["amount_home"]),
        )

    def _store_expense(
        self,
        user_id: str,
        amount_dest: float,
        comment: str | None,
        amount_home: float | None = None,
    ) -> str:
        trip = self.repo.get_active(user_id)
        if not trip:
            self.repo.set_state(user_id, None)
            return "Нет активной поездки."
        rate = float(trip["rate"]) or 1.0
        home = amount_dest / rate if amount_home is None else amount_home
        balance_dest = float(trip["balance_dest"]) - amount_dest
        balance_home = float(trip["balance_home"]) - home
        self.repo.update_balance(int(trip["id"]), balance_home, balance_dest)
        self.repo.add_expense(int(trip["id"]), amount_dest, home, comment)
        self.repo.set_state(user_id, None)
        note = f" ({comment})" if comment else ""
        return (
            f"Расход {format_amount(amount_dest)} {trip['dest_currency']}{note}.\n"
            f"Остаток: {format_amount(balance_dest)} {trip['dest_currency']} = "
            f"{format_amount(balance_home)} {trip['home_currency']}"
        )

    def _balance(self, user_id: str) -> str:
        trip = self.repo.get_active(user_id)
        if not trip:
            return "Нет активной поездки."
        return (
            f"Остаток: {format_amount(float(trip['balance_dest']))} {trip['dest_currency']} = "
            f"{format_amount(float(trip['balance_home']))} {trip['home_currency']}"
        )

    def _history(self, user_id: str) -> str:
        trip = self.repo.get_active(user_id)
        if not trip:
            return "Нет активной поездки."
        rows = self.repo.list_expenses(int(trip["id"]))
        if not rows:
            return "Расходов пока нет."
        lines = [f"История «{trip['name']}»:" ]
        total_dest = 0.0
        total_home = 0.0
        for item in rows:
            total_dest += float(item["amount_dest"])
            total_home += float(item["amount_home"])
            comment = (item.get("comment") or "").strip()
            suffix = f" — {comment}" if comment else ""
            lines.append(
                f"- {format_amount(float(item['amount_dest']))} {trip['dest_currency']} = "
                f"{format_amount(float(item['amount_home']))} {trip['home_currency']}{suffix}"
            )
        lines.append(
            f"Итого: {format_amount(total_dest)} {trip['dest_currency']} = "
            f"{format_amount(total_home)} {trip['home_currency']}"
        )
        return "\n".join(lines)

    def _trip_list(self, user_id: str) -> str:
        trips = self.repo.list_active(user_id)
        if not trips:
            return "Активных поездок нет. Создать: новая поездка"
        lines = ["Поездки:"]
        for index, trip in enumerate(trips, start=1):
            lines.append(f"{index}. {trip['name']} ({trip['home_currency']}→{trip['dest_currency']})")
        lines.append("Переключить: поездка 1")
        return "\n".join(lines)

    def _switch(self, user_id: str, index: int) -> str:
        trips = self.repo.list_active(user_id)
        if not 1 <= index <= len(trips):
            return "Нет поездки с таким номером."
        trip = trips[index - 1]
        self.repo.set_active(user_id, int(trip["id"]))
        return f"Активна: {trip['name']} ({trip['home_currency']}→{trip['dest_currency']})."
