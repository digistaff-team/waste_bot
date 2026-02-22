"""
Vercel Serverless Function для обработки Telegram Webhooks.
"""
import os
import logging
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота (ленивая)
_bot = None
_dp = None


def get_bot_and_dp():
    """Ленивая инициализация бота и диспетчера."""
    global _bot, _dp
    
    if _bot is None:
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.fsm.storage.memory import MemoryStorage
        
        from config import BOT_TOKEN
        from models.database import init_db
        from handlers import registration, seller, buyer, carrier, common
        
        # Создание бота и диспетчера
        _bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        _dp = Dispatcher(storage=MemoryStorage())
        
        # Регистрация роутеров
        _dp.include_router(registration.router)
        _dp.include_router(seller.router)
        _dp.include_router(buyer.router)
        _dp.include_router(carrier.router)
        _dp.include_router(common.router)
    
    return _bot, _dp


async def handle_webhook(update: dict):
    """Обработка входящего обновления от Telegram."""
    from aiogram.types import Update
    from models.database import init_db
    
    bot, dp = get_bot_and_dp()
    
    # Инициализация БД при первом запросе
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
    
    # Преобразуем в объект Update
    telegram_update = Update.model_validate(update)
    
    # Обрабатываем обновление
    await dp.feed_update(bot, telegram_update)


def handler(request, context):
    """
    Точка входа для Vercel Serverless Function.
    Обрабатывает POST запросы от Telegram Webhook.
    """
    import json
    
    # Vercel передаёт request как dict
    method = request.get("method", "POST")
    
    # Проверяем метод
    if isinstance(method, str) and method.upper() != "POST":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Method not allowed"}),
            "headers": {"Content-Type": "application/json"}
        }
    
    try:
        # Получаем тело запроса
        body = request.get("body", "{}")
        if isinstance(body, str):
            update = json.loads(body)
        else:
            update = body
        
        logger.info(f"Received update: {update.get('update_id')}")
        
        # Создаём новый event loop для async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(handle_webhook(update))
        finally:
            loop.close()
        
        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True}),
            "headers": {"Content-Type": "application/json"}
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }