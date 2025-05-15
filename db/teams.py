import aiosqlite
from db.db import DB_PATH
from db.models import Team, User
from typing import List, Optional


async def get_team_by_user_id(team_id: int) -> Optional[Team]:
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем команду по ID
        cursor = await db.execute("SELECT id, name FROM teams WHERE id = ?", (team_id,))
        row = await cursor.fetchone()
        if row:
            # Если команда найдена, получаем её участников
            team = Team(*row)
            # Получаем пользователей, принадлежащих к этой команде
            cursor = await db.execute("SELECT user_id, username FROM users WHERE team_id = ?", (team_id,))
            team.members = [User(user_id=row[0], username=row[1]) for row in await cursor.fetchall()]
            return team
        return None


async def create_team(name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO teams (name) VALUES (?)", (name,))
        await db.commit()
        return cursor.lastrowid


async def get_team(team_id: int) -> Optional[Team]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, name FROM teams WHERE id = ?", (team_id,))
        row = await cursor.fetchone()
        return Team(id=row[0], name=row[1]) if row else None


async def get_team_members(team_id: int) -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE team_id = ?", (team_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_all_teams() -> List[Team]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, name FROM teams")
        rows = await cursor.fetchall()
        return [Team(id=row[0], name=row[1]) for row in rows]
