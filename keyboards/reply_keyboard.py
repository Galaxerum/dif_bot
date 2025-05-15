from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Стартовая клавиатура (показывается при первом запуске бота)
start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Создать портфолио")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Основная клавиатура пользователя
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Показать портфолио")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Клавиатура для действий с портфолио
portfolio_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✏️ Редактировать портфолио")],
        [KeyboardButton(text="❌ Удалить портфолио")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)