#!/bin/sh
# Запускает миграции, потом одновременно поднимает FastAPI (uvicorn)
# и Telegram-бот в одном контейнере.
#
# Bot стартует в фоне с авто-рестартом (вдруг Telegram временно недоступен
# или токен ещё не выставлен) — он не валит весь контейнер.
# Uvicorn — главный процесс контейнера: если он падает, контейнер рестартится.
set -eu

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting bot in background with auto-restart..."
(
    while true; do
        python -m app.main || echo "[bot] crashed, restart in 10s"
        sleep 10
    done
) &

echo "[entrypoint] Starting uvicorn (foreground)..."
exec uvicorn app.web.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips='*'
