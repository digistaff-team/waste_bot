"""
Слой работы с базой данных (SQLite + aiosqlite).
Содержит: инициализацию схемы, CRUD-операции для всех сущностей.
"""
import logging
import aiosqlite
from typing import Optional
from config import DB_PATH

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Инициализация схемы
# ─────────────────────────────────────────────────────────────────────────────

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id           INTEGER UNIQUE NOT NULL,
    role            TEXT NOT NULL,
    org_name        TEXT NOT NULL,
    inn             TEXT NOT NULL,
    region          TEXT NOT NULL,
    phone           TEXT NOT NULL,
    email           TEXT NOT NULL,
    vehicle_types   TEXT,
    capacity        REAL,
    carrier_regions TEXT,
    is_verified     INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

CREATE_LOTS_TABLE = """
CREATE TABLE IF NOT EXISTS lots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id       INTEGER NOT NULL REFERENCES users(id),
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
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

CREATE_TRANSPORT_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS transport_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id          INTEGER NOT NULL REFERENCES lots(id),
    buyer_id        INTEGER NOT NULL REFERENCES users(id),
    carrier_id      INTEGER REFERENCES users(id),
    distance_km     REAL,
    transport_cost  REAL,
    status          TEXT DEFAULT 'pending',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
"""

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL REFERENCES transport_requests(id),
    doc_type        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    tg_file_id      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

CREATE_STATUS_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS status_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL REFERENCES transport_requests(id),
    old_status      TEXT,
    new_status      TEXT NOT NULL,
    changed_by      INTEGER REFERENCES users(id),
    comment         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

# ─────────────────────────────────────────────────────────────────────────────
# Индексы для оптимизации запросов
# ─────────────────────────────────────────────────────────────────────────────
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_lots_status ON lots(status)",
    "CREATE INDEX IF NOT EXISTS idx_lots_seller_id ON lots(seller_id)",
    "CREATE INDEX IF NOT EXISTS idx_lots_created_at ON lots(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_transport_requests_lot_id ON transport_requests(lot_id)",
    "CREATE INDEX IF NOT EXISTS idx_transport_requests_buyer_id ON transport_requests(buyer_id)",
    "CREATE INDEX IF NOT EXISTS idx_transport_requests_carrier_id ON transport_requests(carrier_id)",
    "CREATE INDEX IF NOT EXISTS idx_transport_requests_status ON transport_requests(status)",
    "CREATE INDEX IF NOT EXISTS idx_documents_request_id ON documents(request_id)",
    "CREATE INDEX IF NOT EXISTS idx_status_history_request_id ON status_history(request_id)",
    "CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id)",
    "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
]


async def init_db() -> None:
    """Создание всех таблиц и индексов при первом запуске."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_LOTS_TABLE)
        await db.execute(CREATE_TRANSPORT_REQUESTS_TABLE)
        await db.execute(CREATE_DOCUMENTS_TABLE)
        await db.execute(CREATE_STATUS_HISTORY_TABLE)
        
        # Создаём индексы
        for index_sql in INDEXES:
            await db.execute(index_sql)
        
        await db.commit()
        logger.info("База данных и индексы инициализированы")


# ─────────────────────────────────────────────────────────────────────────────
# Пользователи
# ─────────────────────────────────────────────────────────────────────────────

async def get_user_by_tg_id(tg_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO users
               (tg_id, role, org_name, inn, region, phone, email,
                vehicle_types, capacity, carrier_regions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["tg_id"], data["role"], data["org_name"], data["inn"],
                data["region"], data["phone"], data["email"],
                data.get("vehicle_types"), data.get("capacity"),
                data.get("carrier_regions"),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def update_user(tg_id: int, fields: dict) -> None:
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [tg_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {set_clause} WHERE tg_id = ?", values
        )
        await db.commit()


async def get_carriers_by_region(region: str) -> list[dict]:
    """Получить перевозчиков, работающих в указанном регионе."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM users
               WHERE role = 'carrier'
               AND (carrier_regions LIKE ? OR carrier_regions LIKE '%все%')""",
            (f"%{region}%",),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Лоты
# ─────────────────────────────────────────────────────────────────────────────

async def create_lot(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO lots
               (seller_id, fkko_code, fkko_name, volume, unit, price,
                price_format, condition, address_from, address_to,
                lat_from, lon_from, lat_to, lon_to,
                valid_until, photo_file_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["seller_id"], data["fkko_code"], data["fkko_name"],
                data["volume"], data["unit"], data["price"],
                data["price_format"], data["condition"],
                data.get("address_from"), data.get("address_to"),
                data.get("lat_from"), data.get("lon_from"),
                data.get("lat_to"), data.get("lon_to"),
                data.get("valid_until"), data.get("photo_file_id"),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_lot_by_id(lot_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM lots WHERE id = ?", (lot_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_lots_by_seller(seller_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM lots WHERE seller_id = ? ORDER BY created_at DESC",
            (seller_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def search_lots(filters: dict) -> list[dict]:
    """
    Поиск лотов по фильтрам.
    filters: region, fkko_name, volume_min, volume_max, price_min, price_max
    """
    query = "SELECT * FROM lots WHERE status = 'active'"
    params: list = []

    if filters.get("region"):
        query += " AND (address_from LIKE ? OR address_to LIKE ?)"
        params += [f"%{filters['region']}%", f"%{filters['region']}%"]

    if filters.get("fkko_name"):
        query += " AND fkko_name LIKE ?"
        params.append(f"%{filters['fkko_name']}%")

    if filters.get("volume_min") is not None:
        query += " AND volume >= ?"
        params.append(filters["volume_min"])

    if filters.get("volume_max") is not None:
        query += " AND volume <= ?"
        params.append(filters["volume_max"])

    if filters.get("price_min") is not None:
        query += " AND price >= ?"
        params.append(filters["price_min"])

    if filters.get("price_max") is not None:
        query += " AND price <= ?"
        params.append(filters["price_max"])

    query += " ORDER BY created_at DESC LIMIT 50"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def update_lot_status(lot_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE lots SET status = ? WHERE id = ?", (status, lot_id)
        )
        await db.commit()


async def cancel_lot(lot_id: int, seller_tg_id: int) -> bool:
    """Отмена лота продавцом. Возвращает True если успешно."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT l.id FROM lots l JOIN users u ON l.seller_id = u.id "
            "WHERE l.id = ? AND u.tg_id = ? AND l.status = 'active'",
            (lot_id, seller_tg_id),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        await db.execute(
            "UPDATE lots SET status = 'cancelled' WHERE id = ?", (lot_id,)
        )
        await db.commit()
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Заявки на перевозку
# ─────────────────────────────────────────────────────────────────────────────

async def create_transport_request(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO transport_requests
               (lot_id, buyer_id, distance_km, transport_cost)
               VALUES (?, ?, ?, ?)""",
            (
                data["lot_id"], data["buyer_id"],
                data.get("distance_km"), data.get("transport_cost"),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_transport_request_by_id(req_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM transport_requests WHERE id = ?", (req_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_requests_for_carrier(carrier_id: int) -> list[dict]:
    """Заявки, доступные перевозчику (pending) или уже принятые им."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM transport_requests
               WHERE status = 'pending' OR carrier_id = ?
               ORDER BY created_at DESC""",
            (carrier_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_requests_for_buyer(buyer_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM transport_requests WHERE buyer_id = ? ORDER BY created_at DESC",
            (buyer_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def update_request_status(
    req_id: int,
    new_status: str,
    carrier_id: Optional[int] = None,
    changed_by: Optional[int] = None,
    comment: Optional[str] = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем старый статус для истории
        async with db.execute(
            "SELECT status FROM transport_requests WHERE id = ?", (req_id,)
        ) as cursor:
            row = await cursor.fetchone()
            old_status = row[0] if row else None

        update_fields = "status = ?, updated_at = datetime('now')"
        params: list = [new_status]

        if carrier_id is not None:
            update_fields += ", carrier_id = ?"
            params.append(carrier_id)

        params.append(req_id)
        await db.execute(
            f"UPDATE transport_requests SET {update_fields} WHERE id = ?", params
        )

        # Записываем в историю
        await db.execute(
            """INSERT INTO status_history
               (request_id, old_status, new_status, changed_by, comment)
               VALUES (?, ?, ?, ?, ?)""",
            (req_id, old_status, new_status, changed_by, comment),
        )
        await db.commit()


async def get_status_history(req_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM status_history WHERE request_id = ? ORDER BY created_at",
            (req_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Документы
# ─────────────────────────────────────────────────────────────────────────────

async def save_document(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO documents (request_id, doc_type, file_path, tg_file_id)
               VALUES (?, ?, ?, ?)""",
            (data["request_id"], data["doc_type"], data["file_path"], data.get("tg_file_id")),
        )
        await db.commit()
        return cursor.lastrowid


async def get_documents_by_request(req_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM documents WHERE request_id = ?", (req_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
