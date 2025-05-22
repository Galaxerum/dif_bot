from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import BoundFilter
from app.config import bot
from db.admin import get_admin_user_ids
from db.admin import get_relevant_users_with_tags
from db.users import get_relevant_users_without_tags, activate_all_users, deactivate_all_users
from db.tags import add_tags
from aiogram.utils.markdown import escape_md
from services.gemini_api import generate_text
import secrets
import asyncio
import json
from pathlib import Path
import os
from dotenv import load_dotenv
from app.loger_setup import get_logger


logger = get_logger(__name__, level="INFO")


load_dotenv()
SPECIAL_ADMIN_CODE = os.getenv("SPECIAL_ADMIN_CODE")


class IsAdminFilter(BoundFilter):
    key = 'is_admin'

    def __init__(self, is_admin):
        self.is_admin = is_admin

    async def check(self, message: types.Message):
        admin_ids = await get_admin_user_ids()
        return message.from_user.id in admin_ids


def register_filters(dp: Dispatcher):
    dp.filters_factory.bind(IsAdminFilter)


async def activate_all(message: types.Message):
    if message.from_user.id not in await get_admin_user_ids():
        return
    await activate_all_users()

    await message.answer("✅ Все пользователи активированы (relevance = 1)")


async def deactivate_all(message: types.Message):
    if message.from_user.id not in await get_admin_user_ids():
        return

    await deactivate_all_users()

    await message.answer("✅ Все пользователи деактивированы (relevance = 0)")


def load_known_tags():
    if not os.path.exists("known_tags.json"):
        return []
    with open("known_tags.json", "r", encoding="utf-8") as f:
        return json.load(f)


def save_known_tags(tags: list[str]):
    with open("known_tags.json", "w", encoding="utf-8") as f:
        json.dump(sorted(set(tags)), f, ensure_ascii=False, indent=2)


def update_known_tags(new_tags: list[str]):
    known = set(load_known_tags())
    updated = known.union(new_tags)
    save_known_tags(list(updated))


def load_prompt(key: str, path="prompts.json") -> str:
    with open(path, "r", encoding="utf-8") as f:
        prompts = json.load(f)
    return prompts[key]

async def generate_admin_link(message: types.Message):
    user_id = message.from_user.id
    if not user_id in await get_admin_user_ids():
        return

    # Формируем ссылку с SPECIAL_ADMIN_CODE
    bot_username = (await message.bot.get_me()).username
    admin_link = f"https://t.me/{bot_username}?start={SPECIAL_ADMIN_CODE}"

    await message.answer(
        f"🔗 Постоянная ссылка для назначения админа:\n\n"
        f"`{escape_md(admin_link)}`\n\n",
        parse_mode="MarkdownV2"
    )
async def handle_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not user_id in await get_admin_user_ids():
        return

    relevant_users = await get_relevant_users_with_tags()
    count = len(relevant_users)
    await state.update_data(prev_relevant_count=count)

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_relevant_users")
    )
    await message.answer(
        f"✅ Актуальных участников: <b>{count}</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Callback-хэндлер для обновления
async def refresh_relevant_users(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if not user_id in await get_admin_user_ids():
        return await call.answer()

    data = await state.get_data()
    prev_count = data.get("prev_relevant_count", 0)
    current_users = await get_relevant_users_with_tags()
    current_count = len(current_users)

    if current_count != prev_count:
        await call.message.edit_text(
            f"✅ Актуальных участников: <b>{current_count}</b>",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔄 Обновить", callback_data="refresh_relevant_users")
            ),
            parse_mode="HTML"
        )
        await state.update_data(prev_relevant_count=current_count)
        await call.answer("🔁 Обновлено")
    else:
        await call.answer("ℹ️ Изменений нет")


async def generate_link(message: types.Message):
    user_id = message.from_user.id
    if not user_id in await get_admin_user_ids():
        return

    token = secrets.token_urlsafe(16)

    tokens_file = Path("tokens.json")

    if not tokens_file.exists():
        with open(tokens_file, "w") as f:
            json.dump({"activation_token": None}, f)

    with open(tokens_file, "r") as f:
        tokens_data = json.load(f)

    tokens_data["activation_token"] = token

    with open(tokens_file, "w") as f:
        json.dump(tokens_data, f, indent=4)

    bot_username = (await message.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=activate_{token}"

    await message.answer(
        f"🔗 Новая ссылка для активации:\n\n`{escape_md(link)}`",
        parse_mode="MarkdownV2"
    )


async def _process_portfolio_with_ai(portfolio_text: str) -> tuple[list[str], bool]:
    try:
        with open("prompts.json", "r", encoding="utf-8") as f:
            prompts = json.load(f)

        known_tags = load_known_tags()
        known_tags_str = ", ".join(known_tags)
        prompt = f"{prompts['generate_tags']}Известные теги: {known_tags_str}\n\nВот портфолио:\n{portfolio_text}"

        response_text = await generate_text(prompt)
        parsed = json.loads(response_text)

        tags = parsed.get("tags", [])
        is_meaningful = parsed.get("mean", ["False"])[0] == "True"

        return tags, is_meaningful

    except Exception as e:
        logger.error(f"JSON parsing error: {e}")
        return [], False

async def show_typing(chat_id):
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(3)


async def process_users_without_tags(message: types.Message):
    typing_task = asyncio.create_task(show_typing(message.chat.id))

    try:
        users = await get_relevant_users_without_tags()

        if not users:
            await message.answer("🔍 Нет пользователей без тегов для обработки")
            return

        status_msg = await message.answer(f"🔧 Начинаю обработку {len(users)} пользователей...")

        processed = 0
        for user in users:
            user_id = user[1]
            portfolio_text = user[3]

            if not portfolio_text:
                await status_msg.edit_text(f"{status_msg.text}\n⏭ Пропускаю {user_id} - нет портфолио")
                continue

            await status_msg.edit_text(f"{status_msg.text}\n🔄 Обрабатываю пользователя {user_id}...")
            tags, is_meaningful = await _process_portfolio_with_ai(portfolio_text)

            if not is_meaningful or not tags:
                await status_msg.edit_text(f"{status_msg.text}\n❌ Портфолио {user_id} не содержит полезной информации")
                continue

            await add_tags(user_id, tags)
            update_known_tags(tags)
            await status_msg.edit_text(f"{status_msg.text}\n✅ Добавлены теги для {user_id}: {', '.join(tags)}")
            processed += 1
            await asyncio.sleep(1)

        await status_msg.edit_text(f"{status_msg.text}\n🎉 Обработка завершена! Обработано: {processed}/{len(users)}")

    except Exception as e:
        logger.error(f"⚠️ Ошибка: {str(e)}")
    finally:
        typing_task.cancel()

async def show_admin_commands(message: types.Message):
    user_id = message.from_user.id
    if not user_id in await get_admin_user_ids():
        return

    commands = [
        ("/get_users", "Показать количество актуальных участников"),
        ("/get_participant", "Сгенерировать ссылку для участия"),
        ("/admin_help", "Показать список команд для админов"),
        ("/get_admin_link", "Сгенерировать ссылку для назначения админа"),
        ("/generate_tags", "Сгенерировать теги для участников без тегов"),
        ("/generate_teams", "Сгенерировать команды"),
        ("/clear_teams", "Удаление и очистка состава команд"),
        ("/activate_all", "Активирует всех пользователей (relevance = 1)"),
        ("/deactivate_all", "Деактивирует всех пользователей (relevance = 0)"),
        ("/notify_empty_portfolio", "разослать сообщение о необходимости заполнить портфолио")
    ]

    response = "📝 <b>Доступные команды для админов:</b>\n\n"
    response += "\n".join([f"• {cmd} - {desc}" for cmd, desc in commands])

    await message.answer(response, parse_mode="HTML")


def register_handlers(dp: Dispatcher):
    register_filters(dp)
    dp.register_message_handler(handle_admin, commands=["get_users"], state="*", is_admin=True)
    dp.register_message_handler(generate_link, commands=["get_participant"], is_admin=True)
    dp.register_message_handler(generate_admin_link, commands=["get_admin_link"], is_admin=True)
    dp.register_message_handler(show_admin_commands, commands=["admin_help"], is_admin=True)
    dp.register_message_handler(process_users_without_tags, commands=["generate_tags"], is_admin=True)
    dp.register_callback_query_handler(refresh_relevant_users, text="refresh_relevant_users", state="*")
    dp.register_message_handler(activate_all, commands=["activate_all"], is_admin=True)
    dp.register_message_handler(deactivate_all, commands=["deactivate_all"], is_admin=True)
