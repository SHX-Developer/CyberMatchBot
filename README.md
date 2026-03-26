# CyberMate Bot (MVP)

Telegram-бот для поиска тиммейтов по играм (MVP).

## Stack

- Python 3.12+
- aiogram 3
- SQLAlchemy 2 (async)
- PostgreSQL
- Alembic
- python-dotenv

## Project structure

```text
app/
  bot/
  config/
  database/
  handlers/
  keyboards/
  locales/
  middlewares/
  models/
  repositories/
  services/
  utils/
alembic/
```

## Implemented MVP

- /start
- обязательный выбор языка при первом входе (ru/en/uz)
- сохранение пользователя в БД
- главное меню через Reply Keyboard
- создание анкеты с выбором игры (MLBB, CS GO)
- проверка "сначала создайте анкету" при поиске
- раздел "Мои анкеты" (список, удаление, заполнить заново, добавление другой игры)
- запрет дубликата анкеты по игре без подтверждения
- раздел "Профиль" + статистика
- настройки профиля + смена языка

## Run

1. Создай виртуальное окружение и установи зависимости:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Подготовь `.env`:

```bash
cp .env.example .env
```

3. Подними PostgreSQL и примени миграции:

```bash
alembic upgrade head
```

4. Запусти бота:

```bash
python -m app.main
```
