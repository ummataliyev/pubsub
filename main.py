"""FastAPI app entrypoint for the Pub/Sub example service."""
import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from contextlib import asynccontextmanager
from typing import Optional

import fastapi
import pydantic

from config.settings import settings
import database.redis as redis
import database.storage as storage

listener_task: Optional[asyncio.Task] = None


class PublishMessage(pydantic.BaseModel):
    """Request payload for publishing a message."""

    message: str = pydantic.Field(min_length=1, max_length=5000)


@asynccontextmanager
async def lifespan(_: fastapi.FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle.

    :param _: FastAPI application instance.
    :return: Async iterator used by FastAPI lifespan hooks.
    """
    global listener_task
    await storage.processor.ensure_indexes()
    listener_task = asyncio.create_task(redis.listen_redis())
    try:
        yield
    finally:
        if listener_task:
            listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await listener_task

        await redis.redis_client.aclose()
        storage.processor.close()


app = fastapi.FastAPI(lifespan=lifespan)


@app.post("/publish/", status_code=202)
async def publish_message(data: PublishMessage):
    """Publish a message to the configured Redis channel.

    :param data: Request body with the message to publish.
    :return: A small accepted status payload.
    :raises fastapi.HTTPException: If publishing fails.
    """
    try:
        await redis.redis_client.publish(settings.REDIS_CHANNEL, data.message)
        return {"status": "accepted"}
    except Exception as exc:
        raise fastapi.HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/messages/")
async def get_messages(
    limit: int = fastapi.Query(
        settings.DEFAULT_MESSAGES_LIMIT,
        ge=1,
        le=settings.MAX_MESSAGES_LIMIT,
    ),
    cursor: str | None = None,
):
    """Return stored messages with cursor-based pagination.

    :param limit: Maximum number of messages to return.
    :param cursor: Optional cursor for the next page.
    :return: Messages and an optional next cursor.
    :raises fastapi.HTTPException: For invalid cursor or internal errors.
    """
    try:
        messages, next_cursor = await storage.processor.get_messages(limit=limit, cursor=cursor)
        return {"messages": messages, "next_cursor": next_cursor}
    except ValueError as exc:
        raise fastapi.HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise fastapi.HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health/")
async def health_check():
    """Report connectivity to Redis and MongoDB.

    :return: Health status for Redis and MongoDB.
    :raises fastapi.HTTPException: If checks fail unexpectedly.
    """
    try:
        redis_ok = await redis.redis_client.ping()
        mongo_ok = await storage.processor.ping()
        return {"redis": bool(redis_ok), "mongo": bool(mongo_ok)}
    except Exception as exc:
        raise fastapi.HTTPException(status_code=500, detail=str(exc)) from exc
