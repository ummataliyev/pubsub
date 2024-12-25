"""
Storage registration
"""
import typing

from motor import motor_asyncio

from config import settings


class MongoDB:
    """
    MongoDB configuration
    """
    def __init__(self, uri: str):
        self.client = motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client['pubsub']
        self.collection = self.db['messages']

    async def insert_message(self, message: str):
        await self.collection.insert_one({"message": message})

    async def get_messages(self) -> typing.List[str]:
        messages = await self.collection.find().to_list(length=100)
        return [msg["message"] for msg in messages]


processor = MongoDB(settings.MONGODB_URI)
