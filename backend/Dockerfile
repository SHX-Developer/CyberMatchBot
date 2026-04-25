FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Минимум системных пакетов под asyncpg/SQLAlchemy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Сначала только pyproject — кэшируем установку зависимостей.
COPY pyproject.toml ./

# Готовим dummy README, чтобы pyproject не падал из-за отсутствия readme файла.
RUN touch README.md

# Устанавливаем зависимости. Кода ещё нет — pip ругаться не будет, потому что
# мы используем "pip install -e ." после копирования исходников ниже.
RUN pip install --upgrade pip \
    && pip install \
        "aiogram==3.13.1" \
        "SQLAlchemy>=2.0.32,<3.0.0" \
        "greenlet>=3.1.1,<4.0.0" \
        "asyncpg>=0.30.0,<0.31.0" \
        "alembic>=1.13.2,<2.0.0" \
        "python-dotenv>=1.0.1,<2.0.0" \
        "fastapi>=0.116.0,<1.0.0" \
        "uvicorn[standard]>=0.35.0,<1.0.0"

# Теперь копируем код и регистрируем пакет (для импорта app.*).
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

RUN pip install -e .

# Один контейнер — uvicorn + бот в фоне (см. entrypoint.sh).
EXPOSE 8000
CMD ["./entrypoint.sh"]
