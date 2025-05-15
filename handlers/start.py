from aiogram import types
from db.users import add_user, get_user_portfolio
from db.models import User
from keyboards import reply_keyboard
from aiogram import Dispatcher


async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "пользователь"

    user = User(user_id=user_id, username=username, portfolio="", team_id=None)
    await add_user(user)

    portfolio = await get_user_portfolio(user_id)

    if not portfolio or portfolio.strip() == "":
        greeting = (
            f"Привет, {first_name}!\n"
            "Вы можете создать портфолио, чтобы участвовать в мероприятиях форума.\n"
            "Для начала нажмите кнопку ниже."
        )
        await message.answer(greeting, reply_markup=reply_keyboard.start_kb)
    else:
        greeting = f"Привет, {first_name}! Что вы хотите сделать?"
        await message.answer(greeting, reply_markup=reply_keyboard.user_kb)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
