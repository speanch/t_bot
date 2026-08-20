# Security

Старые ключи из `.env` были опубликованы в открытом виде. **Обязательно перегенерируйте их:**

- **Telegram Bot Token** — зайдите в [@BotFather](https://t.me/BotFather), выберите бота,
  нажмите `API Token` → `Revoke current token`, обновите значение в `.env`.
- **OpenRouter API Key** — в разделе [Keys](https://openrouter.ai/keys) удалите старый ключ
  и создайте новый.

После этого скопируйте `.env.example` в `.env` и вставьте новые значения.

Никогда не коммитьте `.env` в репозиторий (см. `.gitignore`).
