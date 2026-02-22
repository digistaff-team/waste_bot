"""
Слой работы с Supabase (PostgreSQL через REST API).
Содержит: инициализацию клиента, CRUD-операции для всех сущностей.
"""
import logging
from typing import Optional
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_ANON_KEY

logger = logging.getLogger(__name__)

# Глобальный клиент Supabase
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Получение или создание клиента Supabase."""
    global _supabase_client
    
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError(
                "SUPABASE_URL и SUPABASE_ANON_KEY должны быть заданы в переменных окружения"
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Supabase клиент инициализирован")
    
    return _supabase_client


# ─────────────────────────────────────────────────────────────────────────────
# Инициализация схемы (выполнить один раз через SQL Editor в Supabase)
# ─────────────────────────────────────────────────────────────────────────────

# SQL для создания таблиц в Supabase (выполнить в SQL Editor):
"""
-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    tg_id           BIGINT UNIQUE NOT NULL,
    role            TEXT NOT NULL,
    org_name        TEXT NOT NULL,
    inn             TEXT NOT NULL,
    region          TEXT NOT NULL,
    phone           TEXT NOT NULL,
    email           TEXT NOT NULL,
    vehicle_types   TEXT,
    capacity        REAL,
    carrier_regions TEXT,
    is_verified     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Лоты
CREATE TABLE IF NOT EXISTS lots (
    id              BIGSERIAL PRIMARY KEY,
    seller_id       BIGINT NOT NULL REFERENCES users(id),
    fkko_code       TEXT NOT NULL,
    fkko_name       TEXT NOT NULL,
    volume          REAL NOT NULL,
    unit            TEXT NOT NULL,
    price           REAL NOT NULL,
    price_format    TEXT NOT NULL,
    condition       TEXT NOT NULL,
    address_from    TEXT,
    address_to      TEXT,
    lat_from        REAL,
    lon_from        REAL,
    lat_to          REAL,
    lon_to          REAL,
    valid_until     TEXT,
    photo_file_id   TEXT,
    status          TEXT DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Заявки на перевозку
CREATE TABLE IF NOT EXISTS transport_requests (
    id              BIGSERIAL PRIMARY KEY,
    lot_id          BIGINT NOT NULL REFERENCES lots(id),
    buyer_id        BIGINT NOT NULL REFERENCES users(id),
    carrier_id      BIGINT REFERENCES users(id),
    distance_km     REAL,
    transport_cost  REAL,
    status          TEXT DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Документы
CREATE TABLE IF NOT EXISTS documents (
    id              BIGSERIAL PRIMARY KEY,
    request_id      BIGINT NOT NULL REFERENCES transport_requests(id),
    doc_type        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    tg_file_id      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- История статусов
CREATE TABLE IF NOT EXISTS status_history (
    id              BIGSERIAL PRIMARY KEY,
    request_id      BIGINT NOT NULL REFERENCES transport_requests(id),
    old_status      TEXT,
    new_status      TEXT NOT NULL,
    changed_by      BIGINT REFERENCES users(id),
    comment         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_lots_status ON lots(status);
CREATE INDEX IF NOT EXISTS idx_lots_seller_id ON lots(seller_id);
CREATE INDEX IF NOT EXISTS idx_lots_created_at ON lots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transport_requests_lot_id ON transport_requests(lot_id);
CREATE INDEX IF NOT EXISTS idx_transport_requests_buyer_id ON transport_requests(buyer_id);
CREATE INDEX IF NOT EXISTS idx_transport_requests_carrier_id ON transport_requests(carrier_id);
CREATE INDEX IF NOT EXISTS idx_transport_requests_status ON transport_requests(status);

-- RLS политики (отключить для простоты или настроить правильно)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE lots ENABLE ROW LEVEL SECURITY;
ALTER TABLE transport_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;

-- Разрешить все операции для авторизованных пользователей
CREATE POLICY "Allow all for anon" ON users FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON lots FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON transport_requests FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON documents FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON status_history FOR ALL USING (true);
"""


async def init_db() -> None:
    """Проверка подключения к Supabase."""
    try:
        supabase = get_supabase()
        # Простой запрос для проверки соединения
        result = supabase.table("users").select("id").limit(1).execute()
        logger.info("Подключение к Supabase успешно")
    except Exception as e:
        logger.error(f"Ошибка подключения к Supabase: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Пользователи
# ─────────────────────────────────────────────────────────────────────────────

async def get_user_by_tg_id(tg_id: int) -> Optional[dict]:
    """Получение пользователя по Telegram ID."""
    try:
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Ошибка получения пользователя: {e}")
        return None


async def create_user(data: dict) -> int:
    """Создание нового пользователя."""
    try:
        supabase = get_supabase()
        result = supabase.table("users").insert({
            "tg_id": data["tg_id"],
            "role": data["role"],
            "org_name": data["org_name"],
            "inn": data["inn"],
            "region": data["region"],
            "phone": data["phone"],
            "email": data["email"],
            "vehicle_types": data.get("vehicle_types"),
            "capacity": data.get("capacity"),
            "carrier_regions": data.get("carrier_regions"),
        }).execute()
        return result.data[0]["id"]
    except Exception as e:
        logger.error(f"Ошибка создания пользователя: {e}")
        raise


async def update_user(tg_id: int, fields: dict) -> None:
    """Обновление данных пользователя."""
    try:
        supabase = get_supabase()
        supabase.table("users").update(fields).eq("tg_id", tg_id).execute()
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя: {e}")
        raise


async def get_carriers_by_region(region: str) -> list[dict]:
    """Получение перевозчиков, работающих в указанном регионе."""
    try:
        supabase = get_supabase()
        # Ищем перевозчиков, у которых регион есть в carrier_regions или указано "все"
        result = supabase.table("users").select("*").eq("role", "carrier").or_(
            f"carrier_regions.ilike.%{region}%,carrier_regions.ilike.%все%"
        ).execute()
        return result.data
    except Exception as e:
        logger.error(f"Ошибка получения перевозчиков: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Лоты
# ─────────────────────────────────────────────────────────────────────────────

async def create_lot(data: dict) -> int:
    """Создание нового лота."""
    try:
        supabase = get_supabase()
        result = supabase.table("lots").insert({
            "seller_id": data["seller_id"],
            "fkko_code": data["fkko_code"],
            "fkko_name": data["fkko_name"],
            "volume": data["volume"],
            "unit": data["unit"],
            "price": data["price"],
            "price_format": data["price_format"],
            "condition": data["condition"],
            "address_from": data.get("address_from"),
            "address_to": data.get("address_to"),
            "lat_from": data.get("lat_from"),
            "lon_from": data.get("lon_from"),
            "lat_to": data.get("lat_to"),
            "lon_to": data.get("lon_to"),
            "valid_until": data.get("valid_until"),
            "photo_file_id": data.get("photo_file_id"),
        }).execute()
        return result.data[0]["id"]
    except Exception as e:
        logger.error(f"Ошибка создания лота: {e}")
        raise


async def get_lot_by_id(lot_id: int) -> Optional[dict]:
    """Получение лота по ID."""
    try:
        supabase = get_supabase()
        result = supabase.table("lots").select("*").eq("id", lot_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Ошибка получения лота: {e}")
        return None


async def get_lots_by_seller(seller_id: int) -> list[dict]:
    """Получение лотов продавца."""
    try:
        supabase = get_supabase()
        result = supabase.table("lots").select("*").eq("seller_id", seller_id).order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"Ошибка получения лотов продавца: {e}")
        return []


async def search_lots(filters: dict) -> list[dict]:
    """Поиск лотов по фильтрам."""
    try:
        supabase = get_supabase()
        query = supabase.table("lots").select("*").eq("status", "active")
        
        if filters.get("region"):
            # Поиск по адресу отправления или назначения
            query = query.or_(
                f"address_from.ilike.%{filters['region']}%,address_to.ilike.%{filters['region']}%"
            )
        
        if filters.get("fkko_name"):
            query = query.ilike("fkko_name", f"%{filters['fkko_name']}%")
        
        if filters.get("volume_min") is not None:
            query = query.gte("volume", filters["volume_min"])
        
        if filters.get("volume_max") is not None:
            query = query.lte("volume", filters["volume_max"])
        
        if filters.get("price_min") is not None:
            query = query.gte("price", filters["price_min"])
        
        if filters.get("price_max") is not None:
            query = query.lte("price", filters["price_max"])
        
        result = query.order("created_at", desc=True).limit(50).execute()
        return result.data
    except Exception as e:
        logger.error(f"Ошибка поиска лотов: {e}")
        return []


async def update_lot_status(lot_id: int, status: str) -> None:
    """Обновление статуса лота."""
    try:
        supabase = get_supabase()
        supabase.table("lots").update({"status": status}).eq("id", lot_id).execute()
    except Exception as e:
        logger.error(f"Ошибка обновления статуса лота: {e}")
        raise


async def cancel_lot(lot_id: int, seller_tg_id: int) -> bool:
    """Отмена лота продавцом."""
    try:
        supabase = get_supabase()
        
        # Получаем лот и проверяем владельца
        user = await get_user_by_tg_id(seller_tg_id)
        if not user:
            return False
        
        lot = await get_lot_by_id(lot_id)
        if not lot or lot["seller_id"] != user["id"] or lot["status"] != "active":
            return False
        
        await update_lot_status(lot_id, "cancelled")
        return True
    except Exception as e:
        logger.error(f"Ошибка отмены лота: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Заявки на перевозку
# ─────────────────────────────────────────────────────────────────────────────

async def create_transport_request(data: dict) -> int:
    """Создание заявки на перевозку."""
    try:
        supabase = get_supabase()
        result = supabase.table("transport_requests").insert({
            "lot_id": data["lot_id"],
            "buyer_id": data["buyer_id"],
            "distance_km": data.get("distance_km"),
            "transport_cost": data.get("transport_cost"),
        }).execute()
        return result.data[0]["id"]
    except Exception as e:
        logger.error(f"Ошибка создания заявки: {e}")
        raise


async def get_transport_request_by_id(req_id: int) -> Optional[dict]:
    """Получение заявки по ID."""
    try:
        supabase = get_supabase()
        result = supabase.table("transport_requests").select("*").eq("id", req_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Ошибка получения заявки: {e}")
        return None


async def get_requests_for_carrier(carrier_id: int) -> list[dict]:
    """Заявки, доступные перевозчику."""
    try:
        supabase = get_supabase()
        result = supabase.table("transport_requests").select("*").or_(
            f"status.eq.pending,carrier_id.eq.{carrier_id}"
        ).order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"Ошибка получения заявок перевозчика: {e}")
        return []


async def get_requests_for_buyer(buyer_id: int) -> list[dict]:
    """Заявки покупателя."""
    try:
        supabase = get_supabase()
        result = supabase.table("transport_requests").select("*").eq("buyer_id", buyer_id).order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"Ошибка получения заявок покупателя: {e}")
        return []


async def update_request_status(
    req_id: int,
    new_status: str,
    carrier_id: Optional[int] = None,
    changed_by: Optional[int] = None,
    comment: Optional[str] = None,
) -> None:
    """Обновление статуса заявки."""
    try:
        supabase = get_supabase()
        
        # Получаем старый статус
        req = await get_transport_request_by_id(req_id)
        old_status = req.get("status") if req else None
        
        # Обновляем заявку
        update_data = {"status": new_status, "updated_at": "NOW()"}
        if carrier_id is not None:
            update_data["carrier_id"] = carrier_id
        
        supabase.table("transport_requests").update(update_data).eq("id", req_id).execute()
        
        # Записываем в историю
        supabase.table("status_history").insert({
            "request_id": req_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "comment": comment,
        }).execute()
    except Exception as e:
        logger.error(f"Ошибка обновления статуса заявки: {e}")
        raise


async def get_status_history(req_id: int) -> list[dict]:
    """История статусов заявки."""
    try:
        supabase = get_supabase()
        result = supabase.table("status_history").select("*").eq("request_id", req_id).order("created_at").execute()
        return result.data
    except Exception as e:
        logger.error(f"Ошибка получения истории статусов: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Документы
# ─────────────────────────────────────────────────────────────────────────────

async def save_document(data: dict) -> int:
    """Сохранение документа."""
    try:
        supabase = get_supabase()
        result = supabase.table("documents").insert({
            "request_id": data["request_id"],
            "doc_type": data["doc_type"],
            "file_path": data["file_path"],
            "tg_file_id": data.get("tg_file_id"),
        }).execute()
        return result.data[0]["id"]
    except Exception as e:
        logger.error(f"Ошибка сохранения документа: {e}")
        raise


async def get_documents_by_request(req_id: int) -> list[dict]:
    """Получение документов по заявке."""
    try:
        supabase = get_supabase()
        result = supabase.table("documents").select("*").eq("request_id", req_id).execute()
        return result.data
    except Exception as e:
        logger.error(f"Ошибка получения документов: {e}")
        return []
