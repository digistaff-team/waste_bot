"""
Р“РµРѕСЃРµСЂРІРёСЃ: РіРµРѕРєРѕРґРёСЂРѕРІР°РЅРёРµ Р°РґСЂРµСЃРѕРІ Рё СЂР°СЃС‡С‘С‚ СЂР°СЃСЃС‚РѕСЏРЅРёР№.
РСЃРїРѕР»СЊР·СѓРµС‚ РЇРЅРґРµРєСЃ.Р“РµРѕРєРѕРґРµСЂ (РµСЃР»Рё С‚РѕРєРµРЅ Р·Р°РґР°РЅ) РёР»Рё geopy (Nominatim).
"""
import aiohttp
import asyncio
import logging
import math
from typing import Optional
try:
    from geopy.distance import geodesic
except ImportError:
    geodesic = None

from config import YANDEX_GEO_TOKEN

logger = logging.getLogger(__name__)

YANDEX_GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"

# РљРµС€ РґР»СЏ РіРµРѕРєРѕРґРёСЂРѕРІР°РЅРёСЏ (Р°РґСЂРµСЃ -> РєРѕРѕСЂРґРёРЅР°С‚С‹)
_geocode_cache: dict[str, Optional[tuple[float, float]]] = {}
_cache_lock = asyncio.Lock()


async def geocode_address(address: str) -> Optional[tuple[float, float]]:
    """
    Р“РµРѕРєРѕРґРёСЂРѕРІР°РЅРёРµ Р°РґСЂРµСЃР° в†’ (lat, lon).
    РЎРЅР°С‡Р°Р»Р° РїСЂРѕР±СѓРµС‚ РЇРЅРґРµРєСЃ.Р“РµРѕРєРѕРґРµСЂ, РїСЂРё РѕС€РёР±РєРµ вЂ” Nominatim.
    Р’РѕР·РІСЂР°С‰Р°РµС‚ None РµСЃР»Рё Р°РґСЂРµСЃ РЅРµ РЅР°Р№РґРµРЅ.
    """
    # РџСЂРѕРІРµСЂСЏРµРј РєРµС€
    async with _cache_lock:
        if address in _geocode_cache:
            return _geocode_cache[address]
    
    result = None
    if YANDEX_GEO_TOKEN:
        result = await _geocode_yandex(address)
        if result:
            async with _cache_lock:
                _geocode_cache[address] = result
            return result

    result = await _geocode_nominatim(address)
    
    # РљРµС€РёСЂСѓРµРј СЂРµР·СѓР»СЊС‚Р°С‚
    async with _cache_lock:
        _geocode_cache[address] = result
    
    return result


async def _geocode_yandex(address: str) -> Optional[tuple[float, float]]:
    """Р“РµРѕРєРѕРґРёСЂРѕРІР°РЅРёРµ С‡РµСЂРµР· РЇРЅРґРµРєСЃ.Р“РµРѕРєРѕРґРµСЂ."""
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
        logger.error("РћС€РёР±РєР° РЇРЅРґРµРєСЃ.Р“РµРѕРєРѕРґРµСЂ: %s", e)
        return None


async def _geocode_nominatim(address: str) -> Optional[tuple[float, float]]:
    """Р“РµРѕРєРѕРґРёСЂРѕРІР°РЅРёРµ С‡РµСЂРµР· OpenStreetMap Nominatim (Р±РµСЃРїР»Р°С‚РЅРѕ, Р±РµР· С‚РѕРєРµРЅР°)."""
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
        logger.error("РћС€РёР±РєР° Nominatim: %s", e)
        return None


def calculate_distance_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """Р Р°СЃС‡С‘С‚ СЂР°СЃСЃС‚РѕСЏРЅРёСЏ РјРµР¶РґСѓ РґРІСѓРјСЏ С‚РѕС‡РєР°РјРё (РєРј) РїРѕ С„РѕСЂРјСѓР»Рµ Haversine."""
    if geodesic is not None:
        return round(geodesic((lat1, lon1), (lat2, lon2)).km, 1)

    # Fallback when geopy isn't installed.
    r_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r_km * c, 1)


async def get_address_with_coords(address: str) -> dict:
    """
    Р“РµРѕРєРѕРґРёСЂРѕРІР°РЅРёРµ Р°РґСЂРµСЃР° СЃ РІРѕР·РІСЂР°С‚РѕРј РїРѕР»РЅРѕРіРѕ СЂРµР·СѓР»СЊС‚Р°С‚Р°.
    Р’РѕР·РІСЂР°С‰Р°РµС‚: {"address": str, "lat": float|None, "lon": float|None}
    """
    coords = await geocode_address(address)
    if coords:
        return {"address": address, "lat": coords[0], "lon": coords[1]}
    return {"address": address, "lat": None, "lon": None}


def clear_geocode_cache() -> None:
    """РћС‡РёСЃС‚РєР° РєРµС€Р° РіРµРѕРєРѕРґРёСЂРѕРІР°РЅРёСЏ."""
    global _geocode_cache
    _geocode_cache.clear()
    logger.info("РљРµС€ РіРµРѕРєРѕРґРёСЂРѕРІР°РЅРёСЏ РѕС‡РёС‰РµРЅ")

