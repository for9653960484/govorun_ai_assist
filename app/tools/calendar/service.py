from __future__ import annotations

import re
from datetime import date

from app.tools.calendar.repository import CalendarRepository
from app.tools.calendar.schemas import PersonBirthday
from app.tools.schedule.birthdays import publish_birthday, withdraw_birthday

_MONTH_WORDS: dict[str, int] = {
    "январь": 1,
    "января": 1,
    "январе": 1,
    "февраль": 2,
    "февраля": 2,
    "феврале": 2,
    "март": 3,
    "марта": 3,
    "марте": 3,
    "апрель": 4,
    "апреля": 4,
    "апреле": 4,
    "май": 5,
    "мая": 5,
    "мае": 5,
    "июнь": 6,
    "июня": 6,
    "июне": 6,
    "июль": 7,
    "июля": 7,
    "июле": 7,
    "август": 8,
    "августа": 8,
    "августе": 8,
    "сентябрь": 9,
    "сентября": 9,
    "сентябре": 9,
    "октябрь": 10,
    "октября": 10,
    "октябре": 10,
    "ноябрь": 11,
    "ноября": 11,
    "ноябре": 11,
    "декабрь": 12,
    "декабря": 12,
    "декабре": 12,
}
_EMPTY_MONTH = "В этом месяце дней рождения нет."
_EMPTY_YEAR = "В этом году дней рождения нет."
_ENTRY_HINT = (
    "Команды боту:\n"
    "<b>запиши</b> 12 октября Иванов Иван\n"
    "<b>выведи</b> октябрь\n"
    "<b>выведи</b> год\n"
    "<b>удали</b> Иванов"
)
_COMMAND = re.compile(
    r"^(запиш(?:и|ите)|вывед(?:и|ите)|удал(?:и|ите))\b\s*(.*)$",
    re.IGNORECASE,
)
_YEAR_QUERY = re.compile(r"^(?:за\s+)?(?:год|\d{4}(?:\s+год)?)$", re.IGNORECASE)
_MONTH_NAME = (
    "января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|"
    "январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь|"
    "январе|феврале|марте|апреле|мае|июне|июле|августе|сентябре|октябре|ноябре|декабре"
)
_DATE_NUM = re.compile(r"\b(\d{1,2})\s*[./-]\s*(\d{1,2})(?:\s*[./-]\s*(\d{2,4}))?\b")
_DATE_TEXT = re.compile(
    rf"\b(\d{{1,2}})\s*(?:-?\s*(?:го|ого))?\s+({_MONTH_NAME})(?:\s+(\d{{4}}))?\b",
    re.IGNORECASE,
)
_DATE_TEXT_REV = re.compile(
    rf"\b({_MONTH_NAME})\s+(\d{{1,2}})(?:\s+(\d{{4}}))?\b",
    re.IGNORECASE,
)
_NOISE = re.compile(
    r"\b(?:дни\s+рождения|день\s+рождения|рождения|рожденья|родился|родилась|именины|именинники|именинник|"
    r"запомни(?:ть)?|добав(?:ь|ить)|запиш(?:и|ите|ать)|календарь|покажи|список|др|"
    r"в|во|за|на|по|месяц|этом|этого|месяце)\b",
    re.IGNORECASE,
)
_NAME_TOKEN = re.compile(r"[A-Za-zА-Яа-яЁё-]{2,}")
_SURNAME_SUFFIXES = (
    "ский", "ская", "цкая", "цкий", "ова", "ева", "ина", "ына",
    "ов", "ев", "ин", "ын", "их", "ых", "ой", "ая",
)
_PATRONYMIC_SUFFIXES = ("ович", "евич", "овна", "евна", "ична", "инична")


class CalendarService:
    """Сервис календаря и именинников."""

    def __init__(self, repo: CalendarRepository) -> None:
        self.repo = repo

    def add_birthday(self, person: PersonBirthday) -> int:
        return self.repo.add_person(person)

    def list_month_birthdays(self, month: int) -> list[dict]:
        return self.repo.by_month(month)

    def search_fio(self, query: str) -> list[dict]:
        return self.repo.find_by_fio(query)

    def format_month_birthdays(self, month: int) -> str:
        """Строки «ДД.ММ - фамилия имя» по возрастанию дня."""
        return _format_rows(self.list_month_birthdays(month), _EMPTY_MONTH)

    def format_year_birthdays(self) -> str:
        """Все дни рождения за год, по возрастанию даты."""
        return _format_rows(self.repo.all_people(), _EMPTY_YEAR)

    def section_text(self) -> str:
        return self.section_hint()

    def section_hint(self) -> str:
        return _ENTRY_HINT

    def _with_google(self, text: str, person_id: int) -> str:
        row = self.repo.get_person(person_id)
        already = bool(row and str(row.get("google_event_id") or "").strip())
        error = publish_birthday(self.repo, person_id)
        if error:
            return f"{text}\n\nВ Google Календарь не отправлено: {error}"
        if already:
            return text
        return f"{text}\n\nВ Google Календаре это событие на весь день, уведомление за 1 день."

    def save_birthday(self, person: PersonBirthday) -> str:
        """Пишет день рождения в SQLite и возвращает список этого месяца."""
        person = PersonBirthday(
            _name_part(person.last_name),
            _name_part(person.first_name),
            _name_part(person.middle_name),
            person.day,
            person.month,
            person.year,
        )
        if not person.last_name or not person.first_name or not _valid_date(person.day, person.month, person.year):
            return self.section_hint()
        for row in self.repo.by_month(person.month):
            same_day = int(row["birth_day"]) == person.day
            same_last = str(row["last_name"]).casefold() == person.last_name.casefold()
            same_first = str(row["first_name"]).casefold() == person.first_name.casefold()
            if same_day and same_last and same_first:
                return self._with_google(self.format_month_birthdays(person.month), int(row["id"]))
        person_id = self.repo.add_person(person)
        return self._with_google(self.format_month_birthdays(person.month), person_id)

    def delete_by_name(self, query: str) -> str | None:
        """Удаляет одну запись по имени. None — никого не нашли."""
        found_date = _find_date(query)
        name_text = query
        if found_date is not None:
            _day, _month, _year, start, end = found_date
            name_text = f"{query[:start]} {query[end:]}"
        needle = " ".join(name_text.replace("ё", "е").split()).casefold()
        if not needle:
            return "Укажите имя: удали Иванов"
        found = [row for row in self.repo.all_people() if _row_matches(row, needle)]
        if found_date is not None:
            day, month = found_date[0], found_date[1]
            found = [
                row for row in found
                if int(row["birth_day"]) == day and int(row["birth_month"]) == month
            ]
        if not found:
            return None
        if len(found) > 1:
            names = {
                (
                    str(row.get("last_name") or "").casefold(),
                    str(row.get("first_name") or "").casefold(),
                )
                for row in found
            }
            hint = "Уточните дату." if len(names) == 1 else "Уточните имя."
            return _format_rows(found, "") + f"\n{hint}"
        row = found[0]
        event_id = str(row.get("google_event_id") or "").strip()
        error = withdraw_birthday(event_id)
        if error:
            return f"Событие в Google Календаре не удалено: {error}"
        self.repo.delete_person(int(row["id"]))
        return f"Удалено: {_format_line(row)}"

    def answer_request(self, text: str, *, capture: bool = False) -> str | None:
        """Команды запиши, выведи и удали. Иначе None."""
        raw = " ".join((text or "").split())
        if not raw:
            return None
        match = _COMMAND.match(raw)
        if match is None:
            return None
        verb = match.group(1).casefold()
        rest = match.group(2).strip()
        if verb.startswith("зап"):
            person = parse_birthday(rest)
            if person is None:
                return "Нужны дата и ФИО: запиши 12 октября Иванов Иван"
            return self.save_birthday(person)
        if verb.startswith("выв"):
            return self._show(rest)
        removed = self.delete_by_name(rest)
        if removed is None:
            if capture:
                return "Запись не найдена."
            return None
        return removed

    def _show(self, rest: str) -> str:
        folded = " ".join(rest.replace("ё", "е").split()).casefold()
        if not folded:
            return "Укажите месяц или год: выведи октябрь"
        if _YEAR_QUERY.fullmatch(folded):
            return self.format_year_birthdays()
        month = parse_month(rest)
        if month is not None and not _name_leftover(rest):
            return self.format_month_birthdays(month)
        return "Укажите месяц или год: выведи октябрь"

    def answer_month_request(self, text: str) -> str | None:
        """Ответ на запрос дней рождения за месяц, если месяц в тексте указан."""
        return self.answer_request(text, capture=False)


def parse_month(value: object) -> int | None:
    """Номер месяца из числа или русского названия."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 12 else None
    if isinstance(value, float) and value.is_integer():
        number = int(value)
        return number if 1 <= number <= 12 else None
    text = str(value or "").strip().lower().replace("ё", "е")
    if not text:
        return None
    if text.isdigit():
        number = int(text)
        return number if 1 <= number <= 12 else None
    words = re.findall(r"[0-9]+|[а-я]+", text)
    for word in words:
        month = _MONTH_WORDS.get(word)
        if month is not None:
            return month
    for word in words:
        if word.isdigit():
            number = int(word)
            if 1 <= number <= 12:
                return number
    return None


def parse_birthday(text: str) -> PersonBirthday | None:
    """Дата и ФИО из свободной фразы. Год необязателен."""
    found = _find_date(text)
    if found is None:
        return None
    day, month, year, start, end = found
    if not _valid_date(day, month, year):
        return None
    without_date = f"{text[:start]} {text[end:]}"
    cleaned = _NOISE.sub(" ", without_date)
    tokens = [token for token in _NAME_TOKEN.findall(cleaned) if token.casefold() not in _MONTH_WORDS]
    fio = _split_fio(tokens)
    if fio is None:
        return None
    last_name, first_name, middle_name = fio
    return PersonBirthday(last_name, first_name, middle_name, day, month, year)


def _find_date(text: str) -> tuple[int, int, int, int, int] | None:
    matches: list[tuple[int, int, int, int, int]] = []
    for match in _DATE_NUM.finditer(text):
        year = _normalize_year(match.group(3))
        matches.append((int(match.group(1)), int(match.group(2)), year, match.start(), match.end()))
    for match in _DATE_TEXT.finditer(text):
        month = _MONTH_WORDS.get(match.group(2).casefold())
        if month is None:
            continue
        year = _normalize_year(match.group(3))
        matches.append((int(match.group(1)), month, year, match.start(), match.end()))
    for match in _DATE_TEXT_REV.finditer(text):
        month = _MONTH_WORDS.get(match.group(1).casefold())
        if month is None:
            continue
        year = _normalize_year(match.group(3))
        matches.append((int(match.group(2)), month, year, match.start(), match.end()))
    if not matches:
        return None
    return min(matches, key=lambda item: item[3])


def _normalize_year(raw: str | None) -> int:
    if not raw:
        return 0
    year = int(raw)
    if year >= 100:
        return year if 1900 <= year <= 2100 else 0
    return 2000 + year if year <= date.today().year % 100 else 1900 + year


def _valid_date(day: int, month: int, year: int) -> bool:
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return False
    if month in {4, 6, 9, 11} and day > 30:
        return False
    if month == 2:
        leap = year == 0 or year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)
        if day > (29 if leap else 28):
            return False
    return True


def _split_fio(tokens: list[str]) -> tuple[str, str, str] | None:
    middle = ""
    core: list[str] = []
    for token in tokens:
        if not middle and _is_patronymic(token):
            middle = token
            continue
        core.append(token)
    if len(core) != 2:
        return None
    last_name, first_name = core
    if _is_surname(first_name) and not _is_surname(last_name):
        last_name, first_name = first_name, last_name
    return _name_part(last_name), _name_part(first_name), _name_part(middle)


def _is_surname(word: str) -> bool:
    folded = word.casefold().replace("ё", "е")
    return any(folded.endswith(suffix) for suffix in _SURNAME_SUFFIXES)


def _is_patronymic(word: str) -> bool:
    folded = word.casefold().replace("ё", "е")
    return any(folded.endswith(suffix) for suffix in _PATRONYMIC_SUFFIXES)


def _name_part(word: str) -> str:
    if not word:
        return ""
    parts: list[str] = []
    for piece in word.split("-"):
        if not piece:
            continue
        if piece.isupper() or piece.islower():
            parts.append(piece[:1].upper() + piece[1:].lower())
        else:
            parts.append(piece[:1].upper() + piece[1:])
    return "-".join(parts)


def _format_rows(rows: list[dict], empty: str) -> str:
    lines = [_format_line(row) for row in rows]
    lines = [line for line in lines if line]
    return "\n".join(lines) if lines else empty


def _format_line(row: dict) -> str:
    last_name = str(row.get("last_name") or "").strip()
    first_name = str(row.get("first_name") or "").strip()
    if not last_name or not first_name:
        return ""
    return f"{int(row['birth_day']):02d}.{int(row['birth_month']):02d} - {last_name} {first_name}"


def _row_matches(row: dict, needle: str) -> bool:
    last_name = str(row.get("last_name") or "").casefold().replace("ё", "е")
    first_name = str(row.get("first_name") or "").casefold().replace("ё", "е")
    middle_name = str(row.get("middle_name") or "").casefold().replace("ё", "е")
    full = " ".join(part for part in (last_name, first_name, middle_name) if part)
    swapped = " ".join(part for part in (first_name, last_name) if part)
    if needle in {last_name, first_name, middle_name, full, swapped}:
        return True
    parts = [part for part in (last_name, first_name, middle_name) if part]
    tokens = needle.split()
    return bool(tokens) and all(token in parts for token in tokens)


def _name_leftover(text: str) -> bool:
    cleaned = _NOISE.sub(" ", text)
    for word in _MONTH_WORDS:
        cleaned = re.sub(rf"\b{word}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = _DATE_NUM.sub(" ", cleaned)
    return _NAME_TOKEN.search(cleaned) is not None
