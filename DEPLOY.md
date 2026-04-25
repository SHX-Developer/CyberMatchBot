# Деплой через Dokploy (автоматически по `git push`)

Сценарий: VPS с Dokploy, Postgres уже работает в Dokploy как отдельный
Database-сервис, нужно поднять рядом backend + bot + frontend и автоматически
перевыкатывать всё при пуше в `main`.

## 0. Структура файлов в репо

| Файл | Назначение |
|---|---|
| `docker-compose.yml` | standalone (включает свой Postgres) — для локального теста |
| `docker-compose.dokploy.yml` | **для Dokploy** — без Postgres, подключается к существующему |
| `backend/Dockerfile` | FastAPI + aiogram |
| `frontend/Dockerfile` | React build → nginx |
| `frontend/nginx.conf` | SPA + проксирование `/api/*` на `backend:8000` |
| `.env.example` | шаблон env-переменных |

## 1. Если в Dokploy уже крутится старый бот

Чтобы не было конфликта `getUpdates` (Telegram запрещает двух ботов с одним токеном):

- Зайди в Dokploy → старый сервис бота → **Stop** или **Delete** его compose,
- ИЛИ замени его compose-файл нашим новым `docker-compose.dokploy.yml`.

База остаётся как есть. Наш `backend` при старте сделает `alembic upgrade head` —
накатит новые миграции (nickname, birth_date, is_registered, новые игры,
аватар, profile_status) **поверх существующих данных**, ничего не потеряв.

## 2. Создать сервис в Dokploy

В существующем Project (где уже Postgres):

1. **+ Create Service** → **Compose**.
2. **Provider**: подключи свой GitHub-репозиторий (тот же, что и сейчас).
3. **Branch**: `main`.
4. **Compose File**: `docker-compose.dokploy.yml` ← важно, не дефолтный.
5. **Save**.

## 3. Подключить compose к сети Postgres

Postgres в Dokploy живёт в своём docker network. Чтобы наши сервисы могли
до него достучаться:

- В compose-сервисе → вкладка **Advanced** → **Networks** → **Add External Network**
  → выбери network того Postgres-сервиса (обычно `dokploy-network` или
  `<projectname>_default`).

После этого `backend` сможет обращаться к Postgres по имени контейнера.

## 4. Environment

В compose-сервисе → **Environment** вставь:

```env
BOT_TOKEN=<токен_из_BotFather>

# Имя контейнера Postgres в Dokploy + его кредсы.
# Имя смотришь в Dokploy → Postgres сервис → Container Name.
DATABASE_URL=postgresql+asyncpg://cybermate:<password>@<имя_postgres_контейнера>:5432/cybermate

WEBAPP_URL=https://cybermate.example.com
WEBAPP_AUTH_REQUIRED=true
WEBAPP_DEV_USER_ID=
LOG_LEVEL=INFO
```

> Если postgres из Dokploy у тебя называется, скажем, `cybermate-db-abc123`,
> то DATABASE_URL = `postgresql+asyncpg://USER:PASS@cybermate-db-abc123:5432/DBNAME`.
> Юзера/пароль возьми из вкладки Postgres → Credentials.

## 5. Домен и HTTPS

Сервис **frontend** в compose → вкладка **Domains** → **+ Add Domain**:

- Host: `cybermate.example.com` (твой реальный домен или duckdns)
- Path: `/`
- Container Port: `80`
- HTTPS: **on**, Provider: **Let's Encrypt**

Dokploy сам выпишет сертификат и настроит редирект.

## 6. Авто-деплой по `git push`

Это и есть то, что ты просишь.

1. В Dokploy → твой compose-сервис → **General** → **Auto Deploy** = **on**.
2. Скопируй **Webhook URL** который покажет Dokploy.
3. Открой репо на GitHub → **Settings** → **Webhooks** → **Add webhook**:
   - Payload URL: вставь webhook из Dokploy
   - Content type: `application/json`
   - Trigger: **Just the push event**
4. **Save**.

Готово. Теперь на каждый `git push origin main`:
GitHub → webhook → Dokploy → `git pull` → `docker compose -f docker-compose.dokploy.yml build` → пересоздание контейнеров → миграции прогоняются автоматически.

## 7. Первый деплой

В Dokploy → **Deploy**. Следи за логами:

- `backend` → миграция → `Uvicorn running on http://0.0.0.0:8000`
- `bot` → `Bot started. Press Ctrl+C to stop.`
- `frontend` → `nginx ready`

Открой `https://твой-домен/api/health` → `{"status":"ok"}`. Открой бота в TG → `/start` → должна прийти картинка с кнопкой «🎮 Открыть Cyber Mate».

## 8. После деплоя — связать с Telegram

В BotFather:
```
/newapp     → выбрать бота → Title=Cyber Mate, Short name=cybermate
            → ввести URL: https://твой-домен
/setdomain  → выбрать бота → ввести https://твой-домен
```

После этого кнопка из `/start` откроет полноценный мини-апп прямо в Telegram.

## 9. Что произойдёт при следующем `git push`

1. GitHub получает push, дёргает webhook.
2. Dokploy делает `git pull` в свой клон репо.
3. Видит изменения → `docker compose build` — пересобирает изменённые образы (Vite перебилдится только если поменялся фронт; backend — только если поменялся pyproject или код).
4. `docker compose up -d --remove-orphans` — пересоздаёт контейнеры с новыми образами.
5. `backend` стартует → `alembic upgrade head` накатывает новые миграции, если есть → uvicorn.
6. `bot` стартует на новой версии.
7. `frontend` отдаёт свежий `dist/`.
8. Юзеры через 10–60 секунд получают новую версию (зависит от размера билда).

Простой пользователя ≈ 5–10 секунд (только пока контейнеры пересоздаются). Если нужен zero-downtime — это уже про Dokploy rolling updates, отдельная история.

## 10. Бэкап БД

Postgres-сервис в Dokploy имеет встроенный **Backup** в UI: расписание, S3-target, ручной снапшот. Включи минимум раз в сутки.

## 11. Откат

В Dokploy → compose-сервис → **Deployments** → выбираешь предыдущий deployment → **Redeploy**. Откатывается к старому коммиту.

---

## Локальный тест перед пушем

Чтобы убедиться, что compose поднимается, прежде чем пушить:

```bash
cp .env.example .env   # заполни
docker compose up -d --build
docker compose ps
curl http://localhost:8080/api/health
docker compose down -v
```

Это standalone-режим со встроенным Postgres — он **не** трогает прод.
