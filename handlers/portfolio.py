from aiogram import types
from aiogram.types import ParseMode
from db.users import get_user, update_user_team
from services.deepseek_api import generate_text
from aiogram import Dispatcher


async def portfolio_handler(message: types.Message):
    user_id = message.from_user.id
    portfolio_text = message.text.strip()

    # Получаем пользователя из базы данных
    user = await get_user(user_id)
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")
        return

    # Отправляем запрос к нейросети для разбивки портфолио на теги
    tags = await generate_text(f"Разбей следующее портфолио на теги: {portfolio_text}")

    # Сохраняем теги для пользователя
    user.portfolio = tags
    await update_user_team(user_id, tags)  # Можешь обновить команду или другие данные

    # Отправляем сообщение с результатами
    await message.answer(f"Ваши теги:\n{tags}", parse_mode=ParseMode.MARKDOWN)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(portfolio_handler, commands=["portfolio"])
