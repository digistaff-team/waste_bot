from flask import Flask, request, jsonify
import logging
import asyncio
import os

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_bot = None
_dp = None
_session = None


async def get_bot_and_dp():
    """Ленивая инициализация бота и диспетчера."""
    global _bot, _dp, _session
    
    if _bot is None:
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.fsm.storage.memory import MemoryStorage
        from aiohttp import ClientSession
        
        BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        
        from handlers import registration, seller, buyer, carrier, common
        
        _session = ClientSession()
        _bot = Bot(
            token=BOT_TOKEN,
            session=_session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        _dp = Dispatcher(storage=MemoryStorage())
        
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
    
    bot, dp = await get_bot_and_dp()
    
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
    
    telegram_update = Update.model_validate(update)
    await dp.feed_update(bot, telegram_update)


@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Обработка POST запросов от Telegram."""
    try:
        update = request.get_json(force=True)
        logger.info(f"Received update: {update.get('update_id')}")
        
        # Используем текущий event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(handle_webhook(update))
        
        return jsonify({"ok": True})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/webhook', methods=['GET'])
def webhook_info():
    """Информация об эндпоинте."""
    return jsonify({
        "status": "ok",
        "message": "WasteBot webhook endpoint",
        "usage": "POST Telegram updates here"
    })


@app.route('/', methods=['GET'])
def index():
    """Корневой эндпоинт."""
    return jsonify({
        "name": "WasteBot",
        "status": "running"
    })