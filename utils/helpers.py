"""
Вспомогательные функции: конвертация единиц, форматирование, валидация.
"""
import re
from datetime import datetime
from typing import Optional

from config import (
    UNIT_TON, UNIT_M3,
    PRICE_FORMAT_PER_TON, PRICE_FORMAT_PER_TRIP,
    LOT_STATUS_LABELS, ROLE_LABELS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Валидация
# ─────────────────────────────────────────────────────────────────────────────

def validate_inn(inn: str) -> bool:
    """Базовая проверка формата ИНН (10 или 12 цифр)."""
    return bool(re.fullmatch(r"\d{10}|\d{12}", inn.strip()))


def validate_phone(phone: str) -> bool:
    """Проверка формата телефона."""
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    return bool(re.fullmatch(r"(\+7|8)\d{10}", cleaned))


def validate_email(email: str) -> bool:
    """Проверка формата email."""
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()))


def validate_date(date_str: str) -> Optional[datetime]:
    """Парсинг даты в формате ДД.ММ.ГГГГ. Возвращает datetime или None."""
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y")
    except ValueError:
        return None


def validate_positive_number(value: str) -> Optional[float]:
    """Парсинг положительного числа. Возвращает float или None."""
    try:
        num = float(value.replace(",", "."))
        return num if num > 0 else None
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Конвертация единиц измерения
# ─────────────────────────────────────────────────────────────────────────────

# Плотность типичных отходов (тонн/м³) — усреднённые значения
WASTE_DENSITY: dict[str, float] = {
    "макулатура": 0.15,
    "металлолом": 2.5,
    "пластик": 0.05,
    "стекло": 1.5,
    "резина": 0.6,
    "дерево": 0.5,
    "текстиль": 0.1,
    "default": 0.5,
}


def tons_to_m3(tons: float, waste_type: str = "default") -> float:
    """Конвертация тонн в м³ по плотности типа отхода."""
    density = WASTE_DENSITY.get(waste_type.lower(), WASTE_DENSITY["default"])
    return round(tons / density, 2)


def m3_to_tons(m3: float, waste_type: str = "default") -> float:
    """Конвертация м³ в тонны по плотности типа отхода."""
    density = WASTE_DENSITY.get(waste_type.lower(), WASTE_DENSITY["default"])
    return round(m3 * density, 2)


def convert_price(
    price: float,
    from_format: str,
    to_format: str,
    volume_tons: float,
) -> float:
    """
    Конвертация цены между форматами.
    from_format / to_format: PRICE_FORMAT_PER_TON | PRICE_FORMAT_PER_TRIP
    """
    if from_format == to_format:
        return price
    if from_format == PRICE_FORMAT_PER_TON and to_format == PRICE_FORMAT_PER_TRIP:
        return round(price * volume_tons, 2)
    if from_format == PRICE_FORMAT_PER_TRIP and to_format == PRICE_FORMAT_PER_TON:
        if volume_tons == 0:
            return 0.0
        return round(price / volume_tons, 2)
    return price


# ─────────────────────────────────────────────────────────────────────────────
# Форматирование
# ─────────────────────────────────────────────────────────────────────────────

def format_lot_card(lot: dict) -> str:
    """Форматирование карточки лота для отображения."""
    status_label = LOT_STATUS_LABELS.get(lot.get("status", ""), lot.get("status", ""))
    price = lot.get('price') or 0
    price_str = f"{price:,.0f} ₽ {lot.get('price_format', '')}"
    volume_str = f"{lot.get('volume', 0)} {lot.get('unit', '')}"

    # Дополнительная цена в другом формате
    volume_tons = lot.get("volume", 0)
    if lot.get("unit") != UNIT_TON:
        volume_tons = m3_to_tons(lot.get("volume", 0))

    price_format = lot.get('price_format', PRICE_FORMAT_PER_TON)
    if price_format == PRICE_FORMAT_PER_TON:
        alt_price = convert_price(price, PRICE_FORMAT_PER_TON, PRICE_FORMAT_PER_TRIP, volume_tons)
        alt_str = f"(≈ {alt_price:,.0f} ₽ за рейс)"
    else:
        alt_price = convert_price(price, PRICE_FORMAT_PER_TRIP, PRICE_FORMAT_PER_TON, volume_tons)
        alt_str = f"(≈ {alt_price:,.0f} ₽/тонна)"

    lines = [
        f"♻️ <b>{lot.get('fkko_name', 'Неизвестно')}</b>",
        f"📦 Объём: {volume_str}",
        f"💰 Цена: {price_str} {alt_str}",
        f"🚚 Условие: {lot.get('condition', 'Не указано')}",
    ]
    if lot.get("address_from"):
        lines.append(f"📍 Откуда: {lot['address_from']}")
    if lot.get("address_to"):
        lines.append(f"🏁 Куда: {lot['address_to']}")
    if lot.get("valid_until"):
        lines.append(f"📅 Актуален до: {lot['valid_until']}")
    lines.append(f"🔖 Статус: {status_label}")
    lines.append(f"🆔 Лот #{lot.get('id', '?')}")
    return "\n".join(lines)


def format_user_card(user: dict) -> str:
    """Форматирование карточки пользователя."""
    role_label = ROLE_LABELS.get(user.get("role", ""), user.get("role", ""))
    lines = [
        f"👤 <b>{user.get('org_name', 'Неизвестно')}</b>",
        f"🏷 Роль: {role_label}",
        f"📋 ИНН: {user.get('inn', 'Не указан')}",
        f"🌍 Регион: {user.get('region', 'Не указан')}",
        f"📞 Телефон: {user.get('phone', 'Не указан')}",
        f"📧 Email: {user.get('email', 'Не указан')}",
    ]
    if user.get("vehicle_types"):
        lines.append(f"🚛 Типы ТС: {user['vehicle_types']}")
    if user.get("capacity"):
        lines.append(f"⚖️ Грузоподъёмность: {user['capacity']} т")
    if user.get("carrier_regions"):
        lines.append(f"🗺 Регионы перевозок: {user['carrier_regions']}")
    return "\n".join(lines)


def format_transport_request(req: dict, lot: dict, seller: dict) -> str:
    """Форматирование заявки на перевозку."""
    transport_cost = req.get('transport_cost') or 0
    distance_km = req.get('distance_km') or '?'
    
    lines = [
        f"🚛 <b>Заявка на перевозку #{req.get('id', '?')}</b>",
        f"",
        f"♻️ Отход: {lot.get('fkko_name', 'Неизвестно')}",
        f"📦 Объём: {lot.get('volume', 0)} {lot.get('unit', '')}",
        f"📍 Откуда: {lot.get('address_from') or 'Не указан'}",
        f"🏁 Куда: {lot.get('address_to') or 'Не указан'}",
        f"📏 Расстояние: {distance_km} км",
        f"💰 Стоимость перевозки: {transport_cost:,.0f} ₽",
        f"",
        f"🏭 Продавец: {seller.get('org_name', 'Неизвестно')}",
        f"📞 Контакт: {seller.get('phone', 'Не указан')}",
    ]
    return "\n".join(lines)


def plural_form(n: int, one: str, few: str, many: str) -> str:
    """Склонение существительных по числу."""
    if 11 <= n % 100 <= 19:
        return many
    r = n % 10
    if r == 1:
        return one
    if 2 <= r <= 4:
        return few
    return many
