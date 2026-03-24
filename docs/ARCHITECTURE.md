# CyberMate MVP Architecture

## Layers

- `handlers` — Telegram update routing, сценарии диалога.
- `services` — бизнес-логика (правила MVP, проверки, orchestration).
- `repositories` — SQLAlchemy запросы к БД.
- `models` — ORM сущности.
- `keyboards` — Reply/Inline keyboard builders.
- `locales` — i18n (ru/en/uz) и translation manager.
- `middlewares` — DI для `AsyncSession`.
- `bot`/`main` — bootstrap приложения.

## Current tables (implemented)

1. `users`
- Telegram user identity
- locale (`language_code_enum`)
- registration metadata

2. `player_profiles`
- анкеты по играм
- `owner_id`, `game`, timestamps
- optional MVP-ready fields: `rank`, `role`, `play_time`, `about`
- unique `(owner_id, game)` to prevent duplicates

3. `user_stats`
- counters for profile block
- `likes_count`, `followers_count`, `profile_views_count`, `mutual_likes_count`

## Enums

- `language_code_enum`: `ru`, `en`, `uz`
- `game_code_enum`: `mlbb`, `cs_go`

## Extension points (next iterations)

Potential new tables (not implemented in MVP):

- `profile_likes` (who liked whose profile)
- `user_follows` (followers/subscriptions)
- `profile_views` (view events)
- `friend_links` (confirmed teammates/friends)
- `match_filters` (saved search preferences)

Current service/repository boundaries allow adding these without rewriting handlers.
