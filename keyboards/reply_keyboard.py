from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
        [KeyboardButton(text="📂 Показать портфолио")],
        [KeyboardButton("👥 Моя команда")]
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


team_button = KeyboardButton("👥 Моя команда")

# Создаем клавиатуру с одной кнопкой
team_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,  # Оптимизировать размер кнопки
    one_time_keyboard=True  # Скрыть клавиатуру после нажатия
).add(team_button)