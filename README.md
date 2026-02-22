# ♻️ WasteBot

Telegram-бот для платформы прозрачного обращения с отходами.

## Возможности

- **Продавцы** — размещение лотов отходов по ФККО
- **Покупатели** — поиск и бронирование отходов
- **Перевозчики** — приём заявок на транспортировку
- Проверка ИНН через API ФНС
- Геокодирование через Яндекс
- Генерация документов (ТТН, акты)

## Технологии

- Python 3.11+
- aiogram 3.4
- Supabase (PostgreSQL)
- Redis (опционально для FSM)

## Локальный запуск

```bash
# Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/Waste_bot.git
cd Waste_bot

# Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Установить зависимости
pip install -r requirements.txt

# Скопировать .env.example в .env и заполнить переменные
cp .env.example .env

# Запустить бота
python bot.py
```

## Настройка Supabase

### 1. Создать проект

1. Перейдите на [supabase.com](https://supabase.com)
2. Создайте новый проект
3. Запомните пароль базы данных

### 2. Создать таблицы

1. Откройте **SQL Editor** в Supabase
2. Скопируйте содержимое файла `supabase_schema.sql`
3. Выполните SQL

### 3. Получить ключи

1. Перейдите в **Settings → API**
2. Скопируйте:
   - **Project URL** → `SUPABASE_URL`
   - **anon public key** → `SUPABASE_ANON_KEY`

### 4. Добавить переменные окружения

В Vercel или локально в `.env`:

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Переменные окружения

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `BOT_TOKEN` | Токен Telegram бота | ✅ |
| `SUPABASE_URL` | URL проекта Supabase | ✅ |
| `SUPABASE_ANON_KEY` | Публичный ключ Supabase | ✅ |
| `FNS_API_TOKEN` | Токен API ФНС | ❌ |
| `YANDEX_GEO_TOKEN` | Токен Яндекс.Геокодера | ❌ |
| `ADMIN_ID` | Telegram ID администратора | ❌ |

## Деплой на Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/Waste_bot)

1. Форкните репозиторий
2. Импортируйте в Vercel
3. Добавьте переменные окружения:
   - `BOT_TOKEN`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
4. Деплой!

### После деплоя

Установите webhook:

```bash
python set_webhook.py set https://your-app.vercel.app/api/webhook
```

## Структура проекта

```
Waste_bot/
├── bot.py                 # Точка входа (polling)
├── config.py              # Конфигурация
├── api/
│   └── webhook.py         # Vercel serverless endpoint
├── handlers/              # Хэндлеры бота
│   ├── registration.py    # Регистрация пользователей
│   ├── seller.py          # Функции продавца
│   ├── buyer.py           # Функции покупателя
│   ├── carrier.py         # Функции перевозчика
│   └── common.py          # Общие хэндлеры
├── models/
│   ├── database.py        # Автовыбор БД (Supabase/SQLite)
│   └── supabase_db.py     # Supabase клиент
├── services/              # Внешние API
├── keyboards/             # Клавиатуры
├── utils/                 # Утилиты
├── supabase_schema.sql    # SQL схема для Supabase
└── set_webhook.py         # Утилита установки webhook
```

## Лицензия

MIT