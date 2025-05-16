import aiosqlite
from db.db import DB_PATH


async def get_admin_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM admin")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def add_admin(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admin (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()


async def get_relevant_users_with_tags():
    results = []

    async with aiosqlite.connect("main.db") as db:
        # Получаем пользователей с relevance = True
        async with db.execute("SELECT user_id, username FROM users WHERE relevance = 1") as cursor:
            users = await cursor.fetchall()

        for user_id, username in users:
            # Получаем теги для каждого пользователя
            async with db.execute("SELECT tag FROM tags WHERE user_id = ?", (user_id,)) as tag_cursor:
                tag_rows = await tag_cursor.fetchall()
                tags = [row[0] for row in tag_rows]

            results.append({
                "user_id": user_id,
                "username": username,
                "tags": tags
            })

    return results
