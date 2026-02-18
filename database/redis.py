import asyncio

from contextlib import suppress

from redis.asyncio import Redis

from config import settings
from database import storage


redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=False,
)


async def listen_redis():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(settings.REDIS_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            data = message.get("data")
            if isinstance(data, bytes):
                payload = data.decode("utf-8")
            else:
                payload = str(data)

            await storage.processor.insert_message(payload)
    except asyncio.CancelledError:
        raise
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(settings.REDIS_CHANNEL)
            await pubsub.aclose()
