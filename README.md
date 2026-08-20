# Telegram-бот генерации изображений (AvtoMerkaBot)

Telegram-бот для генерации изображений с примеркой мебели.

## Возможности

- генерация изображений через OpenRouter
- реферальная система
- PostgreSQL с миграциями

## Структура

- `bot.py` — точка входа
- `handlers/` — обработчики команд
- `services/image_gen.py` — генерация изображений
- `db/` — работа с БД
- `migrations/` — SQL-миграции

## Настройка

Скопируйте `.env.example` в `.env` и заполните:

- `BOT_TOKEN` — токен бота (получить у @BotFather)
- `OPENROUTER_API_KEY` — ключ OpenRouter
- `DATABASE_URL` — подключение к PostgreSQL
- `PROXY` — опционально (SOCKS5)

## Запуск

```
pip install -r requirements.txt
python bot.py
```

## Безопасность

См. `SECURITY.md`.
