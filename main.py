"""App instance."""
import asyncio
from contextlib import suppress
from typing import Optional

import fastapi
import pydantic

from config import settings
from database import redis
from database import storage

app = fastapi.FastAPI()
listener_task: Optional[asyncio.Task] = None


class PublishMessage(pydantic.BaseModel):
    message: str = pydantic.Field(min_length=1, max_length=5000)


@app.post("/publish/", status_code=202)
async def publish_message(data: PublishMessage):
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
    try:
        messages, next_cursor = await storage.processor.get_messages(limit=limit, cursor=cursor)
        return {"messages": messages, "next_cursor": next_cursor}
    except ValueError as exc:
        raise fastapi.HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise fastapi.HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health/")
async def health_check():
    try:
        redis_ok = await redis.redis_client.ping()
        mongo_ok = await storage.processor.ping()
        return {"redis": bool(redis_ok), "mongo": bool(mongo_ok)}
    except Exception as exc:
        raise fastapi.HTTPException(status_code=500, detail=str(exc)) from exc


@app.on_event("startup")
async def startup_event():
    global listener_task
    await storage.processor.ensure_indexes()
    listener_task = asyncio.create_task(redis.listen_redis())


@app.on_event("shutdown")
async def shutdown_event():
    if listener_task:
        listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await listener_task

    await redis.redis_client.aclose()
    storage.processor.close()
