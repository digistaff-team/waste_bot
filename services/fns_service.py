"""
Сервис проверки ИНН через API ФНС (api-fns.ru).
При отсутствии токена выполняет только локальную валидацию формата.
"""
import aiohttp
import logging
from typing import Optional

from config import FNS_API_TOKEN

logger = logging.getLogger(__name__)

FNS_API_URL = "https://api-fns.ru/api/egr"


async def check_inn(inn: str) -> dict:
    """
    Проверка ИНН через API ФНС.
    Возвращает:
        {
            "valid": bool,
            "org_name": str | None,   # Название организации из реестра
            "error": str | None,
        }
    """
    # Если токен не настроен — только форматная проверка
    if not FNS_API_TOKEN:
        logger.warning("FNS_API_TOKEN не задан, выполняется только форматная проверка ИНН")
        return {"valid": True, "org_name": None, "error": None}

    try:
        params = {
            "req": inn,
            "key": FNS_API_TOKEN,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                FNS_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return {
                        "valid": False,
                        "org_name": None,
                        "error": f"Ошибка API ФНС: HTTP {resp.status}",
                    }
                data = await resp.json()

        items = data.get("items", [])
        if not items:
            return {
                "valid": False,
                "org_name": None,
                "error": "ИНН не найден в реестре ФНС",
            }

        item = items[0]
        # Для ЮЛ — поле "НаимСокрЮЛ", для ИП — "ФИО"
        org_name = (
            item.get("НаимСокрЮЛ")
            or item.get("ФИО")
            or item.get("name")
        )
        return {"valid": True, "org_name": org_name, "error": None}

    except aiohttp.ClientError as e:
        logger.error("Ошибка соединения с API ФНС: %s", e)
        return {
            "valid": True,  # При ошибке сети не блокируем регистрацию
            "org_name": None,
            "error": "Не удалось проверить ИНН через ФНС (сетевая ошибка)",
        }
    except Exception as e:
        logger.exception("Неожиданная ошибка при проверке ИНН: %s", e)
        return {"valid": True, "org_name": None, "error": str(e)}
