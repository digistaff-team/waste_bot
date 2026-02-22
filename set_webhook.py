"""
Утилита для установки webhook на Vercel.
Запускать локально после деплоя: python set_webhook.py https://your-app.vercel.app/api/webhook
"""
import sys
import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN


async def set_webhook(webhook_url: str):
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задан в .env")
        return
    
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    try:
        result = await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )
        if result:
            print(f"✅ Webhook установлен: {webhook_url}")
        else:
            print("❌ Не удалось установить webhook")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()


async def delete_webhook():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задан в .env")
        return
    
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook удалён")
    finally:
        await bot.session.close()


async def get_webhook_info():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задан в .env")
        return
    
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    try:
        info = await bot.get_webhook_info()
        print(f"📍 Текущий webhook: {info.url or '(не установлен)'}")
        print(f"   Pending updates: {info.pending_update_count}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python set_webhook.py set <webhook_url>  - установить webhook")
        print("  python set_webhook.py delete             - удалить webhook")
        print("  python set_webhook.py info               - информация о webhook")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "set" and len(sys.argv) >= 3:
        asyncio.run(set_webhook(sys.argv[2]))
    elif command == "delete":
        asyncio.run(delete_webhook())
    elif command == "info":
        asyncio.run(get_webhook_info())
    else:
        print("❌ Неверная команда")
        sys.exit(1)
