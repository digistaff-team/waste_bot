"""
Точка входа WasteBot.
Инициализирует бота, регистрирует роутеры, запускает polling.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from config import BOT_TOKEN, USE_REDIS, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
from models.database import init_db
from handlers import registration, seller, buyer, carrier, common

# ─────────────────────────────────────────────────────────────────────────────
# Настройка логирования
# ─────────────────────────────────────────────────────────────────────────────
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
    """Создание хранилища состояний (Redis или Memory)."""
    if USE_REDIS:
        try:
            storage = RedisStorage(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            )
            # Проверяем соединение
            await storage.get_state()
            logger.info(f"FSM хранилище: Redis ({REDIS_HOST}:{REDIS_PORT})")
            return storage
        except Exception as e:
            logger.warning(f"Не удалось подключиться к Redis: {e}. Используется MemoryStorage.")
    return MemoryStorage()


async def main() -> None:
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN не задан! Укажите токен в файле .env")
        sys.exit(1)

    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных готова.")

    # Выбор хранилища для FSM
    storage = await get_storage()

    # Создание бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # ── Регистрация роутеров (порядок важен!) ─────────────────────────────────
    # 1. Регистрация — первой, т.к. содержит /start
    dp.include_router(registration.router)
    # 2. Продавец
    dp.include_router(seller.router)
    # 3. Покупатель
    dp.include_router(buyer.router)
    # 4. Перевозчик
    dp.include_router(carrier.router)
    # 5. Общие хэндлеры — последними (содержит fallback)
    dp.include_router(common.router)

    # Удаляем вебхук если был установлен ранее
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("WasteBot запущен. Ожидание сообщений...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await storage.close()
        logger.info("WasteBot остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
