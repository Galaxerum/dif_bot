from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from db.users import get_user, update_user_portfolio, get_user_portfolio, delete_user_portfolio, update_user_username
from db.tags import add_tags
from services.local_AI import generate_text
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
    waiting_for_username = State()
    waiting_for_portfolio = State()
    processing = State()
    confirm_tags = State()
    editing = State()
    choose_edit = State()
    waiting_for_new_username = State()
    waiting_for_new_portfolio = State()

class PortfolioDelete(StatesGroup):
    waiting_for_confirmation = State()

async def show_typing(chat_id, bot):
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(3)

async def start_portfolio_processing(message: types.Message, state: FSMContext):
    await state.set_state(PortfolioProcessing.waiting_for_username)
    await message.answer(
        "📝 Пожалуйста, введите ваше ФИО для профиля.\n"
        "(Чтобы отменить, используйте /cancel)",
        reply_markup=ReplyKeyboardRemove()
    )

async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if len(username) < 3:
        await message.answer("Пожалуйста, введите корректное ФИО (минимум 3 символа).")
        return
    user_id = message.from_user.id
    await update_user_username(user_id, username)
    await state.set_state(PortfolioProcessing.waiting_for_portfolio)

    portfolio_instructions = (
        "🎯 Давай соберём твою визитку — мини-портфолио.\n"
        "Хочется понять, кто ты, в чём твоя сила и с кем тебя стоит познакомить.\n"
        "Расскажи о себе — можно в свободной форме, а можно по этим пунктам:\n\n"

        "- Расскажи коротко о себе\n"
        "  Кто ты, с какого города, чем занимаешься, в какой сфере работаешь?\n\n"

        "- Чем ты полезен другим\n"
        "  Навыки, опыт, чем можешь усилить проект или команду?\n\n"

        "- В чём твоя сила\n"
        "  Расскажи о своих достижениях. Можно с цифрами, если хочется!\n\n"

        "- Интересные факты\n"
        "  2–3 коротких, ярких штриха к портрету.\n"
        "  Не банальщина — то, что тебя выделяет.\n\n"

        "- Еще можно выйти за рамки обыденного и добавить:\n"
        "— Что бы ты сделал, если бы не боялся последствий?\n"
        "— Чем бы занялся, если бы у тебя были все ресурсы мира?"
    )

    await message.answer(
        portfolio_instructions,
        parse_mode="HTML"
    )

async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "↩️ Возврат в главное меню.",
        reply_markup=reply_keyboard.user_kb
    )

async def process_new_username(message: types.Message, state: FSMContext):
    new_username = message.text.strip()
    if 3 > len(new_username) > 128:
        await message.answer("Пожалуйста, введите корректное ФИО.")
        return
    user_id = message.from_user.id
    await update_user_username(user_id, new_username)
    await message.answer("✅ ФИО успешно обновлено.", reply_markup=reply_keyboard.portfolio_kb)
    await state.finish()

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
        processing_msg = await message.answer("⏳ Сохраняю ваш профиль...")

        tags = []
        is_meaningful = True

        if USE_AI:
            tags, is_meaningful = await _process_portfolio_with_ai(portfolio_text)
            if not is_meaningful or not tags:
                await message.answer(
                    "❌ Ваш профиль не содержит достаточно сведений.\n"
                    "Пожалуйста, отправьте более подробный и содержательный текст."
                )
                return

            update_known_tags(tags)
            await add_tags(user_id, tags)
            print(f"Tags for user {user_id}: {tags}")

        await update_user_portfolio(user_id, portfolio_text)

        if current_state in [PortfolioProcessing.editing.state,
                           PortfolioProcessing.waiting_for_new_portfolio.state]:
            await processing_msg.edit_text("✅ Профиль обновлено.")
            await message.answer("✅ Обновление успешно завершено.", reply_markup=reply_keyboard.portfolio_kb)
            await state.finish()
            return

        await processing_msg.edit_text(
            f"📂 Ваш профиль:\n\n{portfolio_text}\n\nЧто вы хотите сделать?"
        )

        async with state.proxy() as data:
            data['portfolio_text'] = portfolio_text
            data['tags'] = tags

        await PortfolioProcessing.confirm_tags.set()
        await message.answer(
            "Сохранить этот профиль?",
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
            "✅ Ваш профиль успешно сохранен!",
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
            "❌ У вас нет профиля для удаления.",
            reply_markup=reply_keyboard.user_kb
        )
        return

    await state.set_state(PortfolioDelete.waiting_for_confirmation)

    await message.answer(
        "❗ Вы уверены, что хотите удалить профиль?\n"
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
            "🗑 Ваше профиль был удален.",
            reply_markup=reply_keyboard.start_kb
        )
    else:
        await message.answer(
            "✅ Удаление отменено. Профиль остался без изменений.",
            reply_markup=reply_keyboard.portfolio_kb
        )

    await state.finish()

async def edit_portfolio(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    portfolio = await get_user_portfolio(user_id)

    if not portfolio:
        await message.answer(
            "❌ У вас ещё нет сохранённого профиля.\n"
            "Нажмите '➕ Создать профиль' чтобы создать его.",
            reply_markup=reply_keyboard.start_kb
        )
        return

    await state.set_state(PortfolioProcessing.choose_edit)
    await message.answer(
        "Что вы хотите изменить?",
        reply_markup=reply_keyboard.edit_options_kb
    )

async def choose_edit_handler(message: types.Message, state: FSMContext):
    if message.text == "📝 Изменить ФИО":
        await PortfolioProcessing.waiting_for_new_username.set()
        await message.answer(
            "Пожалуйста, введите новое ФИО:",
            reply_markup=ReplyKeyboardRemove()
        )
    elif message.text == "📄 Изменить профиль":
        await PortfolioProcessing.waiting_for_new_portfolio.set()
        await message.answer(
            "✏️ Отправьте новый текст профиля для обновления.\n"
            "(Чтобы отменить, используйте /cancel)",
            reply_markup=ReplyKeyboardRemove()
        )
    elif message.text == "❌ Отмена":
        await state.finish()
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=reply_keyboard.portfolio_kb
        )
    else:
        await message.answer(
            "Пожалуйста, выберите один из вариантов:",
            reply_markup=reply_keyboard.edit_options_kb
        )


async def show_portfolio(message: types.Message):
    user_id = message.from_user.id
    portfolio = await get_user_portfolio(user_id)
    user = await get_user(user_id)  # Получаем объект пользователя

    # Получаем username через атрибут, а не через .get()
    username = getattr(user, "username", "Не указано ФИО") if user else "Не указано ФИО"

    if not portfolio:
        await message.answer(
            "❌ У вас ещё нет сохранённого профиля.\n"
            "Нажмите '➕ Создать профиль' чтобы создать его.",
            reply_markup=reply_keyboard.start_kb
        )
        return

    # Формируем сообщение с ФИО и портфолио
    portfolio_message = (
        f"👤 <b>Пользователь:</b> {username}\n\n"
        f"📂 <b>Профиль:</b>\n{portfolio}\n\n"
        "Выберите действие:"
    )

    await message.answer(
        portfolio_message,
        parse_mode="HTML",
        reply_markup=reply_keyboard.portfolio_kb
    )


def register_handlers(dp: Dispatcher):
    # Обработчики команд
    dp.register_message_handler(
        start_portfolio_processing,
        text="➕ Создать профиль",
        state="*"
    )
    dp.register_message_handler(
        show_portfolio,
        text="📂 Показать профиль",
    )
    dp.register_message_handler(
        edit_portfolio,
        text="✏️ Редактировать профиль",
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
        process_username,
        state=PortfolioProcessing.waiting_for_username,
        content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        process_portfolio_text,
        state=[PortfolioProcessing.waiting_for_portfolio,
              PortfolioProcessing.editing,
              PortfolioProcessing.waiting_for_new_portfolio],
        content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        confirm_tags_save,
        state=PortfolioProcessing.confirm_tags,
        content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        choose_edit_handler,
        state=PortfolioProcessing.choose_edit,
        content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        process_new_username,
        state=PortfolioProcessing.waiting_for_new_username,
        content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        ask_delete_portfolio,
        text="❌ Удалить профиль",
        state="*"
    )
    dp.register_message_handler(
        confirm_delete_portfolio,
        state=PortfolioDelete.waiting_for_confirmation,
        content_types=types.ContentType.TEXT
    )