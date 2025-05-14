import aiosqlite
from db.db import DB_PATH
from typing import List


async def add_tags(user_id: int, tags: List[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        for tag in tags:
            await db.execute("INSERT INTO tags (user_id, tag) VALUES (?, ?)", (user_id, tag))
        await db.commit()


async def get_all_tags() -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT tag FROM tags")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_user_tags(user_id: int) -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT tag FROM tags WHERE user_id = ?", (user_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
