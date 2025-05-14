from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Основная клавиатура пользователя
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Показать портфолио")],
        [KeyboardButton(text="✏️ Редактировать портфолио")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Клавиатура для действий с портфолио
portfolio_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✏️ Редактировать портфолио")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)