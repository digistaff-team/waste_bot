"""
Хэндлер продавца: размещение лота, просмотр своих лотов, управление.
FSM: выбор ФККО → объём → единица → цена → формат цены → условие
     → адрес отправки → адрес доставки → срок → фото → подтверждение.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PhotoSize
from aiogram.fsm.context import FSMContext
from config import (
    ROLE_SELLER, CONDITION_DELIVERY, CONDITION_PICKUP,
    UNIT_TON, UNIT_M3, PRICE_FORMAT_PER_TON, PRICE_FORMAT_PER_TRIP,
)
from models.database import (
    get_user_by_tg_id, create_lot, get_lots_by_seller,
    get_lot_by_id, cancel_lot,
)
from services.fkko_service import get_popular_fkko, search_fkko, get_fkko_by_code
from services.geo_service import get_address_with_coords
from utils.states import LotCreationStates
from utils.helpers import validate_positive_number, validate_date, format_lot_card
from keyboards.main_keyboards import (
    kb_seller_main, kb_fkko_popular, kb_fkko_search_results,
    kb_choose_unit, kb_choose_price_format, kb_choose_condition,
    kb_skip_or_cancel, kb_confirm_or_cancel, kb_cancel_only,
    kb_lot_actions_seller, kb_lots_navigation,
)

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательная проверка роли
# ─────────────────────────────────────────────────────────────────────────────

async def _require_seller(message: Message) -> dict | None:
    """Проверяет, что пользователь — продавец. Возвращает user или None."""
    user = await get_user_by_tg_id(message.from_user.id)
    if not user or user["role"] != ROLE_SELLER:
        await message.answer("⛔ Эта функция доступна только для продавцов.")
        return None
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Начало создания лота
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "📦 Разместить отход")
async def cmd_create_lot(message: Message, state: FSMContext) -> None:
    user = await _require_seller(message)
    if not user:
        return

    await state.clear()
    popular = get_popular_fkko()
    await message.answer(
        "♻️ <b>Размещение лота</b>\n\n"
        "Выберите тип отхода из популярных категорий\n"
        "или нажмите 🔍 Поиск по названию:",
        reply_markup=kb_fkko_popular(popular),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.choosing_fkko)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 1: Выбор ФККО через inline-кнопки
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(LotCreationStates.choosing_fkko, F.data.startswith("fkko:"))
async def cb_fkko_selected(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]

    if code == "search":
        await callback.message.edit_text(
            "🔍 Введите название или часть кода ФККО для поиска:"
        )
        await state.set_state(LotCreationStates.entering_fkko_search)
        await callback.answer()
        return

    if code == "cancel":
        await state.clear()
        await callback.message.edit_text("Создание лота отменено.")
        await callback.message.answer("Главное меню:", reply_markup=kb_seller_main())
        await callback.answer()
        return

    item = get_fkko_by_code(code)
    if not item:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    await state.update_data(fkko_code=item["code"], fkko_name=item["name"])
    await callback.message.edit_text(
        f"✅ Выбран тип отхода:\n<b>{item['name']}</b>\n"
        f"Код ФККО: <code>{item['code']}</code>",
        parse_mode="HTML",
    )
    await callback.message.answer(
        "📦 Введите <b>объём</b> отхода (число, например: 10.5):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.entering_volume)
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 1а: Поиск ФККО по тексту
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.entering_fkko_search)
async def step_fkko_search(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    results = search_fkko(message.text.strip())
    if not results:
        await message.answer(
            "❌ Ничего не найдено. Попробуйте другой запрос\n"
            "(например: «макулатура», «металл», «пластик»):"
        )
        return

    await message.answer(
        f"🔍 Найдено {len(results)} результатов. Выберите нужный:",
        reply_markup=kb_fkko_search_results(results),
    )
    await state.set_state(LotCreationStates.choosing_fkko)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 2: Объём
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.entering_volume)
async def step_volume(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    volume = validate_positive_number(message.text)
    if volume is None:
        await message.answer("❌ Введите положительное число (например: 10 или 10.5):")
        return

    await state.update_data(volume=volume)
    await message.answer(
        "📏 Выберите <b>единицу измерения</b>:",
        reply_markup=kb_choose_unit(),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.choosing_unit)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 3: Единица измерения
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.choosing_unit)
async def step_unit(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    unit_map = {
        f"⚖️ {UNIT_TON}": UNIT_TON,
        f"📦 {UNIT_M3}": UNIT_M3,
    }
    unit = unit_map.get(message.text)
    if not unit:
        await message.answer("Выберите единицу из предложенных:", reply_markup=kb_choose_unit())
        return

    await state.update_data(unit=unit)
    await message.answer(
        "💰 Введите <b>цену</b> (число, например: 2000):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.entering_price)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 4: Цена
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.entering_price)
async def step_price(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    price = validate_positive_number(message.text)
    if price is None:
        await message.answer("❌ Введите положительное число (например: 2000):")
        return

    await state.update_data(price=price)
    await message.answer(
        "📊 Выберите <b>формат цены</b>:",
        reply_markup=kb_choose_price_format(),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.choosing_price_format)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 5: Формат цены
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.choosing_price_format)
async def step_price_format(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    fmt_map = {
        f"💰 {PRICE_FORMAT_PER_TON}": PRICE_FORMAT_PER_TON,
        f"🚛 {PRICE_FORMAT_PER_TRIP}": PRICE_FORMAT_PER_TRIP,
    }
    price_format = fmt_map.get(message.text)
    if not price_format:
        await message.answer("Выберите формат из предложенных:", reply_markup=kb_choose_price_format())
        return

    await state.update_data(price_format=price_format)
    await message.answer(
        "🚚 Выберите <b>условие передачи</b>:",
        reply_markup=kb_choose_condition(),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.choosing_condition)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 6: Условие передачи
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.choosing_condition)
async def step_condition(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    cond_map = {
        f"🚚 {CONDITION_DELIVERY}": CONDITION_DELIVERY,
        f"🏭 {CONDITION_PICKUP}": CONDITION_PICKUP,
    }
    condition = cond_map.get(message.text)
    if not condition:
        await message.answer("Выберите условие из предложенных:", reply_markup=kb_choose_condition())
        return

    await state.update_data(condition=condition)

    # Для доставки запрашиваем адреса
    if condition == CONDITION_DELIVERY:
        await message.answer(
            "📍 Введите <b>адрес отправки</b> (откуда забрать отход):\n"
            "<i>Например: Москва, ул. Промышленная, 5</i>",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(LotCreationStates.entering_address_from)
    else:
        # Самовывоз — только адрес откуда
        await message.answer(
            "📍 Введите <b>адрес самовывоза</b>:\n"
            "<i>Например: Москва, ул. Промышленная, 5</i>",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(LotCreationStates.entering_address_from)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 7: Адрес отправки
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.entering_address_from)
async def step_address_from(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    address = message.text.strip()
    geo_msg = await message.answer("🗺 Определяю координаты адреса...")
    geo = await get_address_with_coords(address)
    await geo_msg.delete()

    await state.update_data(
        address_from=geo["address"],
        lat_from=geo["lat"],
        lon_from=geo["lon"],
    )

    if geo["lat"]:
        await message.answer(f"✅ Адрес найден: {address}")
    else:
        await message.answer(f"⚠️ Координаты не определены, адрес сохранён как текст.")

    data = await state.get_data()
    if data.get("condition") == CONDITION_DELIVERY:
        await message.answer(
            "🏁 Введите <b>адрес доставки</b> (куда доставить):\n"
            "<i>Например: Санкт-Петербург, ул. Заводская, 10</i>",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(LotCreationStates.entering_address_to)
    else:
        await _ask_valid_until(message, state)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 8: Адрес доставки (только для "с доставкой")
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.entering_address_to)
async def step_address_to(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    address = message.text.strip()
    geo_msg = await message.answer("🗺 Определяю координаты адреса...")
    geo = await get_address_with_coords(address)
    await geo_msg.delete()

    await state.update_data(
        address_to=geo["address"],
        lat_to=geo["lat"],
        lon_to=geo["lon"],
    )

    if geo["lat"]:
        await message.answer(f"✅ Адрес доставки найден: {address}")
    else:
        await message.answer(f"⚠️ Координаты не определены, адрес сохранён как текст.")

    await _ask_valid_until(message, state)


async def _ask_valid_until(message: Message, state: FSMContext) -> None:
    await message.answer(
        "📅 Введите <b>дату окончания актуальности</b> лота (ДД.ММ.ГГГГ)\n"
        "или нажмите ⏭ Пропустить:",
        reply_markup=kb_skip_or_cancel(),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.entering_valid_until)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 9: Срок актуальности
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.entering_valid_until)
async def step_valid_until(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    if message.text == "⏭ Пропустить":
        await state.update_data(valid_until=None)
    else:
        dt = validate_date(message.text)
        if not dt:
            await message.answer(
                "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ\n"
                "или нажмите ⏭ Пропустить:"
            )
            return
        await state.update_data(valid_until=message.text.strip())

    await message.answer(
        "📸 Прикрепите <b>фото отхода</b> (необязательно)\n"
        "или нажмите ⏭ Пропустить:",
        reply_markup=kb_skip_or_cancel(),
        parse_mode="HTML",
    )
    await state.set_state(LotCreationStates.uploading_photo)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 10: Фото (опционально)
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.uploading_photo, F.photo)
async def step_photo(message: Message, state: FSMContext) -> None:
    # Берём фото наилучшего качества
    photo: PhotoSize = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)
    await message.answer("✅ Фото прикреплено!")
    await _show_lot_preview(message, state)


@router.message(LotCreationStates.uploading_photo)
async def step_photo_skip(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return
    if message.text == "⏭ Пропустить":
        await state.update_data(photo_file_id=None)
        await _show_lot_preview(message, state)
    else:
        await message.answer(
            "Пожалуйста, прикрепите фото или нажмите ⏭ Пропустить:",
            reply_markup=kb_skip_or_cancel(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Предпросмотр лота
# ─────────────────────────────────────────────────────────────────────────────

async def _show_lot_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()

    # Формируем временный объект лота для форматирования
    preview_lot = {
        "id": "—",
        "fkko_name": data["fkko_name"],
        "fkko_code": data["fkko_code"],
        "volume": data["volume"],
        "unit": data["unit"],
        "price": data["price"],
        "price_format": data["price_format"],
        "condition": data["condition"],
        "address_from": data.get("address_from"),
        "address_to": data.get("address_to"),
        "valid_until": data.get("valid_until"),
        "status": "active",
    }

    card = format_lot_card(preview_lot)
    preview_text = f"📋 <b>Предпросмотр лота:</b>\n\n{card}"

    if data.get("photo_file_id"):
        await message.answer_photo(
            photo=data["photo_file_id"],
            caption=preview_text,
            reply_markup=kb_confirm_or_cancel(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            preview_text,
            reply_markup=kb_confirm_or_cancel(),
            parse_mode="HTML",
        )
    await state.set_state(LotCreationStates.confirming)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 11: Подтверждение публикации
# ─────────────────────────────────────────────────────────────────────────────

@router.message(LotCreationStates.confirming)
async def step_lot_confirm(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лота отменено.", reply_markup=kb_seller_main())
        return

    if message.text != "✅ Подтвердить":
        await message.answer(
            "Нажмите ✅ Подтвердить для публикации или ❌ Отмена:",
            reply_markup=kb_confirm_or_cancel(),
        )
        return

    data = await state.get_data()
    user = await get_user_by_tg_id(message.from_user.id)

    lot_data = {
        "seller_id": user["id"],
        "fkko_code": data["fkko_code"],
        "fkko_name": data["fkko_name"],
        "volume": data["volume"],
        "unit": data["unit"],
        "price": data["price"],
        "price_format": data["price_format"],
        "condition": data["condition"],
        "address_from": data.get("address_from"),
        "address_to": data.get("address_to"),
        "lat_from": data.get("lat_from"),
        "lon_from": data.get("lon_from"),
        "lat_to": data.get("lat_to"),
        "lon_to": data.get("lon_to"),
        "valid_until": data.get("valid_until"),
        "photo_file_id": data.get("photo_file_id"),
    }

    try:
        lot_id = await create_lot(lot_data)
        await state.clear()
        await message.answer(
            f"✅ <b>Лот #{lot_id} опубликован!</b>\n\n"
            f"♻️ {data['fkko_name']}\n"
            f"📦 {data['volume']} {data['unit']} — "
            f"{data['price']:,.0f} ₽ {data['price_format']}",
            reply_markup=kb_seller_main(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка при создании лота: %s", e)
        await message.answer(
            "❌ Ошибка при публикации лота. Попробуйте позже.",
            reply_markup=kb_seller_main(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Просмотр своих лотов
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "📋 Мои лоты")
async def cmd_my_lots(message: Message, state: FSMContext) -> None:
    user = await _require_seller(message)
    if not user:
        return

    lots = await get_lots_by_seller(user["id"])
    if not lots:
        await message.answer(
            "📭 У вас пока нет размещённых лотов.\n"
            "Нажмите 📦 Разместить отход чтобы создать первый.",
            reply_markup=kb_seller_main(),
        )
        return

    await state.update_data(lots=lots, lots_page=0)
    await _show_lot_page(message, lots, 0)


async def _show_lot_page(message: Message, lots: list, page: int) -> None:
    lot = lots[page]
    card = format_lot_card(lot)
    total = len(lots)

    if lot.get("photo_file_id"):
        await message.answer_photo(
            photo=lot["photo_file_id"],
            caption=card,
            reply_markup=kb_lot_actions_seller(lot["id"]),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            card,
            reply_markup=kb_lot_actions_seller(lot["id"]),
            parse_mode="HTML",
        )

    if total > 1:
        await message.answer(
            f"Лот {page + 1} из {total}",
            reply_markup=kb_lots_navigation(page, total),
        )


@router.callback_query(F.data.startswith("lots_nav:"))
async def cb_lots_nav(callback: CallbackQuery, state: FSMContext) -> None:
    # Проверка роли продавца
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or user["role"] != ROLE_SELLER:
        await callback.answer("⛔ Эта функция доступна только для продавцов", show_alert=True)
        return

    page_str = callback.data.split(":")[1]
    if page_str == "noop":
        await callback.answer()
        return

    page = int(page_str)
    data = await state.get_data()
    lots = data.get("lots", [])

    if not lots or page < 0 or page >= len(lots):
        await callback.answer("Нет данных", show_alert=True)
        return

    await state.update_data(lots_page=page)
    lot = lots[page]
    card = format_lot_card(lot)

    await callback.message.edit_text(
        f"{card}\n\nЛот {page + 1} из {len(lots)}",
        reply_markup=kb_lots_navigation(page, len(lots)),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Отмена лота
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lot_cancel:"))
async def cb_lot_cancel(callback: CallbackQuery) -> None:
    lot_id = int(callback.data.split(":")[1])
    success = await cancel_lot(lot_id, callback.from_user.id)

    if success:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"✅ Лот #{lot_id} снят с публикации.",
            reply_markup=kb_seller_main(),
        )
    else:
        await callback.answer(
            "❌ Не удалось снять лот (уже отменён или не найден)",
            show_alert=True,
        )
    await callback.answer()
