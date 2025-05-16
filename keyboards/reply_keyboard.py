from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Создать профиль")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Основная клавиатура пользователя
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Показать профиль")],
        [KeyboardButton("👥 Моя команда")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Клавиатура для действий с портфолио
portfolio_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✏️ Редактировать профиль")],
        [KeyboardButton(text="❌ Удалить профиль")],
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

# Клавиатура для выбора, что редактировать
edit_options_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Изменить ФИО")],
        [KeyboardButton(text="📄 Изменить профиль")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
