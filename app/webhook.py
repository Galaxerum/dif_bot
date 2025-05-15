from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import types
from app.config import bot, dp, WEBHOOK_URL, WEBHOOK_PATH
from aiogram import Dispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    yield
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.storage.close()
    await dp.storage.wait_closed()


app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = await request.json()
    telegram_update = types.Update(**update)
    await dp.process_update(telegram_update)
