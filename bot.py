"""
РўРѕС‡РєР° РІС…РѕРґР° WasteBot.
РРЅРёС†РёР°Р»РёР·РёСЂСѓРµС‚ Р±РѕС‚Р°, СЂРµРіРёСЃС‚СЂРёСЂСѓРµС‚ СЂРѕСѓС‚РµСЂС‹, Р·Р°РїСѓСЃРєР°РµС‚ polling.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, USE_REDIS, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
from models.database import init_db
from handlers import registration, seller, buyer, carrier, common

# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# РќР°СЃС‚СЂРѕР№РєР° Р»РѕРіРёСЂРѕРІР°РЅРёСЏ
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("waste_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def get_storage():
    """РЎРѕР·РґР°РЅРёРµ С…СЂР°РЅРёР»РёС‰Р° СЃРѕСЃС‚РѕСЏРЅРёР№ (Redis РёР»Рё Memory)."""
    if USE_REDIS:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            storage = RedisStorage(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            )
            # РџСЂРѕРІРµСЂСЏРµРј СЃРѕРµРґРёРЅРµРЅРёРµ
            await storage.get_state()
            logger.info(f"FSM С…СЂР°РЅРёР»РёС‰Рµ: Redis ({REDIS_HOST}:{REDIS_PORT})")
            return storage
        except Exception as e:
            logger.warning(f"РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє Redis: {e}. РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ MemoryStorage.")
    return MemoryStorage()


async def main() -> None:
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN РЅРµ Р·Р°РґР°РЅ! РЈРєР°Р¶РёС‚Рµ С‚РѕРєРµРЅ РІ С„Р°Р№Р»Рµ .env")
        sys.exit(1)

    # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ Р±Р°Р·С‹ РґР°РЅРЅС‹С…
    logger.info("РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ Р±Р°Р·С‹ РґР°РЅРЅС‹С…...")
    await init_db()
    logger.info("Р‘Р°Р·Р° РґР°РЅРЅС‹С… РіРѕС‚РѕРІР°.")

    # Р’С‹Р±РѕСЂ С…СЂР°РЅРёР»РёС‰Р° РґР»СЏ FSM
    storage = await get_storage()

    # РЎРѕР·РґР°РЅРёРµ Р±РѕС‚Р° Рё РґРёСЃРїРµС‚С‡РµСЂР°
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # в”Ђв”Ђ Р РµРіРёСЃС‚СЂР°С†РёСЏ СЂРѕСѓС‚РµСЂРѕРІ (РїРѕСЂСЏРґРѕРє РІР°Р¶РµРЅ!) в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
    # 1. Р РµРіРёСЃС‚СЂР°С†РёСЏ вЂ” РїРµСЂРІРѕР№, С‚.Рє. СЃРѕРґРµСЂР¶РёС‚ /start
    dp.include_router(registration.router)
    # 2. РџСЂРѕРґР°РІРµС†
    dp.include_router(seller.router)
    # 3. РџРѕРєСѓРїР°С‚РµР»СЊ
    dp.include_router(buyer.router)
    # 4. РџРµСЂРµРІРѕР·С‡РёРє
    dp.include_router(carrier.router)
    # 5. РћР±С‰РёРµ С…СЌРЅРґР»РµСЂС‹ вЂ” РїРѕСЃР»РµРґРЅРёРјРё (СЃРѕРґРµСЂР¶РёС‚ fallback)
    dp.include_router(common.router)

    # РЈРґР°Р»СЏРµРј РІРµР±С…СѓРє РµСЃР»Рё Р±С‹Р» СѓСЃС‚Р°РЅРѕРІР»РµРЅ СЂР°РЅРµРµ
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("WasteBot Р·Р°РїСѓС‰РµРЅ. РћР¶РёРґР°РЅРёРµ СЃРѕРѕР±С‰РµРЅРёР№...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await storage.close()
        logger.info("WasteBot РѕСЃС‚Р°РЅРѕРІР»РµРЅ.")


if __name__ == "__main__":
    asyncio.run(main())

