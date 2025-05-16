from typing import TextIO

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from db.users import get_user, update_user_portfolio, get_user_portfolio, delete_user_portfolio
from db.tags import add_tags, get_user_tags
from services.gemini_api import generate_text
import asyncio
from keyboards import reply_keyboard
import json
import os


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


class PortfolioProcessing(StatesGroup):
    waiting_for_portfolio = State()
    processing = State()
    confirm_tags = State()
    editing = State()


class PortfolioDelete(StatesGroup):
    waiting_for_confirmation = State()


async def show_typing(chat_id, bot):
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(3)


async def start_portfolio_processing(message: types.Message, state: FSMContext):
    await state.set_state(PortfolioProcessing.waiting_for_portfolio)
    await message.answer(
        "📝 Отправьте текст вашего портфолио.\n"
        "(Чтобы отменить, используйте /cancel)",
        reply_markup=ReplyKeyboardRemove()
    )


async def show_portfolio(message: types.Message):
    user_id = message.from_user.id
    portfolio = await get_user_portfolio(user_id)

    if not portfolio:
        await message.answer(
            "❌ У вас ещё нет сохранённого портфолио.\n"
            "Нажмите '➕ Создать портфолио' чтобы создать его.",
            reply_markup=reply_keyboard.start_kb
        )
        return

    # debug_tags = await get_user_tags(user_id)
    # print(f"Debug: User {user_id} tags: {debug_tags}")  # Логируем теги в консоль

    await message.answer(
        f"📂 Ваше портфолио:\n\n{portfolio}\n\n"
        "Что вы хотите сделать?",
        reply_markup=reply_keyboard.portfolio_kb
    )


async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "↩️ Возврат в главное меню.",
        reply_markup=reply_keyboard.user_kb
    )


async def edit_portfolio(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    portfolio = await get_user_portfolio(user_id)

    if not portfolio:
        await message.answer(
            "❌ У вас ещё нет сохранённого портфолио.\n"
            "Нажмите '➕ Создать портфолио' чтобы создать его.",
            reply_markup=reply_keyboard.start_kb
        )
        return

    await state.set_state(PortfolioProcessing.editing)
    await message.answer(
        "✏️ Отправьте новый текст портфолио для обновления.\n"
        "(Чтобы отменить, используйте /cancel)",
        reply_markup=ReplyKeyboardRemove()
    )


USE_AI = True


async def process_portfolio_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    portfolio_text = message.text.strip()
    user = await get_user(user_id)

    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")
        await state.finish()
        return

    if len(portfolio_text) >= 1024:
        await message.answer("Сообщение слишком длинное")
        return

    current_state = await state.get_state()
    typing_task = asyncio.create_task(show_typing(message.chat.id, message.bot))

    try:
        processing_msg = await message.answer("⏳ Сохраняю ваше портфолио...")

        tags = []
        is_meaningful = True

        if USE_AI:
            tags, is_meaningful = await _process_portfolio_with_ai(portfolio_text)
            if not is_meaningful or not tags:
                await message.answer(
                    "❌ Ваше портфолио не содержит достаточно сведений.\n"
                    "Пожалуйста, отправьте более подробный и содержательный текст."
                )
                return

            update_known_tags(tags)
            await add_tags(user_id, tags)
            print(f"Tags for user {user_id}: {tags}")

        await update_user_portfolio(user_id, portfolio_text)

        if current_state == PortfolioProcessing.editing.state:
            await processing_msg.edit_text("✅ Портфолио обновлено.")
            await message.answer("✅ Обновление успешно завершено.", reply_markup=reply_keyboard.portfolio_kb)
            await state.finish()
            return

        await processing_msg.edit_text(
            f"📂 Ваше портфолио:\n\n{portfolio_text}\n\nЧто вы хотите сделать?"
        )

        async with state.proxy() as data:
            data['portfolio_text'] = portfolio_text
            data['tags'] = tags

        await PortfolioProcessing.confirm_tags.set()
        await message.answer(
            "Сохранить это портфолио?",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="✅ Да, сохранить")],
                    [types.KeyboardButton(text="❌ Нет, отменить")],
                ],
                resize_keyboard=True
            )
        )

    except Exception as e:
        print(f"⚠️ Произошла ошибка при обработке: {str(e)}")
        await state.finish()
    finally:
        typing_task.cancel()


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
        print(f"JSON parsing error: {e}")
        return [], False


async def confirm_tags_save(message: types.Message, state: FSMContext):
    if message.text == "✅ Да, сохранить":
        async with state.proxy() as data:
            portfolio_text = data['portfolio_text']
            tags = data['tags']
            user_id = message.from_user.id

        await update_user_portfolio(user_id, portfolio_text)
        await add_tags(user_id, tags)

        await message.answer(
            "✅ Ваше портфолио успешно сохранено!",
            reply_markup=reply_keyboard.user_kb
        )
    else:
        await message.answer(
            "❌ Изменения отменены.",
            reply_markup=reply_keyboard.start_kb
        )

    await state.finish()


async def cancel_portfolio_processing(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    portfolio = await get_user_portfolio(user_id)

    if portfolio:
        keyboard = reply_keyboard.user_kb
    else:
        keyboard = reply_keyboard.start_kb

    await message.answer(
        "❌ Действие отменено.",
        reply_markup=keyboard
    )


async def ask_delete_portfolio(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    portfolio = await get_user_portfolio(user_id)
    if not portfolio:
        await message.answer(
            "❌ У вас нет портфолио для удаления.",
            reply_markup=reply_keyboard.user_kb
        )
        return

    await state.set_state(PortfolioDelete.waiting_for_confirmation)

    await message.answer(
        "❗ Вы уверены, что хотите удалить портфолио?\n"
        "Это действие необратимо.\n\n"
        "Пожалуйста, подтвердите:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton("✅ Да, удалить")],
                [types.KeyboardButton("❌ Нет, оставить")],
            ],
            resize_keyboard=True
        )
    )


async def confirm_delete_portfolio(message: types.Message, state: FSMContext):
    if message.text == "✅ Да, удалить":
        user_id = message.from_user.id
        await delete_user_portfolio(user_id)  # Очищаем портфолио
        await add_tags(user_id, [])  # Очищаем теги

        await message.answer(
            "🗑 Ваше портфолио было удалено.",
            reply_markup=reply_keyboard.start_kb
        )
    else:
        await message.answer(
            "✅ Удаление отменено. Портфолио осталось без изменений.",
            reply_markup=reply_keyboard.portfolio_kb
        )

    await state.finish()


def register_handlers(dp: Dispatcher):
    # Обработчики команд
    dp.register_message_handler(
        start_portfolio_processing,
        text="➕ Создать портфолио",
        state="*"
    )
    dp.register_message_handler(
        show_portfolio,
        text="📂 Показать портфолио",
    )
    dp.register_message_handler(
        edit_portfolio,
        text="✏️ Редактировать портфолио",
        state="*"
    )
    dp.register_message_handler(
        back_to_main_menu,
        text="🔙 Назад",
        state="*"
    )

    # Обработчики состояний
    dp.register_message_handler(
        cancel_portfolio_processing,
        commands=["cancel"],
        state=PortfolioProcessing.all_states
    )
    dp.register_message_handler(
        process_portfolio_text,
        state=[PortfolioProcessing.waiting_for_portfolio, PortfolioProcessing.editing],
        content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        confirm_tags_save,
        state=PortfolioProcessing.confirm_tags,
        content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        ask_delete_portfolio,
        text="❌ Удалить портфолио",
        state="*"
    )
    dp.register_message_handler(
        confirm_delete_portfolio,
        state=PortfolioDelete.waiting_for_confirmation,
        content_types=types.ContentType.TEXT
    )
