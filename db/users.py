import aiosqlite
from db.db import DB_PATH
from db.models import User
from typing import Optional, List


async def update_user_username(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        await db.commit()


async def add_user(user: User):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Преобразуем объект User в словарь
            user_data = user.dict()

            # Теперь можно передавать данные из словаря
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, portfolio, team_id) VALUES (?, ?, ?, ?)",
                (user_data['user_id'], user_data['username'], user_data['portfolio'], user_data['team_id'])
            )
            await db.commit()
    except Exception as e:
        print(f"Error adding user: {e}")


async def get_user(user_id: int) -> Optional[User]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id, username, portfolio, team_id FROM users WHERE user_id = ?",
                                      (user_id,))
            row = await cursor.fetchone()
            return User(**dict(zip([column[0] for column in cursor.description], row))) if row else None
    except Exception as e:
        print(f"Error getting user {user_id}: {e}")
        return None


async def delete_user_portfolio(user_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET portfolio = '' WHERE user_id = ?", (user_id,))
            await db.commit()
    except Exception as e:
        print(f"Error deleting portfolio for user {user_id}: {e}")


async def get_user_portfolio(user_id: int) -> Optional[User]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT portfolio FROM users WHERE user_id = ?",
                                      (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"Error getting user {user_id}: {e}")
        return None


async def update_user_team(user_id: int, team_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET team_id = ? WHERE user_id = ?", (team_id, user_id))
            await db.commit()
    except Exception as e:
        print(f"Error updating user team {user_id}: {e}")


async def get_all_users() -> List[User]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id, username, portfolio, team_id FROM users")
            rows = await cursor.fetchall()
            return [User(**dict(zip([column[0] for column in cursor.description], row))) for row in rows]
    except Exception as e:
        print(f"Error fetching all users: {e}")
        return []


async def update_user_portfolio(user_id: int, portfolio: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET portfolio = ? WHERE user_id = ?", (portfolio, user_id))
            await db.commit()
    except Exception as e:
        print(f"Error updating user portfolio {user_id}: {e}")


async def set_relevance_true_by_user_id(user_id: int):
    async with aiosqlite.connect("main.db") as db:
        await db.execute(
            "UPDATE users SET relevance = 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()

async def activate_all_users():
    async with aiosqlite.connect("main.db") as db:
        await db.execute("UPDATE users SET relevance = 1")
        await db.commit()

async def deactivate_all_users():
    async with aiosqlite.connect("main.db") as db:
        await db.execute("UPDATE users SET relevance = 0")
        await db.commit()


async def get_relevant_users_without_tags():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT u.id, u.user_id, u.username, u.portfolio, u.team_id 
            FROM users u
            LEFT JOIN tags t ON u.user_id = t.user_id
            WHERE t.user_id IS NULL OR json_array_length(t.tag) = 0
        """)
        return await cursor.fetchall() or []