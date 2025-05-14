from aiogram import types
from aiogram.types import ParseMode
from db.users import get_user
from db.teams import get_team_by_user_id
from aiogram import Dispatcher


async def team_handler(message: types.Message):
    user_id = message.from_user.id

    # Получаем пользователя из базы данных
    user = await get_user(user_id)
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")
        return

    # Получаем команду пользователя
    team = await get_team_by_user_id(user.team_id)
    if not team:
        await message.answer("Вы еще не состоите в команде.")
        return

    # Формируем сообщение с данными о команде
    team_info = f"Вы в команде: {team.name}\n" + "\n".join([f"{member.username}" for member in team.members])

    # Отправляем информацию о команде
    await message.answer(team_info, parse_mode=ParseMode.MARKDOWN)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(team_handler, commands=["team"])
