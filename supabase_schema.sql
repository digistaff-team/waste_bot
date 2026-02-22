-- ============================================================================
-- WasteBot Database Schema for Supabase
-- Выполните этот SQL в SQL Editor вашего проекта Supabase
-- ============================================================================

-- ── Пользователи ─────────────────────────────────────────────────────────────
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

-- ── Лоты отходов ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lots (
    id              BIGSERIAL PRIMARY KEY,
    seller_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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

-- ── Заявки на перевозку ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transport_requests (
    id              BIGSERIAL PRIMARY KEY,
    lot_id          BIGINT NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    buyer_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    carrier_id      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    distance_km     REAL,
    transport_cost  REAL,
    status          TEXT DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Документы ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              BIGSERIAL PRIMARY KEY,
    request_id      BIGINT NOT NULL REFERENCES transport_requests(id) ON DELETE CASCADE,
    doc_type        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    tg_file_id      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── История статусов ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS status_history (
    id              BIGSERIAL PRIMARY KEY,
    request_id      BIGINT NOT NULL REFERENCES transport_requests(id) ON DELETE CASCADE,
    old_status      TEXT,
    new_status      TEXT NOT NULL,
    changed_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    comment         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Индексы для оптимизации ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_lots_status ON lots(status);
CREATE INDEX IF NOT EXISTS idx_lots_seller_id ON lots(seller_id);
CREATE INDEX IF NOT EXISTS idx_lots_created_at ON lots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transport_requests_lot_id ON transport_requests(lot_id);
CREATE INDEX IF NOT EXISTS idx_transport_requests_buyer_id ON transport_requests(buyer_id);
CREATE INDEX IF NOT EXISTS idx_transport_requests_carrier_id ON transport_requests(carrier_id);
CREATE INDEX IF NOT EXISTS idx_transport_requests_status ON transport_requests(status);
CREATE INDEX IF NOT EXISTS idx_documents_request_id ON documents(request_id);
CREATE INDEX IF NOT EXISTS idx_status_history_request_id ON status_history(request_id);

-- ── Row Level Security (RLS) ────────────────────────────────────────────────
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE lots ENABLE ROW LEVEL SECURITY;
ALTER TABLE transport_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;

-- Политика: разрешить все операции для анонимных пользователей
-- (для Telegram бота, который работает через anon key)
CREATE POLICY "Allow all operations for anon users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations for anon users" ON lots FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations for anon users" ON transport_requests FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations for anon users" ON documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations for anon users" ON status_history FOR ALL USING (true) WITH CHECK (true);

-- ── Функция для автоматического обновления updated_at ───────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для transport_requests
DROP TRIGGER IF EXISTS update_transport_requests_updated_at ON transport_requests;
CREATE TRIGGER update_transport_requests_updated_at
    BEFORE UPDATE ON transport_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ГОТОВО! Таблицы созданы.
-- ============================================================================
