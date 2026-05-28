# Vita Opros

Система еженедельных опросов сотрудников через Telegram + дашборд для анализа.

## Архитектура

- **Bot** — Telegram бот (aiogram 3) для проведения опросов
- **Dashboard** — FastAPI + React для просмотра статистики
- **Database** — PostgreSQL (ранее SQLite)
- **Cache/FSM** — Redis

## Требования

- Docker + Docker Compose
- Или Python 3.11+ (для локальной разработки)

## Быстрый старт (Docker)

### 1. Настройка окружения

```bash
cp .env.example .env
# Отредактируй .env — укажи BOT_TOKEN и POSTGRES_PASSWORD
```

### 2. Запуск

```bash
docker-compose up -d --build
```

### 3. Применение миграций

```bash
docker-compose exec bot alembic upgrade head
```

### 4. Проверка

- Dashboard: http://localhost:8000
- Health check: http://localhost:8000/health

## Миграция с SQLite на PostgreSQL

Если у вас есть данные в SQLite:

```bash
# 1. Запустите PostgreSQL
docker-compose up -d postgres

# 2. Примените миграции
alembic upgrade head

# 3. Запустите скрипт миграции данных
python migrate_data.py

# 4. Запустите остальные сервисы
docker-compose up -d
```

## Локальная разработка

### Установка зависимостей

```bash
pip install -e ".[dev]"
```

### Запуск PostgreSQL и Redis (через Docker)

```bash
docker-compose up -d postgres redis
```

### Запуск бота

```bash
python run_bot.py
```

### Запуск дашборда

```bash
python run_dashboard.py
```

### Тесты

```bash
pytest
```

## Бэкапы

```bash
# Ручной бэкап
bash backup.sh

# Автоматические бэкапы (добавь в cron)
# 0 2 * * * /path/to/backup.sh
```

Бэкапы сохраняются в `./backups/`.

## Полезные команды

```bash
# Логи
docker-compose logs -f bot
docker-compose logs -f dashboard

# Пересборка
docker-compose up -d --build

# Остановка
docker-compose down

# Полная очистка (удалит данные!)
docker-compose down -v
```

## Структура проекта

```
vita_opros/
├── bot/              # Telegram бот
│   ├── main.py       # Точка входа
│   ├── models.py     # SQLAlchemy модели
│   ├── routers/      # Хендлеры
│   └── services/     # Бизнес-логика
├── dashboard/        # Веб-дашборд
│   ├── api/          # FastAPI
│   └── frontend/     # React
├── migrations/       # Alembic миграции
├── tests/            # Тесты
├── docker-compose.yml
├── pyproject.toml
└── .env
```

## Безопасность

- **BOT_TOKEN** — никогда не коммить в репозиторий!
- **POSTGRES_PASSWORD** — используй сильный пароль в продакшене
- **CORS** — в продакшене ограничь `allow_origins` в `dashboard/api/main.py`
- **API** — добавь аутентификацию для `/api/*` эндпоинтов