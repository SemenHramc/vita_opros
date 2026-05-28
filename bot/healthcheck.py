import asyncio
import sys
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_redis(url: str) -> tuple[bool, str]:
    try:
        redis = Redis.from_url(url)
        await redis.ping()
        await redis.aclose()
        return True, "OK"
    except Exception as e:
        return False, str(e)


async def check_database(url: str) -> tuple[bool, str]:
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True, "OK"
    except Exception as e:
        return False, str(e)


async def main():
    redis_url = sys.argv[1] if len(sys.argv) > 1 else "redis://localhost:6379/0"
    database_url = sys.argv[2] if len(sys.argv) > 2 else "sqlite+aiosqlite:///./vita_opros.db"

    print(f"Checking Redis: {redis_url}")
    redis_ok, redis_msg = await check_redis(redis_url)
    print(f"Redis: {redis_msg}")

    print(f"Checking Database...")
    db_ok, db_msg = await check_database(database_url)
    print(f"Database: {db_msg}")

    if redis_ok and db_ok:
        print("Healthcheck PASSED")
        sys.exit(0)
    else:
        print("Healthcheck FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())