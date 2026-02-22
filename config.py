"""
Конфигурация бота — загрузка переменных окружения и глобальные константы.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

# ── Внешние API ───────────────────────────────────────────────────────────────
FNS_API_TOKEN: str = os.getenv("FNS_API_TOKEN", "")
YANDEX_GEO_TOKEN: str = os.getenv("YANDEX_GEO_TOKEN", "")

# ── Хранилище (локальное, для разработки) ─────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "waste_bot.db")
DOCS_PATH: str = os.getenv("DOCS_PATH", "documents/")

# ── Redis для FSM ─────────────────────────────────────────────────────────────
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

# Использовать Redis вместо MemoryStorage
USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"

# ── Бизнес-константы ──────────────────────────────────────────────────────────
# Базовая стоимость перевозки (руб/км/тонна)
BASE_RATE_PER_KM_PER_TON: float = 15.0
# Минимальная стоимость рейса (руб)
MIN_TRIP_COST: float = 3_000.0
# Максимальный радиус поиска перевозчиков (км)
MAX_CARRIER_RADIUS_KM: int = 500

# ── Роли пользователей ────────────────────────────────────────────────────────
ROLE_SELLER = "seller"
ROLE_BUYER = "buyer"
ROLE_CARRIER = "carrier"

ROLE_LABELS = {
    ROLE_SELLER: "🏭 Продавец",
    ROLE_BUYER: "🛒 Покупатель",
    ROLE_CARRIER: "🚛 Перевозчик",
}

# ── Статусы лота ──────────────────────────────────────────────────────────────
LOT_STATUS_ACTIVE = "active"
LOT_STATUS_RESERVED = "reserved"
LOT_STATUS_IN_TRANSIT = "in_transit"
LOT_STATUS_COMPLETED = "completed"
LOT_STATUS_CANCELLED = "cancelled"

LOT_STATUS_LABELS = {
    LOT_STATUS_ACTIVE: "✅ Активен",
    LOT_STATUS_RESERVED: "🔒 Зарезервирован",
    LOT_STATUS_IN_TRANSIT: "🚛 В пути",
    LOT_STATUS_COMPLETED: "✔️ Завершён",
    LOT_STATUS_CANCELLED: "❌ Отменён",
}

# ── Единицы измерения ─────────────────────────────────────────────────────────
UNIT_TON = "тонна"
UNIT_M3 = "м³"

PRICE_FORMAT_PER_TON = "за тонну"
PRICE_FORMAT_PER_TRIP = "за рейс"

# ── Условия сделки ────────────────────────────────────────────────────────────
CONDITION_DELIVERY = "с доставкой"
CONDITION_PICKUP = "самовывоз"