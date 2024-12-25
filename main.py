"""
App instance
"""
import fastapi
import asyncio
import pydantic
from redis.asyncio import Redis

from database import storage
from database import redis

app = fastapi.FastAPI()

redis_client = Redis(host='localhost', port=6379, db=0)


class PublishMessage(pydantic.BaseModel):
    message: str


@app.post("/publish/")
async def publish_message(data: PublishMessage):
    try:
        await redis_client.publish("messages", data.message)

        return {"status": "Message published and saved"}
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=str(e))


@app.get("/messages/")
async def get_messages():
    try:
        messages = await storage.processor.get_messages()
        return {"messages": messages}
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis.listen_redis())
    print("Starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()
    print("Shutting down...")
