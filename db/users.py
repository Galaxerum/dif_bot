import aiosqlite
from db.db import DB_PATH
from db.models import User
from typing import Optional, List


async def add_user(user: User):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, portfolio, team_id) VALUES (?, ?, ?, ?)",
                (user.user_id, user.username, user.portfolio, user.team_id)
            )
            await db.commit()
    except Exception as e:
        print(f"Error adding user: {e}")
        # Можно логировать ошибку или обрабатывать ее более детально


async def get_user(user_id: int) -> Optional[User]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id, username, portfolio, team_id FROM users WHERE user_id = ?",
                                      (user_id,))
            row = await cursor.fetchone()
            return User(*row) if row else None
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
            return [User(*row) for row in rows]
    except Exception as e:
        print(f"Error fetching all users: {e}")
        return []  # Возвращаем пустой список при ошибке
