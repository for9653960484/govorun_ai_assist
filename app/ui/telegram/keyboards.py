from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура Telegram на русском."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Показать темы"), KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
    )
