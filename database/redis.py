from redis.asyncio import Redis

from database import storage


redis_client = Redis(host='localhost', port=6379, db=0)


async def listen_redis():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("messages")
    async for message in pubsub.listen():
        if message["type"] == "message":
            print(message)
            await storage.processor.insert_message(message['data'].decode())
            print(f"Received message: {message['data'].decode()}")
