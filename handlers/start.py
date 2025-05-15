from aiogram import types
from aiogram.types import ParseMode
from db.users import add_user
from db.models import User
from keyboards import reply_keyboard
from aiogram import Dispatcher


async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Создаем объект User
    user = User(user_id=user_id, username=username, portfolio="", team_id=None)

    # Добавляем пользователя в базу
    await add_user(user)

    greeting = (f"Привет, {message.from_user.first_name}!\nЯ бот, который поможет тебе составить команду по твоим "
                f"навыкам. Просто отправь мне свое портфолио.")

    await message.answer(greeting, reply_markup=reply_keyboard.user_kb)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
