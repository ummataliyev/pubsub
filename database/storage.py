"""MongoDB storage adapter for persisted messages."""
import datetime
import typing

from bson import ObjectId
from bson.errors import InvalidId
from motor import motor_asyncio

from config.settings import settings


class MongoDB:
    """MongoDB access layer for message writes and reads."""

    def __init__(self, uri: str):
        """Create MongoDB client and select db/collection.

        :param uri: MongoDB connection URI.
        :return: None
        """
        self.client = motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client["pubsub"]
        self.collection = self.db["messages"]

    async def ensure_indexes(self):
        """Create required indexes for the messages collection.

        :return: None
        """
        await self.collection.create_index([("created_at", -1)])

    async def ping(self) -> bool:
        """Check MongoDB availability.

        :return: True when ping succeeds.
        """
        await self.client.admin.command("ping")
        return True

    def close(self):
        """Close the MongoDB client.

        :return: None
        """
        self.client.close()

    async def insert_message(self, message: str):
        """Insert a message document with UTC timestamp.

        :param message: Message payload to persist.
        :return: None
        """
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
        """Fetch messages using cursor-based pagination.

        :param limit: Max number of items to return.
        :param cursor: Optional ObjectId cursor from previous page.
        :return: Tuple of messages and next cursor.
        :raises ValueError: If cursor is not a valid ObjectId.
        """
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
