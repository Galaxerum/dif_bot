from aiogram import types
from db.users import add_user, get_user_portfolio, get_user
from db.admin import add_admin
from db.models import User
from keyboards import reply_keyboard
from aiogram import Dispatcher
from db.users import set_relevance_true_by_user_id
from dotenv import load_dotenv
import json
import os
from pathlib import Path

load_dotenv()

SPECIAL_ADMIN_CODE=os.getenv("SPECIAL_ADMIN_CODE")


async def is_valid_token(token: str) -> bool:
    if not Path("tokens.json").exists():
        return False

    with open("tokens.json", "r") as f:
        data = json.load(f)
        return data.get("activation_token") == token

async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "пользователь"
    args = message.get_args()


    if not await get_user(user_id):
        user = User(user_id=user_id, username=username, portfolio="", team_id=None)
        await add_user(user)

    portfolio = await get_user_portfolio(user_id)

    if not args:
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

    elif args == SPECIAL_ADMIN_CODE:
        await add_admin(user_id)
        await message.answer("✅ Вы были назначены админом! /admin_help для вызова списка команд")

    elif args.startswith("activate_"):
        try:
            token = args.split("_")[1]

            # Проверяем токен (в этом примере - в памяти, лучше использовать БД)
            if await is_valid_token(token):
                await set_relevance_true_by_user_id(user_id)
                await message.answer("✅ Вы успешно активированы!")
            else:
                await message.answer("❌ Неверный или устаревший код активации.")
        except IndexError:
            await message.answer("❌ Неправильный формат ссылки.")




def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
