"""Storage registration."""
import datetime
import typing

from bson import ObjectId
from bson.errors import InvalidId
from motor import motor_asyncio

from config import settings


class MongoDB:
    """MongoDB configuration."""

    def __init__(self, uri: str):
        self.client = motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client["pubsub"]
        self.collection = self.db["messages"]

    async def ensure_indexes(self):
        await self.collection.create_index([("created_at", -1)])

    async def ping(self) -> bool:
        await self.client.admin.command("ping")
        return True

    def close(self):
        self.client.close()

    async def insert_message(self, message: str):
        await self.collection.insert_one(
            {
                "message": message,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
            }
        )

    async def get_messages(
        self,
        limit: int = settings.DEFAULT_MESSAGES_LIMIT,
        cursor: str | None = None,
    ) -> typing.Tuple[typing.List[str], str | None]:
        query: dict[str, typing.Any] = {}
        if cursor:
            try:
                query["_id"] = {"$lt": ObjectId(cursor)}
            except InvalidId as exc:
                raise ValueError("Invalid cursor") from exc

        docs = (
            await self.collection.find(query)
            .sort("_id", -1)
            .limit(limit + 1)
            .to_list(length=limit + 1)
        )

        has_more = len(docs) > limit
        docs = docs[:limit]

        next_cursor = str(docs[-1]["_id"]) if docs and has_more else None
        return [msg["message"] for msg in docs], next_cursor


processor = MongoDB(settings.MONGODB_URI)
