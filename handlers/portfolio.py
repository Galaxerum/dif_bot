from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardRemove
from db.users import get_user, update_user_portfolio, get_user_portfolio
from db.tags import add_tags, get_user_tags
from services.gemini_api import generate_text
import json
import asyncio
from keyboards import reply_keyboard  # Импортируем клавиатуры


class PortfolioProcessing(StatesGroup):
    waiting_for_portfolio = State()
    processing = State()
    confirm_tags = State()
    editing = State()


async def show_typing(chat_id, bot):
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(3)


async def start_portfolio_processing(message: types.Message):
    await PortfolioProcessing.waiting_for_portfolio.set()
    await message.answer(
        "📝 Отправьте текст вашего портфолио для обработки.\n"
        "Я разберу его на ключевые теги и сохраню.\n\n"
        "(Чтобы отменить, используйте /cancel)",
        reply_markup=ReplyKeyboardRemove()
    )


async def show_portfolio(message: types.Message):
    user_id = message.from_user.id
    portfolio = await get_user_portfolio(user_id)

    if not portfolio:
        await message.answer(
            "❌ У вас ещё нет сохранённого портфолио.\n"
            "Используйте /portfolio чтобы создать его.",
            reply_markup=reply_keyboard.user_kb
        )
        return

    # Для дебага получаем теги, но пользователю не показываем
    debug_tags = await get_user_tags(user_id)
    print(f"Debug: User {user_id} tags: {debug_tags}")  # Логируем теги в консоль

    await message.answer(
        f"📂 Ваше портфолио:\n\n{portfolio}\n\n"
        "Что вы хотите сделать?",
        reply_markup=reply_keyboard.portfolio_kb
    )


async def edit_portfolio(message: types.Message):
    await PortfolioProcessing.editing.set()
    await message.answer(
        "✏️ Отправьте новый текст портфолио для обновления.\n"
        "(Чтобы отменить, используйте /cancel)",
        reply_markup=ReplyKeyboardRemove()
    )


async def process_portfolio_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    portfolio_text = message.text.strip()

    user = await get_user(user_id)
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")
        await state.finish()
        return

    current_state = await state.get_state()
    if current_state == PortfolioProcessing.editing.state:
        # Если это редактирование, сразу обновляем без подтверждения
        await update_user_portfolio(user_id, portfolio_text)
        await message.answer(
            "✅ Портфолио успешно обновлено!",
            reply_markup=reply_keyboard.user_kb
        )
        await state.finish()
        return

    await PortfolioProcessing.processing.set()
    async with state.proxy() as data:
        data['portfolio_text'] = portfolio_text

    typing_task = asyncio.create_task(show_typing(message.chat.id, message.bot))

    try:
        processing_msg = await message.answer("⏳ Обрабатываю ваше портфолио...")

        tags = await generate_text(
            f"Разбей следующее портфолио на теги. Ответ только в виде формата JSON. Максимум 2048 символов. "
            f"Ответы должны быть максимально краткие. Тегов должно быть не менее 5.\n"
            f"Вот портфолио: {portfolio_text}"
        )

        # Для дебага выводим теги в консоль
        print(f"Debug: Generated tags for user {user_id}: {tags}")

        await processing_msg.delete()
        await message.answer("🔍 Теги успешно сгенерированы и сохранены!")

        async with state.proxy() as data:
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
        await message.answer(f"⚠️ Произошла ошибка при обработке: {str(e)}")
        await state.finish()
    finally:
        typing_task.cancel()

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
            reply_markup=reply_keyboard.user_kb
        )

    await state.finish()


async def cancel_portfolio_processing(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=reply_keyboard.user_kb
    )


def register_handlers(dp: Dispatcher):
    # Обработчики команд
    dp.register_message_handler(
        start_portfolio_processing,
        commands=["portfolio"],
        state="*"
    )
    dp.register_message_handler(
        show_portfolio,
        text="📂 Показать портфолио",
        state="*"
    )
    dp.register_message_handler(
        edit_portfolio,
        text="✏️ Редактировать портфолио",
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