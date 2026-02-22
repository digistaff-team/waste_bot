"""
Общие хэндлеры: профиль пользователя, команды /help, /cancel,
обработка неизвестных сообщений.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from config import ROLE_SELLER, ROLE_BUYER, ROLE_CARRIER
from models.database import get_user_by_tg_id
from utils.helpers import format_user_card
from keyboards.main_keyboards import kb_main_by_role, kb_choose_role

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# /help
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    user = await get_user_by_tg_id(message.from_user.id)

    base_help = (
        "♻️ <b>WasteBot — помощь</b>\n\n"
        "<b>Общие команды:</b>\n"
        "/start — перезапустить бота / главное меню\n"
        "/help — эта справка\n"
        "/cancel — отменить текущее действие\n"
        "/profile — мой профиль\n\n"
    )

    if not user:
        await message.answer(
            base_help + "Для начала работы нажмите /start и зарегистрируйтесь.",
            parse_mode="HTML",
        )
        return

    role_help = {
        ROLE_SELLER: (
            "<b>Команды продавца:</b>\n"
            "📦 Разместить отход — создать новый лот\n"
            "📋 Мои лоты — просмотр и управление лотами\n"
            "📊 Мои сделки — история завершённых сделок\n"
        ),
        ROLE_BUYER: (
            "<b>Команды покупателя:</b>\n"
            "🔍 Найти отходы — поиск по фильтрам\n"
            "📋 Мои заявки — статус текущих заявок\n"
            "📊 Мои сделки — история завершённых сделок\n"
        ),
        ROLE_CARRIER: (
            "<b>Команды перевозчика:</b>\n"
            "📋 Доступные заявки — список заявок на перевозку\n"
            "🚛 Мои перевозки — текущие и завершённые рейсы\n"
        ),
    }

    await message.answer(
        base_help + role_help.get(user["role"], ""),
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    await state.clear()
    user = await get_user_by_tg_id(message.from_user.id)
    
    if user:
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=kb_main_by_role(user["role"]),
        )
    else:
        await message.answer(
            "❌ Действие отменено. Нажмите /start для начала работы.",
            reply_markup=kb_choose_role(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# /profile
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("profile"))
@router.message(F.text == "👤 Мой профиль")
async def cmd_profile(message: Message) -> None:
    user = await get_user_by_tg_id(message.from_user.id)
    
    if not user:
        await message.answer(
            "Вы не зарегистрированы. Нажмите /start для начала работы.",
            reply_markup=kb_choose_role(),
        )
        return

    await message.answer(
        format_user_card(user),
        parse_mode="HTML",
        reply_markup=kb_main_by_role(user["role"]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fallback — обработка неизвестных сообщений
# ─────────────────────────────────────────────────────────────────────────────

@router.message()
async def fallback_message(message: Message) -> None:
    user = await get_user_by_tg_id(message.from_user.id)
    
    if not user:
        await message.answer(
            "Я вас не понимаю. Нажмите /start для начала работы.",
            reply_markup=kb_choose_role(),
        )
        return

    await message.answer(
        "Я вас не понимаю. Используйте кнопки меню или /help для справки.",
        reply_markup=kb_main_by_role(user["role"]),
    )