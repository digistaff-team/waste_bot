"""
Хэндлер перевозчика: просмотр доступных заявок, принятие перевозки,
обновление статуса, генерация документов.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ROLE_CARRIER
from models.database import (
    get_user_by_tg_id, get_user_by_id, get_requests_for_carrier,
    get_transport_request_by_id, get_lot_by_id,
    update_request_status, update_lot_status,
    get_documents_by_request, save_document, update_document_tg_file_id,
)
from services.document_service import generate_transfer_act, generate_waybill
from utils.states import CarrierStates
from utils.helpers import format_transport_request
from keyboards.main_keyboards import (
    kb_carrier_main, kb_request_actions_carrier,
    kb_lots_navigation, kb_generate_docs,
)

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательная проверка роли
# ─────────────────────────────────────────────────────────────────────────────

async def _require_carrier(message: Message) -> dict | None:
    user = await get_user_by_tg_id(message.from_user.id)
    if not user or user["role"] != ROLE_CARRIER:
        await message.answer("⛔ Эта функция доступна только для перевозчиков.")
        return None
    return user


async def _get_request_parties(req: dict) -> tuple[dict | None, dict | None, dict | None]:
    """Получить лот, продавца и покупателя для заявки."""
    lot = await get_lot_by_id(req["lot_id"])
    if not lot:
        return None, None, None

    seller = await get_user_by_id(lot["seller_id"])
    buyer = await get_user_by_id(req["buyer_id"])

    return lot, seller, buyer
            buyer = dict(row) if row else None

    return lot, seller, buyer


# ─────────────────────────────────────────────────────────────────────────────
# Доступные заявки
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "🚛 Доступные заявки")
async def cmd_available_requests(message: Message, state: FSMContext) -> None:
    user = await _require_carrier(message)
    if not user:
        return

    requests = await get_requests_for_carrier(user["id"])
    # Показываем только pending (не принятые другими)
    pending = [r for r in requests if r["status"] == "pending"]

    if not pending:
        await message.answer(
            "📭 Нет доступных заявок на перевозку.\n"
            "Проверьте позже — новые заявки появляются по мере размещения лотов.",
            reply_markup=kb_carrier_main(),
        )
        return

    await state.update_data(carrier_requests=pending, carrier_req_page=0)
    await _show_carrier_request(message, state, pending, 0, user)


async def _show_carrier_request(
    message: Message,
    state: FSMContext,
    requests: list,
    page: int,
    carrier: dict,
) -> None:
    req = requests[page]
    total = len(requests)

    lot, seller, buyer = await _get_request_parties(req)
    if not lot or not seller or not buyer:
        await message.answer(f"⚠️ Данные заявки #{req['id']} недоступны.")
        return

    text = format_transport_request(req, lot, seller)
    text += f"\n\n🛒 Покупатель: {buyer['org_name']}"
    text += f"\n📞 Контакт: {buyer['phone']}"

    await message.answer(
        text,
        reply_markup=kb_request_actions_carrier(req["id"], req["status"]),
        parse_mode="HTML",
    )

    if total > 1:
        await message.answer(
            f"Заявка {page + 1} из {total}",
            reply_markup=kb_lots_navigation(page, total),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Мои перевозки (принятые заявки)
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "📋 Мои перевозки")
async def cmd_my_deliveries(message: Message, state: FSMContext) -> None:
    user = await _require_carrier(message)
    if not user:
        return

    all_requests = await get_requests_for_carrier(user["id"])
    # Только принятые этим перевозчиком
    my_requests = [r for r in all_requests if r.get("carrier_id") == user["id"]]

    if not my_requests:
        await message.answer(
            "📭 У вас пока нет принятых перевозок.\n"
            "Перейдите в 🚛 Доступные заявки чтобы принять заявку.",
            reply_markup=kb_carrier_main(),
        )
        return

    await state.update_data(my_deliveries=my_requests, delivery_page=0)
    await _show_my_delivery(message, state, my_requests, 0)


async def _show_my_delivery(
    message: Message, state: FSMContext, requests: list, page: int
) -> None:
    req = requests[page]
    total = len(requests)

    lot, seller, buyer = await _get_request_parties(req)
    if not lot or not seller or not buyer:
        await message.answer(f"⚠️ Данные заявки #{req['id']} недоступны.")
        return

    status_map = {
        "pending": "⏳ Ожидает перевозчика",
        "accepted": "✅ Принята",
        "in_transit": "🚛 В пути",
        "delivered": "📦 Доставлено",
        "completed": "✔️ Завершено",
        "cancelled": "❌ Отменено",
    }

    lines = [
        f"🚛 <b>Перевозка #{req['id']}</b>",
        f"🔖 Статус: <b>{status_map.get(req['status'], req['status'])}</b>",
        f"",
        f"♻️ {lot['fkko_name']}",
        f"📦 {lot['volume']} {lot['unit']}",
        f"📍 Откуда: {lot.get('address_from', '—')}",
        f"🏁 Куда: {lot.get('address_to', '—')}",
    ]
    if req.get("distance_km"):
        lines.append(f"📏 Расстояние: {req['distance_km']} км")
    if req.get("transport_cost"):
        lines.append(f"💰 Стоимость: {req['transport_cost']:,.0f} ₽")
    lines += [
        f"",
        f"🏭 Продавец: {seller['org_name']} ({seller['phone']})",
        f"🛒 Покупатель: {buyer['org_name']} ({buyer['phone']})",
        f"📅 Создана: {req['created_at'][:10]}",
    ]

    await message.answer(
        "\n".join(lines),
        reply_markup=kb_request_actions_carrier(req["id"], req["status"]),
        parse_mode="HTML",
    )

    if total > 1:
        await message.answer(
            f"Перевозка {page + 1} из {total}",
            reply_markup=kb_lots_navigation(page, total),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Принятие заявки перевозчиком
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("req_accept:"))
async def cb_req_accept(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(callback.from_user.id)

    if not user or user["role"] != ROLE_CARRIER:
        await callback.answer("⛔ Только перевозчики могут принимать заявки", show_alert=True)
        return

    req = await get_transport_request_by_id(req_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if req["status"] != "pending":
        await callback.answer("❌ Заявка уже принята другим перевозчиком", show_alert=True)
        return

    await update_request_status(
        req_id,
        "accepted",
        carrier_id=user["id"],
        changed_by=user["id"],
        comment=f"Принята перевозчиком {user['org_name']}",
    )

    await callback.message.edit_reply_markup(
        reply_markup=kb_request_actions_carrier(req_id, "accepted")
    )
    await callback.message.answer(
        f"✅ <b>Заявка #{req_id} принята!</b>\n\n"
        f"Свяжитесь с продавцом для организации забора груза.\n"
        f"Когда заберёте груз — нажмите «🚛 Груз забран».",
        reply_markup=kb_carrier_main(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Обновление статуса: груз забран (в пути)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("req_pickup:"))
async def cb_req_pickup(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(callback.from_user.id)

    req = await get_transport_request_by_id(req_id)
    if not req or req.get("carrier_id") != user["id"]:
        await callback.answer("❌ Нет доступа к этой заявке", show_alert=True)
        return

    if req["status"] != "accepted":
        await callback.answer("❌ Неверный статус заявки", show_alert=True)
        return

    await update_request_status(
        req_id, "in_transit",
        changed_by=user["id"],
        comment="Груз забран перевозчиком",
    )
    await update_lot_status(req["lot_id"], "in_transit")

    await callback.message.edit_reply_markup(
        reply_markup=kb_request_actions_carrier(req_id, "in_transit")
    )
    await callback.message.answer(
        f"🚛 <b>Статус обновлён: Груз в пути</b>\n"
        f"Заявка #{req_id}. Когда доставите — нажмите «✔️ Груз доставлен».",
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Обновление статуса: груз доставлен
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("req_delivered:"))
async def cb_req_delivered(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(callback.from_user.id)

    req = await get_transport_request_by_id(req_id)
    if not req or req.get("carrier_id") != user["id"]:
        await callback.answer("❌ Нет доступа к этой заявке", show_alert=True)
        return

    if req["status"] != "in_transit":
        await callback.answer("❌ Неверный статус заявки", show_alert=True)
        return

    await update_request_status(
        req_id, "delivered",
        changed_by=user["id"],
        comment="Груз доставлен перевозчиком",
    )

    await callback.message.edit_reply_markup(
        reply_markup=kb_request_actions_carrier(req_id, "delivered")
    )
    await callback.message.answer(
        f"📦 <b>Груз доставлен!</b>\n"
        f"Заявка #{req_id}. Ожидайте подтверждения от покупателя.\n\n"
        f"Вы можете сформировать документы:",
        reply_markup=kb_generate_docs(req_id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Генерация документов
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("doc_act:"))
async def cb_doc_act(callback: CallbackQuery) -> None:
    """Генерация акта приёма-передачи."""
    req_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(callback.from_user.id)

    req = await get_transport_request_by_id(req_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    lot, seller, buyer = await _get_request_parties(req)
    if not lot or not seller or not buyer:
        await callback.answer("❌ Данные для документа недоступны", show_alert=True)
        return

    # Получаем перевозчика
    carrier = None
    if req.get("carrier_id"):
        carrier = await get_user_by_id(req["carrier_id"])

    generating_msg = await callback.message.answer("📄 Генерирую акт приёма-передачи...")

    try:
        filepath = generate_transfer_act(req_id, lot, seller, buyer, carrier)

        # Сохраняем в БД
        doc_id = await save_document({
            "request_id": req_id,
            "doc_type": "transfer_act",
            "file_path": filepath,
        })

        # Отправляем файл
        with open(filepath, "rb") as f:
            sent = await callback.message.answer_document(
                document=f,
                filename=f"Акт_приёма-передачи_{req_id}.pdf",
                caption=f"📋 Акт приёма-передачи по заявке #{req_id}",
            )

        # Сохраняем tg_file_id для повторной отправки
        if sent.document:
            await update_document_tg_file_id(doc_id, sent.document.file_id)

        await generating_msg.delete()

    except Exception as e:
        logger.error("Ошибка генерации акта: %s", e)
        await generating_msg.delete()
        await callback.message.answer(
            "❌ Ошибка при генерации документа. Попробуйте позже."
        )

    await callback.answer()


@router.callback_query(F.data.startswith("doc_waybill:"))
async def cb_doc_waybill(callback: CallbackQuery) -> None:
    """Генерация транспортной накладной."""
    req_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(callback.from_user.id)

    req = await get_transport_request_by_id(req_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if not req.get("carrier_id"):
        await callback.answer(
            "❌ Накладная доступна только после назначения перевозчика",
            show_alert=True,
        )
        return

    lot, seller, buyer = await _get_request_parties(req)
    if not lot or not seller or not buyer:
        await callback.answer("❌ Данные для документа недоступны", show_alert=True)
        return

    # Получаем перевозчика
    carrier = await get_user_by_id(req["carrier_id"])

    if not carrier:
        await callback.answer("❌ Данные перевозчика не найдены", show_alert=True)
        return

    generating_msg = await callback.message.answer("📄 Генерирую транспортную накладную...")

    try:
        filepath = generate_waybill(
            req_id, lot, seller, buyer, carrier,
            distance_km=req.get("distance_km"),
            transport_cost=req.get("transport_cost"),
        )

        doc_id = await save_document({
            "request_id": req_id,
            "doc_type": "waybill",
            "file_path": filepath,
        })

        with open(filepath, "rb") as f:
            sent = await callback.message.answer_document(
                document=f,
                filename=f"Транспортная_накладная_{req_id}.pdf",
                caption=f"🚛 Транспортная накладная по заявке #{req_id}",
            )

        if sent.document:
            await update_document_tg_file_id(doc_id, sent.document.file_id)

        await generating_msg.delete()

    except Exception as e:
        logger.error("Ошибка генерации накладной: %s", e)
        await generating_msg.delete()
        await callback.message.answer(
            "❌ Ошибка при генерации документа. Попробуйте позже."
        )

    await callback.answer()
