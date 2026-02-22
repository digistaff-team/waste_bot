"""
Геосервис: геокодирование адресов и расчёт расстояний.
Использует Яндекс.Геокодер (если токен задан) или geopy (Nominatim).
"""
import aiohttp
import logging
from typing import Optional
from geopy.distance import geodesic

from config import YANDEX_GEO_TOKEN

logger = logging.getLogger(__name__)

YANDEX_GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"


async def geocode_address(address: str) -> Optional[tuple[float, float]]:
    """
    Геокодирование адреса → (lat, lon).
    Сначала пробует Яндекс.Геокодер, при ошибке — Nominatim.
    Возвращает None если адрес не найден.
    """
    if YANDEX_GEO_TOKEN:
        result = await _geocode_yandex(address)
        if result:
            return result

    return await _geocode_nominatim(address)


async def _geocode_yandex(address: str) -> Optional[tuple[float, float]]:
    """Геокодирование через Яндекс.Геокодер."""
    try:
        params = {
            "apikey": YANDEX_GEO_TOKEN,
            "geocode": address,
            "format": "json",
            "results": 1,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                YANDEX_GEOCODER_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        features = (
            data.get("response", {})
            .get("GeoObjectCollection", {})
            .get("featureMember", [])
        )
        if not features:
            return None

        pos = (
            features[0]
            .get("GeoObject", {})
            .get("Point", {})
            .get("pos", "")
        )
        if not pos:
            return None

        lon_str, lat_str = pos.split()
        return float(lat_str), float(lon_str)

    except Exception as e:
        logger.error("Ошибка Яндекс.Геокодер: %s", e)
        return None


async def _geocode_nominatim(address: str) -> Optional[tuple[float, float]]:
    """Геокодирование через OpenStreetMap Nominatim (бесплатно, без токена)."""
    try:
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "accept-language": "ru",
        }
        headers = {"User-Agent": "WasteBot/1.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        if not data:
            return None

        return float(data[0]["lat"]), float(data[0]["lon"])

    except Exception as e:
        logger.error("Ошибка Nominatim: %s", e)
        return None


def calculate_distance_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """Расчёт расстояния между двумя точками (км) по формуле Haversine."""
    return round(geodesic((lat1, lon1), (lat2, lon2)).km, 1)


async def get_address_with_coords(address: str) -> dict:
    """
    Геокодирование адреса с возвратом полного результата.
    Возвращает: {"address": str, "lat": float|None, "lon": float|None}
    """
    coords = await geocode_address(address)
    if coords:
        return {"address": address, "lat": coords[0], "lon": coords[1]}
    return {"address": address, "lat": None, "lon": None}
