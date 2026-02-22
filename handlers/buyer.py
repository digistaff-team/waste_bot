"""
Хэндлер покупателя: поиск лотов с фильтрами, просмотр, оформление покупки,
трекинг статуса заявок, просмотр документов.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ROLE_BUYER
from models.database import (
    get_user_by_tg_id, search_lots, get_lot_by_id,
    get_requests_for_buyer,
    get_transport_request_by_id, get_status_history,
    get_documents_by_request, update_request_status,
    update_lot_status, create_transport_request,
)
from services.transport_service import calculate_lot_transport_info, format_transport_cost_breakdown
from utils.states import BuyerSearchStates
from utils.helpers import (
    validate_positive_number, format_lot_card, format_transport_request
)
from keyboards.main_keyboards import (
    kb_buyer_main, kb_search_filters, kb_lot_actions_buyer,
    kb_lots_navigation, kb_cancel_only, kb_confirm_or_cancel,
    kb_request_actions_buyer, kb_generate_docs,
)

logger = logging.getLogger(__name__)
router = Router()

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательная проверка роли
# ─────────────────────────────────────────────────────────────────────────────

async def _require_buyer(message: Message) -> dict | None:
    user = await get_user_by_tg_id(message.from_user.id)
    if not user or user["role"] != ROLE_BUYER:
        await message.answer("⛔ Эта функция доступна только для покупателей.")
        return None
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Поиск отходов — главный экран фильтров
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "🔍 Найти отходы")
async def cmd_search(message: Message, state: FSMContext) -> None:
    user = await _require_buyer(message)
    if not user:
        return

    await state.clear()
    # Инициализируем пустые фильтры
    filters = {}
    await state.update_data(filters=filters, search_results=[], search_page=0)

    await message.answer(
        "🔍 <b>Поиск отходов</b>\n\n"
        "Настройте фильтры и нажмите 🔍 Найти.\n"
        "Все фильтры необязательны — без фильтров покажет все активные лоты.",
        reply_markup=kb_search_filters(filters),
        parse_mode="HTML",
    )
    await state.set_state(BuyerSearchStates.choosing_filter)


# ─────────────────────────────────────────────────────────────────────────────
# Обработка нажатий на фильтры
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(BuyerSearchStates.choosing_filter, F.data.startswith("filter:"))
async def cb_filter_action(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":")[1]
    data = await state.get_data()
    filters = data.get("filters", {})

    if action == "region":
        await callback.message.answer(
            "📍 Введите <b>регион</b> для поиска\n"
            "(например: Москва, Санкт-Петербург):",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(BuyerSearchStates.entering_region)

    elif action == "fkko":
        await callback.message.answer(
            "♻️ Введите <b>тип отхода</b> для поиска\n"
            "(например: макулатура, металл, пластик):",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(BuyerSearchStates.entering_fkko_filter)

    elif action == "volume":
        await callback.message.answer(
            "📦 Введите <b>минимальный объём</b> (тонн/м³)\n"
            "или 0 для любого:",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(BuyerSearchStates.entering_volume_min)

    elif action == "price":
        await callback.message.answer(
            "💰 Введите <b>минимальную цену</b> (₽)\n"
            "или 0 для любой:",
            reply_markup=kb_cancel_only(),
            parse_mode="HTML",
        )
        await state.set_state(BuyerSearchStates.entering_price_min)

    elif action == "reset":
        filters = {}
        await state.update_data(filters=filters)
        await callback.message.edit_reply_markup(
            reply_markup=kb_search_filters(filters)
        )
        await callback.answer("Фильтры сброшены")

    elif action == "search":
        await _do_search(callback.message, state, filters)

    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Ввод значений фильтров
# ─────────────────────────────────────────────────────────────────────────────

@router.message(BuyerSearchStates.entering_region)
async def step_filter_region(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _back_to_filters(message, state)
        return

    data = await state.get_data()
    filters = data.get("filters", {})
    filters["region"] = message.text.strip()
    await state.update_data(filters=filters)

    await message.answer(
        f"✅ Регион: <b>{filters['region']}</b>",
        parse_mode="HTML",
    )
    await _back_to_filters(message, state)


@router.message(BuyerSearchStates.entering_fkko_filter)
async def step_filter_fkko(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _back_to_filters(message, state)
        return

    data = await state.get_data()
    filters = data.get("filters", {})
    filters["fkko_name"] = message.text.strip()
    await state.update_data(filters=filters)

    await message.answer(
        f"✅ Тип отхода: <b>{filters['fkko_name']}</b>",
        parse_mode="HTML",
    )
    await _back_to_filters(message, state)


@router.message(BuyerSearchStates.entering_volume_min)
async def step_filter_volume_min(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _back_to_filters(message, state)
        return

    data = await state.get_data()
    filters = data.get("filters", {})

    val = validate_positive_number(message.text)
    if val is None and message.text.strip() != "0":
        await message.answer("❌ Введите число (или 0 для любого):")
        return

    filters["volume_min"] = val or 0
    await state.update_data(filters=filters)

    await message.answer(
        "📦 Введите <b>максимальный объём</b> (или 0 для любого):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(BuyerSearchStates.entering_volume_max)


@router.message(BuyerSearchStates.entering_volume_max)
async def step_filter_volume_max(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _back_to_filters(message, state)
        return

    data = await state.get_data()
    filters = data.get("filters", {})

    val = validate_positive_number(message.text)
    if val is None and message.text.strip() != "0":
        await message.answer("❌ Введите число (или 0 для любого):")
        return

    if val:
        filters["volume_max"] = val
    await state.update_data(filters=filters)
    await _back_to_filters(message, state)


@router.message(BuyerSearchStates.entering_price_min)
async def step_filter_price_min(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _back_to_filters(message, state)
        return

    data = await state.get_data()
    filters = data.get("filters", {})

    val = validate_positive_number(message.text)
    if val is None and message.text.strip() != "0":
        await message.answer("❌ Введите число (или 0 для любой):")
        return

    filters["price_min"] = val or 0
    await state.update_data(filters=filters)

    await message.answer(
        "💰 Введите <b>максимальную цену</b> (или 0 для любой):",
        reply_markup=kb_cancel_only(),
        parse_mode="HTML",
    )
    await state.set_state(BuyerSearchStates.entering_price_max)


@router.message(BuyerSearchStates.entering_price_max)
async def step_filter_price_max(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await _back_to_filters(message, state)
        return

    data = await state.get_data()
    filters = data.get("filters", {})

    val = validate_positive_number(message.text)
    if val is None and message.text.strip() != "0":
        await message.answer("❌ Введите число (или 0 для любой):")
        return

    if val:
        filters["price_max"] = val
    await state.update_data(filters=filters)
    await _back_to_filters(message, state)


async def _back_to_filters(message: Message, state: FSMContext) -> None:
    """Вернуться к экрану фильтров."""
    data = await state.get_data()
    filters = data.get("filters", {})
    await message.answer(
        "🔍 Фильтры обновлены. Нажмите 🔍 Найти для поиска:",
        reply_markup=kb_search_filters(filters),
    )
    await state.set_state(BuyerSearchStates.choosing_filter)


# ─────────────────────────────────────────────────────────────────────────────
# Выполнение поиска
# ─────────────────────────────────────────────────────────────────────────────

async def _do_search(message: Message, state: FSMContext, filters: dict) -> None:
    """Выполнить поиск и показать результаты."""
    searching_msg = await message.answer("🔍 Ищу подходящие лоты...")
    lots = await search_lots(filters)
    await searching_msg.delete()

    if not lots:
        await message.answer(
            "😔 По вашим фильтрам ничего не найдено.\n"
            "Попробуйте изменить параметры поиска.",
            reply_markup=kb_search_filters(filters),
        )
        return

    await state.update_data(search_results=lots, search_page=0)
    await message.answer(
        f"✅ Найдено <b>{len(lots)}</b> лотов:",
        parse_mode="HTML",
    )
    await _show_search_result(message, state, lots, 0)
    await state.set_state(BuyerSearchStates.viewing_results)


async def _show_search_result(
    message: Message, state: FSMContext, lots: list, page: int
) -> None:
    """Показать один лот из результатов поиска."""
    lot = lots[page]
    card = format_lot_card(lot)
    total = len(lots)

    if lot.get("photo_file_id"):
        await message.answer_photo(
            photo=lot["photo_file_id"],
            caption=card,
            reply_markup=kb_lot_actions_buyer(lot["id"]),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            card,
            reply_markup=kb_lot_actions_buyer(lot["id"]),
            parse_mode="HTML",
        )

    if total > 1:
        await message.answer(
            f"Лот {page + 1} из {total}",
            reply_markup=kb_lots_navigation(page, total),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Навигация по результатам поиска
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(BuyerSearchStates.viewing_results, F.data.startswith("lots_nav:"))
async def cb_search_nav(callback: CallbackQuery, state: FSMContext) -> None:
    page_str = callback.data.split(":")[1]
    if page_str == "noop":
        await callback.answer()
        return

    page = int(page_str)
    data = await state.get_data()
    lots = data.get("search_results", [])

    if not lots or page < 0 or page >= len(lots):
        await callback.answer("Нет данных", show_alert=True)
        return

    await state.update_data(search_page=page)
    lot = lots[page]
    card = format_lot_card(lot)

    await callback.message.edit_text(
        f"{card}\n\nЛот {page + 1} из {len(lots)}",
        reply_markup=kb_lots_navigation(page, len(lots)),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Покупка лота — оформление заявки
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lot_buy:"))
async def cb_lot_buy(callback: CallbackQuery, state: FSMContext) -> None:
    lot_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(callback.from_user.id)

    if not user or user["role"] != ROLE_BUYER:
        await callback.answer("⛔ Только покупатели могут оформлять заявки", show_alert=True)
        return

    lot = await get_lot_by_id(lot_id)
    if not lot or lot["status"] != "active":
        await callback.answer("❌ Лот недоступен или уже продан", show_alert=True)
        return

    # Рассчитываем стоимость перевозки
    transport_info = await calculate_lot_transport_info(lot)

    # Сохраняем данные для подтверждения
    await state.update_data(
        purchase_lot_id=lot_id,
        purchase_distance=transport_info.get("distance_km"),
        purchase_transport_cost=transport_info.get("transport_cost"),
    )

    # Формируем сообщение с деталями
    card = format_lot_card(lot)
    lines = [
        f"🛒 <b>Оформление заявки</b>\n",
        card,
        "",
    ]

    if transport_info.get("distance_km"):
        lines.append(
            format_transport_cost_breakdown(
                transport_info["distance_km"],
                lot["volume"],
                lot["unit"],
                transport_info["transport_cost"],
            )
        )
    else:
        lines.append("ℹ️ Стоимость перевозки будет рассчитана после назначения перевозчика.")

    lines.append("\n<b>Подтвердить оформление заявки?</b>")

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=kb_confirm_or_cancel(),
        parse_mode="HTML",
    )
    await state.set_state(BuyerSearchStates.confirming_purchase)
    await callback.answer()


@router.message(BuyerSearchStates.confirming_purchase)
async def step_confirm_purchase(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Оформление отменено.", reply_markup=kb_buyer_main())
        return

    if message.text != "✅ Подтвердить":
        await message.answer(
            "Нажмите ✅ Подтвердить или ❌ Отмена:",
            reply_markup=kb_confirm_or_cancel(),
        )
        return

    data = await state.get_data()
    user = await get_user_by_tg_id(message.from_user.id)
    lot_id = data["purchase_lot_id"]

    # Проверяем статус лота
    lot = await get_lot_by_id(lot_id)
    if not lot or lot["status"] != "active":
        await message.answer(
            "❌ Лот недоступен или уже продан.",
            reply_markup=kb_buyer_main(),
        )
        return

    try:
        # Создаём заявку на перевозку
        req_id = await create_transport_request({
            "lot_id": lot_id,
            "buyer_id": user["id"],
            "distance_km": data.get("purchase_distance"),
            "transport_cost": data.get("purchase_transport_cost"),
        })

        # Резервируем лот
        await update_lot_status(lot_id, "reserved")

        await state.clear()

        await message.answer(
            f"✅ <b>Заявка #{req_id} оформлена!</b>\n\n"
            f"Ожидайте назначения перевозчика.\n"
            f"Вы можете отслеживать статус в разделе 🛒 Мои покупки.",
            reply_markup=kb_buyer_main(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка при создании заявки: %s", e)
        await message.answer(
            "❌ Ошибка при оформлении заявки. Попробуйте позже.",
            reply_markup=kb_buyer_main(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Мои покупки — список заявок
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "🛒 Мои покупки")
async def cmd_my_purchases(message: Message, state: FSMContext) -> None:
    user = await _require_buyer(message)
    if not user:
        return

    requests = await get_requests_for_buyer(user["id"])
    if not requests:
        await message.answer(
            "📭 У вас пока нет оформленных заявок.\n"
            "Нажмите 🔍 Найти отходы чтобы найти подходящий лот.",
            reply_markup=kb_buyer_main(),
        )
        return

    await state.update_data(my_requests=requests, req_page=0)
    await _show_request_page(message, state, requests, 0)


async def _show_request_page(
    message: Message, state: FSMContext, requests: list, page: int
) -> None:
    req = requests[page]
    total = len(requests)

    # Получаем данные лота
    lot = await get_lot_by_id(req["lot_id"])
    if not lot:
        await message.answer(f"⚠️ Лот для заявки #{req['id']} не найден.")
        return

    # Статусы на русском
    status_map = {
        "pending": "⏳ Ожидает перевозчика",
        "accepted": "✅ Перевозчик назначен",
        "in_transit": "🚛 В пути",
        "delivered": "📦 Доставлено",
        "completed": "✔️ Завершено",
        "cancelled": "❌ Отменено",
    }

    lines = [
        f"🛒 <b>Заявка #{req['id']}</b>",
        f"",
        f"♻️ {lot['fkko_name']}",
        f"📦 {lot['volume']} {lot['unit']}",
        f"💰 {lot['price']:,.0f} ₽ {lot['price_format']}",
        f"📍 Откуда: {lot.get('address_from', '—')}",
        f"🏁 Куда: {lot.get('address_to', '—')}",
        f"",
        f"🔖 Статус: <b>{status_map.get(req['status'], req['status'])}</b>",
    ]
    if req.get("distance_km"):
        lines.append(f"📏 Расстояние: {req['distance_km']} км")
    if req.get("transport_cost"):
        lines.append(f"🚛 Стоимость перевозки: {req['transport_cost']:,.0f} ₽")
    lines.append(f"📅 Создана: {req['created_at'][:10]}")

    await message.answer(
        "\n".join(lines),
        reply_markup=kb_request_actions_buyer(req["id"], req["status"]),
        parse_mode="HTML",
    )

    if total > 1:
        await message.answer(
            f"Заявка {page + 1} из {total}",
            reply_markup=kb_lots_navigation(page, total),
        )


# ─────────────────────────────────────────────────────────────────────────────
# История статусов заявки
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("req_history:"))
async def cb_req_history(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split(":")[1])
    history = await get_status_history(req_id)

    if not history:
        await callback.answer("История статусов пуста", show_alert=True)
        return

    status_map = {
        "pending": "⏳ Ожидает перевозчика",
        "accepted": "✅ Перевозчик назначен",
        "in_transit": "🚛 В пути",
        "delivered": "📦 Доставлено",
        "completed": "✔️ Завершено",
        "cancelled": "❌ Отменено",
    }

    lines = [f"📊 <b>История статусов заявки #{req_id}:</b>", ""]
    for entry in history:
        old = status_map.get(entry.get("old_status", ""), entry.get("old_status", "—"))
        new = status_map.get(entry["new_status"], entry["new_status"])
        dt = entry["created_at"][:16].replace("T", " ")
        lines.append(f"🕐 {dt}")
        lines.append(f"   {old} → {new}")
        if entry.get("comment"):
            lines.append(f"   💬 {entry['comment']}")
        lines.append("")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Подтверждение получения груза покупателем
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("req_confirm:"))
async def cb_req_confirm(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(callback.from_user.id)

    req = await get_transport_request_by_id(req_id)
    if not req or req["buyer_id"] != user["id"]:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if req["status"] != "delivered":
        await callback.answer("❌ Груз ещё не доставлен", show_alert=True)
        return

    await update_request_status(
        req_id, "completed",
        changed_by=user["id"],
        comment="Покупатель подтвердил получение",
    )
    await update_lot_status(req["lot_id"], "completed")

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ <b>Получение подтверждено!</b>\n"
        f"Заявка #{req_id} завершена. Спасибо за использование WasteBot!",
        reply_markup=kb_buyer_main(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Документы покупателя
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "📄 Мои документы")
async def cmd_my_docs(message: Message, state: FSMContext) -> None:
    user = await _require_buyer(message)
    if not user:
        return

    requests = await get_requests_for_buyer(user["id"])
    if not requests:
        await message.answer(
            "📭 У вас нет заявок с документами.",
            reply_markup=kb_buyer_main(),
        )
        return

    lines = ["📄 <b>Ваши документы по заявкам:</b>", ""]
    for req in requests:
        docs = await get_documents_by_request(req["id"])
        if docs:
            lines.append(f"📋 Заявка #{req['id']}:")
            for doc in docs:
                doc_type_label = {
                    "transfer_act": "Акт приёма-передачи",
                    "waybill": "Транспортная накладная",
                }.get(doc["doc_type"], doc["doc_type"])
                lines.append(f"  • {doc_type_label} ({doc['created_at'][:10]})")
            lines.append("")

    if len(lines) == 2:
        await message.answer(
            "📭 Документы пока не сформированы.",
            reply_markup=kb_buyer_main(),
        )
        return

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb_buyer_main())


@router.callback_query(F.data.startswith("req_docs:"))
async def cb_req_docs(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split(":")[1])
    docs = await get_documents_by_request(req_id)

    if not docs:
        await callback.message.answer(
            f"📭 Документы для заявки #{req_id} ещё не сформированы.",
            reply_markup=kb_generate_docs(req_id),
        )
    else:
        lines = [f"📄 <b>Документы по заявке #{req_id}:</b>", ""]
        for doc in docs:
            doc_type_label = {
                "transfer_act": "📋 Акт приёма-передачи",
                "waybill": "🚛 Транспортная накладная",
            }.get(doc["doc_type"], doc["doc_type"])
            lines.append(f"{doc_type_label}")
            lines.append(f"  Создан: {doc['created_at'][:10]}")

        await callback.message.answer(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=kb_generate_docs(req_id),
        )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Мои документы
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "📄 Мои документы")
async def cmd_my_documents(message: Message) -> None:
    user = await _require_buyer(message)
    if not user:
        return

    requests = await get_requests_for_buyer(user["id"])
    if not requests:
        await message.answer(
            "📭 У вас пока нет документов.",
            reply_markup=kb_buyer_main(),
        )
        return

    # Собираем все документы по заявкам
    all_docs = []
    for req in requests:
        docs = await get_documents_by_request(req["id"])
        for doc in docs:
            doc["req_id"] = req["id"]
            all_docs.append(doc)

    if not all_docs:
        await message.answer(
            "📭 У вас пока нет документов.",
            reply_markup=kb_buyer_main(),
        )
        return

    text = "📄 <b>Ваши документы:</b>\n\n"
    for doc in all_docs[:10]:
        doc_type_label = {
            "transfer_act": "📋 Акт приёма-передачи",
            "waybill": "🚛 Транспортная накладная",
        }.get(doc["doc_type"], doc["doc_type"])
        text += f"{doc_type_label}\n"
        text += f"   Заявка #{doc['req_id']} | {doc['created_at'][:10]}\n\n"

    await message.answer(text, parse_mode="HTML", reply_markup=kb_buyer_main())
