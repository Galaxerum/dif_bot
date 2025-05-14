import asyncio
import uvicorn
from app.config import bot, dp
from handlers.start import register_handlers as register_start_handler
from handlers.portfolio import register_handlers as register_portfolio_handler
from handlers.team import register_handlers as register_team_handler
# from handlers.admin import register_handlers as register_admin_handler
from app.webhook import app
from db.db import init_db


async def register_all_handlers():
    register_start_handler(dp)
    register_portfolio_handler(dp)
    register_team_handler(dp)
    # register_admin_handler(dp)


async def on_startup():
    await init_db()
    print("База данных подключена")


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(register_all_handlers())
    loop.run_until_complete(on_startup())

    uvicorn.run(app, host="0.0.0.0", port=8081)


if __name__ == "__main__":
    main()
