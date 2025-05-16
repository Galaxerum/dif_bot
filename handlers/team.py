from aiogram import types
from aiogram.types import ParseMode
from aiogram import Dispatcher
from db.teams import TeamDistributor
from db.admin import get_admin_user_ids
import sqlite3


async def generate_teams(message: types.Message):
    # Проверка прав администратора
    user_id = message.from_user.id
    admin_ids = await get_admin_user_ids()

    if user_id not in admin_ids:
        return

    try:
        with TeamDistributor() as distributor:
            distributor.setup_colors({
                "Розовые": 5,
                "Желтые": 18,
                "Зеленые": 1,
                "Белые": 9,
            })
            distributor.distribute_users(max_team_size=10)

        # 2. Рассылаем информацию участникам
        await send_team_notifications(message.bot)

        await message.answer("✅ Команды успешно сформированы и уведомления разосланы!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при формировании команд: {str(e)}")


async def send_team_notifications(bot):
    conn = sqlite3.connect("main.db")
    conn.row_factory = sqlite3.Row

    try:
        # Получаем все команды с участниками
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.colors, 
                   GROUP_CONCAT(u.user_id) as user_ids,
                   GROUP_CONCAT(u.username) as usernames
            FROM teams t
            JOIN users u ON t.id = u.team_id
            WHERE u.relevance = 1
            GROUP BY t.id
        """)

        for team in cursor.fetchall():
            team_id = team["id"]
            color = team["colors"]
            user_ids = team["user_ids"].split(",") if team["user_ids"] else []
            usernames = team["usernames"].split(",") if team["usernames"] else []

            members_list = "\n".join(
                [f"- @{username}" for username in usernames if username]
            )

            message_text = (
                f"🎉 Ваша команда сформирована!\n\n"
                f"🔹 Номер команды: {team_id}\n"
                f"🎨 Цвет команды: {color}\n\n"
                f"👥 Состав команды:\n{members_list}"
            )

            # Отправляем каждому участнику
            for user_id in user_ids:
                try:
                    await bot.send_message(
                        chat_id=int(user_id),
                        text=message_text,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    finally:
        conn.close()


async def team_info(message: types.Message):
    user_id = message.from_user.id

    conn = sqlite3.connect("main.db")
    conn.row_factory = sqlite3.Row

    try:
        # Получаем информацию о команде пользователя
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id as team_id, t.colors, 
                   GROUP_CONCAT(u.username) as members
            FROM users u
            JOIN teams t ON u.team_id = t.id
            WHERE u.user_id = ? AND u.relevance = 1
            GROUP BY t.id
        """, (user_id,))

        team = cursor.fetchone()
        print(team)

        if not team:
            await message.answer("Вы пока не состоите ни в одной команде.")
            return

        # Формируем сообщение
        members = team["members"].split(",") if team["members"] else []
        members_list = "\n".join([f"- @{m}" for m in members if m])

        response = (
            f"🔹 Ваша команда: №{team['team_id']}\n"
            f"🎨 Цвет: {team['colors']}\n\n"
            f"👥 Участники:\n{members_list}"
        )

        await message.answer(response, parse_mode=ParseMode.HTML)
    finally:
        conn.close()

async def clear_teams(message: types.Message):
    user_id = message.from_user.id
    admin_ids = await get_admin_user_ids()

    if user_id not in admin_ids:
        return

    with TeamDistributor() as distributor:
        distributor.clear_all_teams()
    await message.answer("✅ Команды успешно очищены!")


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(generate_teams, commands=["generate_teams"])
    dp.register_message_handler(clear_teams, commands=["clear_teams"])
    dp.register_message_handler(team_info, text="👥 Моя команда")