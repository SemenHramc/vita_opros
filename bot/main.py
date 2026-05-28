import asyncio
import signal

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import TelegramObject, BotCommand, BotCommandScopeAllPrivateChats
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis.asyncio import Redis

from bot.config import settings
from bot.database import async_session, engine
from sqlalchemy import text
from bot.logging_config import configure_logging, get_logger
from bot.middleware import RedisRateLimitMiddleware
from bot.routers import start, survey, admin
from bot.routers.update import router as update_router
from bot.services.reminder import send_reminders, send_friday_reminders

configure_logging(json_format=False)
logger = get_logger(__name__)


class DBSessionMiddleware(BaseMiddleware):

    async def __call__(self, handler, event: TelegramObject, data: dict):
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)


async def set_bot_commands(bot: Bot):
    employee_commands = [
        BotCommand(command="start", description="Перезапустить бота"),
        BotCommand(command="survey", description="Пройти еженедельный опрос"),
        BotCommand(command="update", description="Обновить оценку по клиенту"),
    ]
    admin_commands = employee_commands + [
        BotCommand(command="admin_list_employees", description="Список сотрудников"),
        BotCommand(command="admin_add_employee", description="Добавить сотрудника"),
        BotCommand(command="admin_remove_employee", description="Удалить сотрудника"),
        BotCommand(command="admin_list_clients", description="Список клиентов"),
        BotCommand(command="admin_add_client", description="Добавить клиента"),
        BotCommand(command="admin_remove_client", description="Удалить клиента"),
        BotCommand(command="admin_import_clients", description="Импорт клиентов из CSV"),
    ]
    await bot.set_my_commands(employee_commands, BotCommandScopeAllPrivateChats())
    logger.info("bot_commands_set")


async def main():
    logger.info("bot_starting", bot_token_last4=settings.bot_token[-4:])

    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        logger.info("redis_connected", url=settings.redis_url)
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    try:
        storage = RedisStorage.from_url(settings.redis_url)
    except Exception as e:
        logger.error("redis_storage_failed", error=str(e))
        await redis.aclose()
        raise

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        await redis.aclose()
        await storage.close()
        raise

    bot = Bot(token=settings.bot_token)

    dp = Dispatcher(storage=storage)

    dp.message.middleware(DBSessionMiddleware())
    dp.callback_query.middleware(DBSessionMiddleware())
    dp.message.middleware(
        RedisRateLimitMiddleware(
            redis=redis,
            limit=settings.rate_limit_messages,
            window=settings.rate_limit_window,
        )
    )

    dp.include_router(start.router)
    dp.include_router(survey.router)
    dp.include_router(admin.router)
    dp.include_router(update_router)

    await set_bot_commands(bot)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_reminders,
        "interval",
        hours=settings.reminder_interval_hours,
        args=[bot],
        id="reminder_job",
    )
    scheduler.add_job(
        send_friday_reminders,
        "cron",
        day_of_week="fri",
        hour=settings.friday_reminder_hour,
        minute=settings.friday_reminder_minute,
        args=[bot],
        id="friday_reminder_job",
    )
    scheduler.start()
    logger.info("scheduler_started", jobs_count=len(scheduler.get_jobs()))

    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("shutdown_signal_received")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            asyncio.get_event_loop().add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    logger.info("bot_polling_started")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    done, pending = await asyncio.wait(
        [polling_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    scheduler.shutdown(wait=True)

    await redis.aclose()
    await storage.close()
    await bot.session.close()
    await engine.dispose()
    logger.info("bot_shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())