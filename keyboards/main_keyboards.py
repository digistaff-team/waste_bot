"""
Все клавиатуры бота: главные меню ролей, inline-кнопки для лотов и заявок.
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from config import (
    ROLE_SELLER, ROLE_BUYER, ROLE_CARRIER,
    UNIT_TON, UNIT_M3,
    PRICE_FORMAT_PER_TON, PRICE_FORMAT_PER_TRIP,
    CONDITION_DELIVERY, CONDITION_PICKUP,
)


# ─────────────────────────────────────────────────────────────────────────────
# Выбор роли при регистрации
# ─────────────────────────────────────────────────────────────────────────────

def kb_choose_role() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🏭 Продавец")
    builder.button(text="🛒 Покупатель")
    builder.button(text="🚛 Перевозчик")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ─────────────────────────────────────────────────────────────────────────────
# Главные меню по ролям
# ─────────────────────────────────────────────────────────────────────────────

def kb_seller_main() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Разместить отход")
    builder.button(text="📋 Мои лоты")
    builder.button(text="📊 Мои сделки")
    builder.button(text="👤 Мой профиль")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def kb_buyer_main() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 Найти отходы")
    builder.button(text="🛒 Мои покупки")
    builder.button(text="📄 Мои документы")
    builder.button(text="👤 Мой профиль")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def kb_carrier_main() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚛 Доступные заявки")
    builder.button(text="📋 Мои перевозки")
    builder.button(text="📄 Документы")
    builder.button(text="👤 Мой профиль")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def kb_main_by_role(role: str) -> ReplyKeyboardMarkup:
    """Вернуть главное меню по роли пользователя."""
    if role == ROLE_SELLER:
        return kb_seller_main()
    elif role == ROLE_BUYER:
        return kb_buyer_main()
    elif role == ROLE_CARRIER:
        return kb_carrier_main()
    return kb_seller_main()


# ─────────────────────────────────────────────────────────────────────────────
# Клавиатуры для создания лота
# ─────────────────────────────────────────────────────────────────────────────

def kb_choose_unit() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=f"⚖️ {UNIT_TON}")
    builder.button(text=f"📦 {UNIT_M3}")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_choose_price_format() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=f"💰 {PRICE_FORMAT_PER_TON}")
    builder.button(text=f"🚛 {PRICE_FORMAT_PER_TRIP}")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_choose_condition() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=f"🚚 {CONDITION_DELIVERY}")
    builder.button(text=f"🏭 {CONDITION_PICKUP}")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_skip_or_cancel() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="⏭ Пропустить")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_confirm_or_cancel() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Подтвердить")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_cancel_only() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ─────────────────────────────────────────────────────────────────────────────
# Inline-клавиатуры для ФККО
# ─────────────────────────────────────────────────────────────────────────────

def kb_fkko_popular(items: list[dict]) -> InlineKeyboardMarkup:
    """Кнопки популярных категорий ФККО."""
    builder = InlineKeyboardBuilder()
    for item in items:
        # Обрезаем название до 40 символов для кнопки
        short_name = item["name"][:40] + ("…" if len(item["name"]) > 40 else "")
        builder.button(
            text=short_name,
            callback_data=f"fkko:{item['code']}",
        )
    builder.button(text="🔍 Поиск по названию", callback_data="fkko:search")
    builder.adjust(1)
    return builder.as_markup()


def kb_fkko_search_results(items: list[dict]) -> InlineKeyboardMarkup:
    """Результаты поиска ФККО."""
    builder = InlineKeyboardBuilder()
    for item in items:
        short_name = item["name"][:38] + ("…" if len(item["name"]) > 38 else "")
        builder.button(
            text=f"{item['code']} — {short_name}",
            callback_data=f"fkko:{item['code']}",
        )
    builder.button(text="🔄 Новый поиск", callback_data="fkko:search")
    builder.button(text="❌ Отмена", callback_data="fkko:cancel")
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────────────
# Inline-клавиатуры для лотов
# ─────────────────────────────────────────────────────────────────────────────

def kb_lot_actions_seller(lot_id: int) -> InlineKeyboardMarkup:
    """Действия продавца с лотом."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Снять с публикации", callback_data=f"lot_cancel:{lot_id}")
    builder.button(text="📄 Документы", callback_data=f"lot_docs:{lot_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_lot_actions_buyer(lot_id: int) -> InlineKeyboardMarkup:
    """Действия покупателя с лотом."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить / Оформить заявку", callback_data=f"lot_buy:{lot_id}")
    builder.button(text="◀️ Назад к списку", callback_data="lots:back")
    builder.adjust(1)
    return builder.as_markup()


def kb_lots_navigation(current: int, total: int) -> InlineKeyboardMarkup:
    """Навигация по списку лотов."""
    builder = InlineKeyboardBuilder()
    if current > 0:
        builder.button(text="◀️ Назад", callback_data=f"lots_nav:{current - 1}")
    builder.button(text=f"{current + 1}/{total}", callback_data="lots_nav:noop")
    if current < total - 1:
        builder.button(text="Вперёд ▶️", callback_data=f"lots_nav:{current + 1}")
    builder.adjust(3)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────────────
# Inline-клавиатуры для заявок на перевозку
# ─────────────────────────────────────────────────────────────────────────────

def kb_request_actions_carrier(req_id: int, status: str) -> InlineKeyboardMarkup:
    """Действия перевозчика с заявкой."""
    builder = InlineKeyboardBuilder()
    if status == "pending":
        builder.button(text="✅ Принять заявку", callback_data=f"req_accept:{req_id}")
    elif status == "accepted":
        builder.button(text="🚛 Груз забран (в пути)", callback_data=f"req_pickup:{req_id}")
    elif status == "in_transit":
        builder.button(text="✔️ Груз доставлен", callback_data=f"req_delivered:{req_id}")
    builder.button(text="📄 Документы", callback_data=f"req_docs:{req_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_request_actions_buyer(req_id: int, status: str) -> InlineKeyboardMarkup:
    """Действия покупателя с заявкой."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 История статусов", callback_data=f"req_history:{req_id}")
    builder.button(text="📄 Документы", callback_data=f"req_docs:{req_id}")
    if status == "delivered":
        builder.button(text="✅ Подтвердить получение", callback_data=f"req_confirm:{req_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────────────
# Inline-клавиатуры для документов
# ─────────────────────────────────────────────────────────────────────────────

def kb_generate_docs(req_id: int) -> InlineKeyboardMarkup:
    """Меню генерации документов."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Акт приёма-передачи", callback_data=f"doc_act:{req_id}")
    builder.button(text="🚛 Транспортная накладная", callback_data=f"doc_waybill:{req_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────────────
# Фильтры поиска (Покупатель)
# ─────────────────────────────────────────────────────────────────────────────

def kb_search_filters(filters: dict) -> InlineKeyboardMarkup:
    """Меню настройки фильтров поиска."""
    builder = InlineKeyboardBuilder()

    region_label = f"📍 Регион: {filters.get('region', 'любой')}"
    fkko_label = f"♻️ Тип отхода: {filters.get('fkko_name', 'любой')[:20] if filters.get('fkko_name') else 'любой'}"
    vol_min = filters.get("volume_min", "")
    vol_max = filters.get("volume_max", "")
    vol_label = f"📦 Объём: {vol_min or '0'}–{vol_max or '∞'} т"
    price_min = filters.get("price_min", "")
    price_max = filters.get("price_max", "")
    price_label = f"💰 Цена: {price_min or '0'}–{price_max or '∞'} ₽"

    builder.button(text=region_label, callback_data="filter:region")
    builder.button(text=fkko_label, callback_data="filter:fkko")
    builder.button(text=vol_label, callback_data="filter:volume")
    builder.button(text=price_label, callback_data="filter:price")
    builder.button(text="🔍 Найти", callback_data="filter:search")
    builder.button(text="🔄 Сбросить фильтры", callback_data="filter:reset")
    builder.adjust(1)
    return builder.as_markup()
