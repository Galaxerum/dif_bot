from aiogram import types
from aiogram.types import ParseMode
from db.users import add_user
from aiogram import Dispatcher


async def start_handler(message: types.Message):
    user_id = message.from_user.id
    await add_user(user_id)
    greeting = (f"Привет, {message.from_user.first_name}!\nЯ бот, который поможет тебе составить команду по твоим "
                f"навыкам. Просто отправь мне свое портфолио.")

    await message.answer(greeting)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
