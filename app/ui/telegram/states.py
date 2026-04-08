from aiogram.fsm.state import State, StatesGroup


class ChatStates(StatesGroup):
    """Состояния Telegram-диалога."""

    main = State()
