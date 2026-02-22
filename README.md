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
- SQLite / aiosqlite
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

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен Telegram бота |
| `FNS_API_TOKEN` | Токен API ФНС |
| `YANDEX_GEO_TOKEN` | Токен Яндекс.Геокодера |
| `ADMIN_ID` | Telegram ID администратора |
| `DB_PATH` | Путь к SQLite базе |
| `USE_REDIS` | Использовать Redis для FSM |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | Настройки Redis |

## Деплой на Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/Waste_bot)

1. Форкните репозиторий
2. Импортируйте в Vercel
3. Добавьте переменные окружения в настройках проекта
4. Деплой!

### Важно для Vercel

- Бот работает через **Webhooks** (не polling)
- SQLite **не подходит** для production на Vercel (ephemeral FS)
- Рекомендуется использовать внешнюю БД: Turso, PlanetScale, Supabase или Neon

## Структура проекта

```
Waste_bot/
├── bot.py              # Точка входа
├── config.py           # Конфигурация
├── handlers/           # Хэндлеры бота
│   ├── registration.py # Регистрация пользователей
│   ├── seller.py       # Функции продавца
│   ├── buyer.py        # Функции покупателя
│   ├── carrier.py      # Функции перевозчика
│   └── common.py       # Общие хэндлеры
├── models/             # Работа с БД
├── services/           # Внешние API
├── keyboards/          # Клавиатуры
└── utils/              # Утилиты
```

## Лицензия

MIT
