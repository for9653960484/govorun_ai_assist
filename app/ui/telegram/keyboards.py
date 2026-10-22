from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура Telegram на русском."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Показать темы"), KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
    )


def quotes_keyboard() -> ReplyKeyboardMarkup:
    """Группы активов для поиска котировки."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Валюты"), KeyboardButton(text="Криптовалюты")],
            [KeyboardButton(text="Акции"), KeyboardButton(text="Акции (RU)")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


def schedule_keyboard() -> ReplyKeyboardMarkup:
    """Кнопки личного расписания."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сегодня"), KeyboardButton(text="Неделя"), KeyboardButton(text="Месяц")],
            [KeyboardButton(text="Создать"), KeyboardButton(text="Изменить")],
            [KeyboardButton(text="Перенести"), KeyboardButton(text="Удалить")],
            [KeyboardButton(text="Напоминание"), KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


def schedule_fields_keyboard() -> ReplyKeyboardMarkup:
    """Поле события, которое нужно изменить."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Название"), KeyboardButton(text="Описание")],
            [KeyboardButton(text="Место"), KeyboardButton(text="Длительность")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
    )


def schedule_confirm_keyboard() -> ReplyKeyboardMarkup:
    """Подтверждение удаления события."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
    )


def topics_keyboard(titles: list[str]) -> ReplyKeyboardMarkup:
    """Клавиатура тем: пункты инструментов в порядке регистрации."""
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for title in titles:
        row.append(KeyboardButton(text=title))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton(text="Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
