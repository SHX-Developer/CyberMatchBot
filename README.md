# Cyber Mate

Telegram Mini App для поиска тиммейтов в мобильных и киберспортивных играх.
Монорепо: `backend/` (FastAPI + aiogram + Postgres), `frontend/` (React + Vite).

## Структура

```
CYBER MATE/
├── backend/             # Python · FastAPI + aiogram
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── alembic/
│   ├── app/
│   │   ├── main.py        # бот: /start → картинка + кнопка WebApp
│   │   ├── web/main.py    # /api/* эндпоинты
│   │   ├── config/database/models/repositories/services/assets/
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/            # React + Vite — Telegram Mini App
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── nginx.conf
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml   # 4 сервиса: postgres + backend + bot + frontend
├── .env.example         # шаблон production-конфига
└── .gitignore
```

## Локальный запуск (Docker)

```bash
cp .env.example .env
# заполни POSTGRES_PASSWORD, BOT_TOKEN, WEBAPP_URL
docker compose up -d --build
docker compose ps
```

- Frontend: http://localhost:8080 (порт настраивается через `FRONTEND_PORT`)
- API через nginx: http://localhost:8080/api/health
- Postgres: внутри сети, наружу не выставлен

Миграции прогоняются автоматически при старте `backend` (`alembic upgrade head`).

```bash
docker compose logs -f backend bot
docker compose down            # остановить
docker compose down -v          # + снести БД
```

## Локальный запуск без Docker (dev)

```bash
# Терминал 1
cd backend
.venv/bin/uvicorn app.web.main:app --host 0.0.0.0 --port 8000 --reload

# Терминал 2
cd frontend
npm run dev

# Терминал 3 (опционально)
cd backend && .venv/bin/python -m app.main
```

---

## Деплой на VPS через Dokploy

### Перед началом

1. **VPS** с Ubuntu 22.04+ и >=2 GB RAM (минимум).
2. **Домен** или поддомен (`cybermate.example.com`, либо бесплатный `cybermate.duckdns.org`). А-запись → IP сервера.
3. **Bot token** из BotFather.
4. **Dokploy** установлен на VPS:
   ```bash
   curl -sSL https://dokploy.com/install.sh | sh
   ```
   После установки открыть `http://IP:3000`, создать админа.

### Шаг 1. Настройки бота в BotFather

```
/newapp                  → выбери своего бота → Title: Cyber Mate → Short name: cybermate
/setdomain               → выбери бота → введи https://cybermate.example.com
```

### Шаг 2. Подключить репозиторий

В Dokploy:
- **Project** → New Project → «Cyber Mate».
- Внутри проекта **+ Service** → **Compose**.
- **Provider**: GitHub / GitLab / Git URL → выбрать твой репо, ветка `main`.
- **Compose path**: `docker-compose.yml`.

### Шаг 3. Переменные окружения

В разделе **Environment** Compose-сервиса вставить (взять из `.env.example`):

```
POSTGRES_USER=cybermate
POSTGRES_PASSWORD=<сильный_пароль_24+_символов>
POSTGRES_DB=cybermate

BOT_TOKEN=<токен_BotFather>
WEBAPP_URL=https://cybermate.example.com

WEBAPP_AUTH_REQUIRED=true
LOG_LEVEL=INFO
```

> `FRONTEND_PORT` оставлять не нужно — трафик пойдёт через Traefik Dokploy, не через хост-порт.

### Шаг 4. Удалить `ports:` из frontend (для Dokploy)

В корневом `docker-compose.yml` у сервиса `frontend` удалите блок:
```yaml
    ports:
      - "${FRONTEND_PORT:-8080}:80"
```
В Dokploy внешний трафик идёт через встроенный Traefik, а не через хост-порт.

### Шаг 5. Домен и HTTPS

В сервисе **frontend** вкладка **Domains** → **+ Add Domain**:
- Host: `cybermate.example.com`
- Path: `/`
- Container Port: `80`
- HTTPS: **on**, Certificate Provider: **Let's Encrypt**.

Dokploy сам выпустит сертификат и настроит редирект http→https.

### Шаг 6. Деплой

В Dokploy кнопка **Deploy**. Он сделает `docker compose up -d --build`, прогонит
миграции, поднимет 4 контейнера. В логах проверить:
- `postgres-1` — healthy
- `backend-1` — `INFO: Uvicorn running on http://0.0.0.0:8000`
- `bot-1` — `Bot started. Press Ctrl+C to stop.`
- `frontend-1` — nginx ready

Открыть `https://cybermate.example.com` — увидеть мини-апп. Открыть бота в Telegram,
`/start` → должна прийти картинка с кнопкой «🎮 Открыть Cyber Mate».

### Обновление

```bash
git push
```
В Dokploy включить **Auto Deploy** (webhook), либо вручную **Redeploy**. Миграции
прогонятся автоматически при рестарте `backend`.

### Бэкап БД

В Dokploy раздел Postgres-volumes → schedule snapshots, либо вручную:
```bash
docker compose exec postgres pg_dump -U cybermate cybermate > backup.sql
```

### Что важно проверять на проде

- `WEBAPP_AUTH_REQUIRED=true` — Telegram WebApp HMAC обязателен
- Bot token в `.env` Dokploy, **не в репо**
- HTTPS активен (без него мини-апп не откроется)
- В BotFather URL **совпадает** с `WEBAPP_URL`
- `https://домен/api/health` отвечает `{"status":"ok"}`
