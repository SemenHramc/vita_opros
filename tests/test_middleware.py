import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.middleware import RedisRateLimitMiddleware


class FakeRedis:
    def __init__(self):
        self._data = {}
        self._expires = {}

    def pipeline(self):
        return FakeRedisPipeline(self)

    async def aclose(self):
        pass


class FakeRedisPipeline:
    def __init__(self, redis):
        self.redis = redis
        self._zadd_result = 0
        self._zrem_result = 0
        self._zcard_result = 0
        self._expire_result = True

    def zadd(self, key, mapping):
        if key not in self.redis._data:
            self.redis._data[key] = {}
        self.redis._data[key].update(mapping)
        return self

    def zremrangebyscore(self, key, min_score, max_score):
        if key in self.redis._data:
            self.redis._data[key] = {
                k: v for k, v in self.redis._data[key].items()
                if v > max_score
            }
        return self

    def zcard(self, key):
        self._zcard_result = len(self.redis._data.get(key, {}))
        return self

    def expire(self, key, seconds):
        self.redis._expires[key] = seconds
        return self

    async def execute(self):
        return [self._zadd_result, self._zrem_result, self._zcard_result, self._expire_result]


class TestRedisRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=5, window=60)

        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 123

        timestamps = [1717200000.0 + i for i in range(5)]
        for ts in timestamps:
            with patch("bot.middleware.time") as mock_time:
                mock_time.time.return_value = ts
                result = await middleware(handler, event, {})
            assert result == "ok"

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=3, window=60)

        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 456

        timestamps = [1717200000.0 + i for i in range(4)]
        for i, ts in enumerate(timestamps[:3]):
            with patch("bot.middleware.time") as mock_time:
                mock_time.time.return_value = ts
                result = await middleware(handler, event, {})
            assert result == "ok"

        with patch("bot.middleware.time") as mock_time:
            mock_time.time.return_value = timestamps[3]
            result = await middleware(handler, event, {})
        assert result is None

    @pytest.mark.asyncio
    async def test_allows_anonymous_users(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=1, window=60)

        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = None
        event.message = MagicMock()
        event.message.from_user = None

        result = await middleware(handler, event, {})
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_separate_limits_per_user(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=2, window=60)

        handler = AsyncMock(return_value="ok")

        event1 = MagicMock()
        event1.from_user = MagicMock()
        event1.from_user.id = 100

        event2 = MagicMock()
        event2.from_user = MagicMock()
        event2.from_user.id = 200

        timestamps = [1717200000.0 + i for i in range(3)]
        with patch("bot.middleware.time") as mock_time:
            mock_time.time.return_value = timestamps[0]
            await middleware(handler, event1, {})
            mock_time.time.return_value = timestamps[1]
            await middleware(handler, event1, {})

        with patch("bot.middleware.time") as mock_time:
            mock_time.time.return_value = timestamps[2]
            result = await middleware(handler, event2, {})
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_extracts_user_from_callback_query(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=5, window=60)

        handler = AsyncMock(return_value="ok")
        event = MagicMock(spec=["from_user", "message"])
        event.from_user = MagicMock()
        event.from_user.id = 789

        with patch("bot.middleware.time") as mock_time:
            mock_time.time.return_value = 1717200000.0
            result = await middleware(handler, event, {})
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=3, window=60)

        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 456

        timestamps = [1717200000.0 + i for i in range(4)]
        for i in range(3):
            with patch("bot.middleware.time") as mock_time:
                mock_time.time.return_value = timestamps[i]
                result = await middleware(handler, event, {})
            assert result == "ok"

        with patch("bot.middleware.time") as mock_time:
            mock_time.time.return_value = timestamps[3]
            result = await middleware(handler, event, {})
        assert result is None

    @pytest.mark.asyncio
    async def test_allows_anonymous_users(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=1, window=60)

        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = None
        event.message = MagicMock()
        event.message.from_user = None

        result = await middleware(handler, event, {})
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_separate_limits_per_user(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=2, window=60)

        handler = AsyncMock(return_value="ok")

        event1 = MagicMock()
        event1.from_user = MagicMock()
        event1.from_user.id = 100
        event1.message = MagicMock()
        event1.message.from_user = MagicMock()
        event1.message.from_user.id = 100

        event2 = MagicMock()
        event2.from_user = MagicMock()
        event2.from_user.id = 200
        event2.message = MagicMock()
        event2.message.from_user = MagicMock()
        event2.message.from_user.id = 200

        await middleware(handler, event1, {})
        await middleware(handler, event1, {})

        result = await middleware(handler, event2, {})
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_extracts_user_from_callback_query(self):
        redis = FakeRedis()
        middleware = RedisRateLimitMiddleware(redis=redis, limit=5, window=60)

        handler = AsyncMock(return_value="ok")
        event = MagicMock(spec=["from_user", "message"])
        event.from_user = MagicMock()
        event.from_user.id = 789

        result = await middleware(handler, event, {})
        assert result == "ok"
