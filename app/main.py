import asyncio
import uvicorn
from aiogram.utils import executor
from app.config import bot, dp
from handlers.start import register_handlers as register_start_handler
from handlers.portfolio import register_handlers as register_portfolio_handler
from handlers.team import register_handlers as register_team_handler
from handlers.admin import register_handlers as register_admin_handler
from app.webhook import app
from db.db import init_db
from app.loger_setup import get_logger


logger = get_logger(__name__, level="INFO")

async def register_all_handlers():
    register_admin_handler(dp)
    register_start_handler(dp)
    register_portfolio_handler(dp)
    register_team_handler(dp)



async def on_startup(_):
    await init_db()
    logger.info("База данных подключена")


def start_polling():
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, timeout=60)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(register_all_handlers())
    # loop.run_until_complete(on_startup())
    start_polling()
    # uvicorn.run(app, host="0.0.0.0", port=8081)


if __name__ == "__main__":
    main()
