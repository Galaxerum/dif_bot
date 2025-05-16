from aiogram import types
from aiogram.dispatcher.filters import BoundFilter
from aiogram import Dispatcher
from db.teams import TeamDistributor
from db.admin import get_admin_user_ids
from app.config import bot
import aiosqlite
import asyncio


class IsAdminFilter(BoundFilter):
    key = 'is_admin'

    def __init__(self, is_admin):
        self.is_admin = is_admin

    async def check(self, message: types.Message):
        admin_ids = await get_admin_user_ids()
        return message.from_user.id in admin_ids


def register_filters(dp: Dispatcher):
    dp.filters_factory.bind(IsAdminFilter)


async def get_user_display_info(user_id: int) -> str:
    try:
        chat = await bot.get_chat(user_id)
        if chat.username:
            return f"@{chat.username}"
        name = " ".join(filter(None, [chat.first_name, chat.last_name]))
        return name or f"ID{user_id}"
    except Exception:
        return f"ID{user_id}"


async def generate_teams(message: types.Message):
    if message.from_user.id not in await get_admin_user_ids():
        return

    try:
        with TeamDistributor() as distributor:
            distributor.setup_colors({
                "Розовые": 1,
                "Жёлтые": 0,
                "Зелёные": 0,
                "Белые": 0,
            })
            distributor.distribute_users(max_team_size=2)

        await send_team_notifications()
        await message.answer("✅ Команды успешно сформированы и уведомления разосланы!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


async def send_team_notifications():
    async with aiosqlite.connect("main.db") as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT t.id, t.colors, GROUP_CONCAT(u.user_id) as user_ids
            FROM teams t
            JOIN users u ON t.id = u.team_id
            WHERE u.relevance = 1
            GROUP BY t.id
        """)

        teams = await cursor.fetchall()
        tasks = []

        for team in teams:
            user_ids = team["user_ids"].split(",") if team["user_ids"] else []

            members_info = await asyncio.gather(
                *[get_user_display_info(int(user_id)) for user_id in user_ids],
                return_exceptions=True
            )

            members_list = "\n".join(
                f"- {info}" if not isinstance(info, Exception)
                else f"- ID{user_id}"
                for user_id, info in zip(user_ids, members_info)
            )

            message_text = (
                f"🎉 Ваша команда сформирована!\n\n"
                f"🔹 Номер: {team['id']}\n"
                f"🎨 Цвет: {team['colors']}\n\n"
                f"👥 Состав:\n{members_list}"
            )

            tasks.extend(
                bot.send_message(
                    chat_id=int(user_id),
                    text=message_text,
                    parse_mode="HTML"
                ) for user_id in user_ids
            )

        await asyncio.gather(*tasks, return_exceptions=True)


async def team_info(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect("main.db") as conn:
        conn.row_factory = aiosqlite.Row

        # Сначала находим team_id текущего пользователя
        cursor = await conn.execute("""
            SELECT team_id FROM users 
            WHERE user_id = ? AND relevance = 1
        """, (user_id,))

        user_team = await cursor.fetchone()
        if not user_team:
            await message.answer("Вы пока не в команде.")
            return

        team_id = user_team["team_id"]

        # Теперь находим ВСЕХ участников этой команды
        cursor = await conn.execute("""
            SELECT user_id FROM users 
            WHERE team_id = ? AND relevance = 1
        """, (team_id,))

        member_ids = [row["user_id"] for row in await cursor.fetchall()]

        # Получаем информацию о каждом участнике
        members_info = await asyncio.gather(
            *[get_user_display_info(member_id) for member_id in member_ids],
            return_exceptions=True
        )

        # Получаем информацию о самой команде (цвет)
        cursor = await conn.execute("""
            SELECT colors FROM teams WHERE id = ?
        """, (team_id,))
        team_info = await cursor.fetchone()
        color = team_info["colors"] if team_info else "Не указан"

        # Формируем список участников
        members_list = "\n".join(
            f"- {info}" if not isinstance(info, Exception)
            else f"- [Пользователь {member_id}]"
            for member_id, info in zip(member_ids, members_info)
        )

        await message.answer(
            f"🔹 Команда №{team_id}\n"
            f"🎨 Цвет: {color}\n\n"
            f"👥 Участники:\n{members_list}",
            parse_mode="HTML"
        )


async def clear_teams(message: types.Message):
    if message.from_user.id not in await get_admin_user_ids():
        return

    with TeamDistributor() as distributor:
        distributor.clear_all_teams()
    await message.answer("✅ Команды очищены!")


def register_handlers(dp: Dispatcher):
    register_filters(dp)

    dp.register_message_handler(
        generate_teams,
        commands=["generate_teams"],
        is_admin=True
    )
    dp.register_message_handler(
        clear_teams,
        commands=["clear_teams"],
        is_admin=True
    )
    dp.register_message_handler(
        team_info,
        text="👥 Моя команда"
    )