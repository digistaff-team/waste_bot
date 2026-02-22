"""
Сервис подбора перевозчиков и расчёта стоимости перевозки.
"""
import logging
from typing import Optional

from config import (
    BASE_RATE_PER_KM_PER_TON,
    MIN_TRIP_COST,
    UNIT_TON,
)
from models.database import get_carriers_by_region
from services.geo_service import calculate_distance_km
from utils.helpers import m3_to_tons

logger = logging.getLogger(__name__)


def calculate_transport_cost(
    distance_km: float,
    volume: float,
    unit: str,
    waste_type: str = "default",
) -> float:
    """
    Расчёт стоимости перевозки.
    Формула: расстояние × объём_в_тоннах × базовая_ставка
    Минимальная стоимость: MIN_TRIP_COST
    """
    if unit == UNIT_TON:
        volume_tons = volume
    else:
        volume_tons = m3_to_tons(volume, waste_type)

    cost = distance_km * volume_tons * BASE_RATE_PER_KM_PER_TON
    return round(max(cost, MIN_TRIP_COST), 2)


async def find_carriers_for_lot(lot: dict) -> list[dict]:
    """
    Подбор перевозчиков для лота.
    Ищет перевозчиков по региону отправки.
    """
    region = ""
    if lot.get("address_from"):
        # Берём первое слово адреса как регион (упрощённо)
        region = lot["address_from"].split(",")[0].strip()

    carriers = await get_carriers_by_region(region)
    return carriers


async def calculate_lot_transport_info(lot: dict) -> dict:
    """
    Рассчитывает расстояние и стоимость перевозки для лота.
    Возвращает: {"distance_km": float|None, "transport_cost": float|None}
    """
    lat_from = lot.get("lat_from")
    lon_from = lot.get("lon_from")
    lat_to = lot.get("lat_to")
    lon_to = lot.get("lon_to")

    if not all([lat_from, lon_from, lat_to, lon_to]):
        return {"distance_km": None, "transport_cost": None}

    distance_km = calculate_distance_km(lat_from, lon_from, lat_to, lon_to)
    transport_cost = calculate_transport_cost(
        distance_km=distance_km,
        volume=lot["volume"],
        unit=lot["unit"],
        waste_type=lot.get("fkko_name", "default"),
    )

    return {"distance_km": distance_km, "transport_cost": transport_cost}


def format_transport_cost_breakdown(
    distance_km: float,
    volume: float,
    unit: str,
    cost: float,
) -> str:
    """Форматирование расчёта стоимости перевозки для отображения."""
    lines = [
        "📊 <b>Расчёт стоимости перевозки:</b>",
        f"📏 Расстояние: {distance_km} км",
        f"📦 Объём: {volume} {unit}",
        f"💰 Итого: <b>{cost:,.0f} ₽</b>",
        f"",
        f"<i>Ставка: {BASE_RATE_PER_KM_PER_TON} ₽/км/тонна</i>",
        f"<i>Минимальная стоимость рейса: {MIN_TRIP_COST:,.0f} ₽</i>",
    ]
    return "\n".join(lines)
