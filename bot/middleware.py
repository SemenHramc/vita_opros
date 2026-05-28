import time

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis

from bot.logging_config import get_logger

logger = get_logger(__name__)


class RedisRateLimitMiddleware(BaseMiddleware):

    def __init__(self, redis: Redis, limit: int, window: int):
        self.redis = redis
        self.limit = limit
        self.window = window

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id
        elif hasattr(event, "message") and event.message and getattr(event.message, "from_user", None):
            user_id = event.message.from_user.id

        if user_id:
            key = f"rate_limit:{user_id}"
            now = time.time()
            pipe = self.redis.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - self.window)
            pipe.zcard(key)
            pipe.expire(key, self.window)
            results = await pipe.execute()

            count = results[2]
            if count > self.limit:
                logger.warning("rate_limit_exceeded", user_id=user_id)
                await event.answer(
                    "\u041f\u043e\u0434\u043e\u0436\u0434\u0438\u0442\u0435 \u0447\u0443\u0442\u044c, \u0441\u043b\u0438\u0448\u043a\u043e\u043c \u043c\u043d\u043e\u0433\u043e \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0439. \u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
                )
                return None

        return await handler(event, data)