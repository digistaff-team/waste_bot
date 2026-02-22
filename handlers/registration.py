"""
Хэндлер регистрации пользователей.
FSM-диалог: роль → название орг. → ИНН → регион → телефон → email
→ (для перевозчика: типы ТС → грузоподъёмность → регионы перевозок)
→ подтверждение → сохранение в БД.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart

from config import ROLE_SELLER, ROLE_BUYER, ROLE_CARRIER
from models.database import get_user_by_tg_id, create_user
from services.fns_service import check_inn
from utils.states import RegistrationStates
from utils.helpers import (
    validate_inn, validate_phone, validate_email, format_user_card
)
from keyboards.main_keyboards import (
    kb_choose_role, kb_main_by_role, kb_confirm_or_cancel, kb_cancel_only
)

logger = logging.getLogger(__name__)
router = Router()

# ─────────────────────────────────────────────────────────────────────────────
# /start — точка входа
# ─────────────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await get_user_by_tg_id(message.from_user.id)

    if user:
        from keyboards.main_keyboards import kb_main_by_role
        await message.answer(
            f"👋 С возвращением, <b>{user['org_name']}</b>!\n"
            f"Ваша роль: {user['role']}",
            reply_markup=kb_main_by_role(user["role"]),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "♻️ <b>Добро пожаловать в WasteBot!</b>\n\n"
        "Платформа для прозрачного обращения с отходами.\n\n"
        "Выберите вашу роль:",
        reply_markup=kb_choose_role(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.choosing_role)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 1: Выбор роли
# ─────────────────────────────────────────────────────────────────────────────

@router.message(RegistrationStates.choosing_role)
async def step_choose_role(message: Message, state: FSMContext) -> None:
    text = message.text.strip()

    role_map = {
        "🏭 Продавец": ROLE_SELLER,
        "🛒 Покупатель": ROLE_BUYER,
        "🚛 Перевозчик": ROLE_CARRIER,
    }
    role = role_map.get(text)
    if not role:
        await message.answer(
            "Пожалуйста, выберите роль из предложенных вариантов.",
            reply_markup=kb_choose_role(),
        )
        return

    await state.update_data(role=role)
    await message.answer(
        "🏢 Введите <b>название вашей организации</b> (или ФИО для ИП):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.entering_org_name)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 2: Название организации
# ─────────────────────────────────────────────────────────────────────────────

@router.message(RegistrationStates.entering_org_name)
async def step_org_name(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    org_name = message.text.strip()
    if len(org_name) < 2:
        await message.answer("Название слишком короткое. Попробуйте ещё раз:")
        return

    await state.update_data(org_name=org_name)
    await message.answer(
        "📋 Введите <b>ИНН</b> организации (10 или 12 цифр):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.entering_inn)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 3: ИНН
# ─────────────────────────────────────────────────────────────────────────────

@router.message(RegistrationStates.entering_inn)
async def step_inn(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    inn = message.text.strip()
    if not validate_inn(inn):
        await message.answer(
            "❌ Неверный формат ИНН. Введите 10 или 12 цифр:"
        )
        return

    # Проверка через API ФНС
    checking_msg = await message.answer("🔍 Проверяю ИНН через реестр ФНС...")
    fns_result = await check_inn(inn)

    if not fns_result["valid"]:
        await checking_msg.delete()
        await message.answer(
            f"❌ {fns_result['error']}\n\nВведите корректный ИНН:"
        )
        return

    await checking_msg.delete()

    data = await state.get_data()
    # Если ФНС вернул название — предлагаем использовать его
    if fns_result.get("org_name"):
        await state.update_data(inn=inn, fns_org_name=fns_result["org_name"])
        await message.answer(
            f"✅ ИНН найден в реестре ФНС.\n"
            f"Организация: <b>{fns_result['org_name']}</b>\n\n"
            f"🌍 Введите <b>регион деятельности</b> (например: Москва, Московская область):",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
    else:
        await state.update_data(inn=inn)
        if fns_result.get("error"):
            await message.answer(f"⚠️ {fns_result['error']}")
        await message.answer(
            "🌍 Введите <b>регион деятельности</b> (например: Москва, Московская область):",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )

    await state.set_state(RegistrationStates.entering_region)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 4: Регион
# ─────────────────────────────────────────────────────────────────────────────

@router.message(RegistrationStates.entering_region)
async def step_region(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    region = message.text.strip()
    if len(region) < 2:
        await message.answer("Введите корректный регион:")
        return

    await state.update_data(region=region)
    await message.answer(
        "📞 Введите <b>контактный телефон</b> (например: +79001234567):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.entering_phone)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 5: Телефон
# ─────────────────────────────────────────────────────────────────────────────

@router.message(RegistrationStates.entering_phone)
async def step_phone(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    phone = message.text.strip()
    if not validate_phone(phone):
        await message.answer(
            "❌ Неверный формат телефона.\n"
            "Введите в формате +79001234567 или 89001234567:"
        )
        return

    await state.update_data(phone=phone)
    await message.answer(
        "📧 Введите <b>email</b> для связи:",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.entering_email)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 6: Email
# ─────────────────────────────────────────────────────────────────────────────

@router.message(RegistrationStates.entering_email)
async def step_email(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    email = message.text.strip().lower()
    if not validate_email(email):
        await message.answer("❌ Неверный формат email. Попробуйте ещё раз:")
        return

    await state.update_data(email=email)
    data = await state.get_data()

    # Для перевозчика — дополнительные поля
    if data["role"] == ROLE_CARRIER:
        await message.answer(
            "🚛 Введите <b>типы транспортных средств</b>\n"
            "(например: Газель, Фура 20т, Самосвал):",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(RegistrationStates.entering_vehicle_types)
    else:
        await _show_confirmation(message, state)


# ─────────────────────────────────────────────────────────────────────────────
# Шаги для перевозчика
# ─────────────────────────────────────────────────────────────────────────────

@router.message(RegistrationStates.entering_vehicle_types)
async def step_vehicle_types(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    await state.update_data(vehicle_types=message.text.strip())
    await message.answer(
        "⚖️ Введите <b>максимальную грузоподъёмность</b> (в тоннах, например: 20):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.entering_capacity)


@router.message(RegistrationStates.entering_capacity)
async def step_capacity(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    try:
        capacity = float(message.text.replace(",", "."))
        if capacity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число (например: 20):")
        return

    await state.update_data(capacity=capacity)
    await message.answer(
        "🗺 Введите <b>регионы перевозок</b>\n"
        "(через запятую, например: Москва, Московская область, Тверь)\n"
        "Или напишите «все» для работы по всей России:",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.entering_carrier_regions)


@router.message(RegistrationStates.entering_carrier_regions)
async def step_carrier_regions(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    await state.update_data(carrier_regions=message.text.strip())
    await _show_confirmation(message, state)


# ─────────────────────────────────────────────────────────────────────────────
# Подтверждение регистрации
# ─────────────────────────────────────────────────────────────────────────────

async def _show_confirmation(message: Message, state: FSMContext) -> None:
    """Показать карточку с данными для подтверждения."""
    data = await state.get_data()

    role_labels = {
        ROLE_SELLER: "🏭 Продавец",
        ROLE_BUYER: "🛒 Покупатель",
        ROLE_CARRIER: "🚛 Перевозчик",
    }

    lines = [
        "📋 <b>Проверьте данные регистрации:</b>",
        "",
        f"👤 Организация: <b>{data['org_name']}</b>",
        f"🏷 Роль: {role_labels.get(data['role'], data['role'])}",
        f"📋 ИНН: {data['inn']}",
        f"🌍 Регион: {data['region']}",
        f"📞 Телефон: {data['phone']}",
        f"📧 Email: {data['email']}",
    ]
    if data.get("vehicle_types"):
        lines.append(f"🚛 Типы ТС: {data['vehicle_types']}")
    if data.get("capacity"):
        lines.append(f"⚖️ Грузоподъёмность: {data['capacity']} т")
    if data.get("carrier_regions"):
        lines.append(f"🗺 Регионы перевозок: {data['carrier_regions']}")

    await message.answer(
        "\n".join(lines),
        reply_markup=kb_confirm_or_cancel(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.confirming)


@router.message(RegistrationStates.confirming)
async def step_confirm(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _cancel_registration(message, state)
        return

    if message.text != "✅ Подтвердить":
        await message.answer(
            "Нажмите ✅ Подтвердить или ❌ Отмена",
            reply_markup=kb_confirm_or_cancel(),
        )
        return

    data = await state.get_data()
    user_data = {
        "tg_id": message.from_user.id,
        "role": data["role"],
        "org_name": data["org_name"],
        "inn": data["inn"],
        "region": data["region"],
        "phone": data["phone"],
        "email": data["email"],
        "vehicle_types": data.get("vehicle_types"),
        "capacity": data.get("capacity"),
        "carrier_regions": data.get("carrier_regions"),
    }

    try:
        await create_user(user_data)
        await state.clear()

        role_labels = {
            ROLE_SELLER: "🏭 Продавец",
            ROLE_BUYER: "🛒 Покупатель",
            ROLE_CARRIER: "🚛 Перевозчик",
        }
        await message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"Добро пожаловать, {data['org_name']}!\n"
            f"Ваша роль: {role_labels.get(data['role'], data['role'])}",
            reply_markup=kb_main_by_role(data["role"]),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка при создании пользователя: %s", e)
        await message.answer(
            "❌ Произошла ошибка при регистрации. Попробуйте позже или обратитесь к администратору."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Отмена регистрации
# ─────────────────────────────────────────────────────────────────────────────

async def _cancel_registration(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Регистрация отменена. Нажмите /start чтобы начать заново.",
        reply_markup=kb_choose_role(),
    )
