import aiosqlite
import asyncio
from pathlib import Path

DB_PATH = Path("main.db")  # или получай путь через config.py

TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            portfolio TEXT,
            team_id INTEGER
        );
    """,
    "tags": """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tag TEXT
        );
    """,
    "teams": """
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        for query in TABLES.values():
            await db.execute(query)
        await db.commit()
