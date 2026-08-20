import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest

from config import config
from db import init_db, close_db
from handlers import router as main_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    session = AiohttpSession(proxy=config.proxy) if config.proxy else None
    bot = Bot(token=config.bot_token, session=session)
    dp = Dispatcher()
    dp.include_router(main_router)

    dp.errors.register(_handle_errors)

    await init_db()

    for attempt in range(1, 100):
        try:
            logger.info("Попытка подключения %d...", attempt)
            await bot.me()
            break
        except Exception as exc:
            logger.warning("Подключение не удалось: %s. Повтор через 10 сек...", exc)
            await asyncio.sleep(10)
    else:
        logger.error("Не удалось подключиться после 100 попыток")
        return

    logger.info("Бот запущен!")

    try:
        await dp.start_polling(bot)
    finally:
        await close_db()


async def _handle_errors(event, exception: Exception) -> None:
    if isinstance(exception, TelegramBadRequest) and "query is too old" in str(exception):
        return
    logger.exception("Unhandled error: %s", exception)


if __name__ == "__main__":
    asyncio.run(main())
