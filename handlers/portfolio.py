from aiogram import types
from aiogram.types import ParseMode
from db.users import get_user, update_user_portfolio
from services.deepseek_api import generate_text
from aiogram import Dispatcher


# Команда: /portfolio — разбивка текста на теги и сохранение в поле portfolio
async def portfolio_handler(message: types.Message):
    user_id = message.from_user.id
    portfolio_text = message.text.strip()

    user = await get_user(user_id)
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")
        return

    tags = await generate_text(f"Разбей следующее портфолио на теги, не пиши ничего лишнего разбей на 2 или 3 тега "
                               f"вот это портфолио: {portfolio_text}")

    await update_user_portfolio(user_id, tags)

    await message.answer(f"Ваши теги:\n{tags}", parse_mode=ParseMode.MARKDOWN)


# Команда: /addportfolio — сохраняет текст как есть, без разбивки
async def add_portfolio_handler(message: types.Message):
    user_id = message.from_user.id
    portfolio_text = message.text.strip()

    user = await get_user(user_id)
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")
        return

    await update_user_portfolio(user_id, portfolio_text)

    await message.answer("Ваше портфолио успешно сохранено.")


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(portfolio_handler, commands=["portfolio"])
    dp.register_message_handler(add_portfolio_handler, commands=["addportfolio"])
