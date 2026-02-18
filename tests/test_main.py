"""API tests with mocked Redis and Mongo dependencies."""
import asyncio

import pytest
from fastapi.testclient import TestClient

import main


class DummyRedisClient:
    """Minimal Redis client stub used by tests."""

    def __init__(self):
        self.published = []
        self.closed = False

    async def publish(self, channel, message):
        """Capture publish call arguments.

        :param channel: Redis channel name.
        :param message: Published message payload.
        :return: Integer publish count.
        """
        self.published.append((channel, message))
        return 1

    async def ping(self):
        """Mock successful health check.

        :return: Always True.
        """
        return True

    async def aclose(self):
        """Mark client as closed.

        :return: None
        """
        self.closed = True


class DummyStorageProcessor:
    """Minimal Mongo storage stub used by tests."""

    def __init__(self):
        self.closed = False
        self.ensure_indexes_called = False
        self.messages = ["m1", "m2"]

    async def ensure_indexes(self):
        """Track startup index creation call.

        :return: None
        """
        self.ensure_indexes_called = True

    async def ping(self):
        """Mock successful health check.

        :return: Always True.
        """
        return True

    def close(self):
        """Mark processor as closed.

        :return: None
        """
        self.closed = True

    async def get_messages(self, limit=50, cursor=None):
        """Return static paginated message list.

        :param limit: Requested limit.
        :param cursor: Optional cursor.
        :return: Tuple of list and no cursor.
        """
        return self.messages[:limit], None

    async def insert_message(self, message):
        """No-op insert used by listener tests.

        :param message: Message payload.
        :return: None
        """
        return None


async def fake_listener():
    """Simulate long-running listener task.

    :return: None
    """
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise


@pytest.fixture
def client(monkeypatch):
    """Create test client with mocked collaborators.

    :param monkeypatch: Pytest monkeypatch fixture.
    :return: Tuple of TestClient and stubs.
    """
    redis_client = DummyRedisClient()
    processor = DummyStorageProcessor()

    monkeypatch.setattr(main.redis, "redis_client", redis_client)
    monkeypatch.setattr(main.redis, "listen_redis", fake_listener)
    monkeypatch.setattr(main.storage, "processor", processor)

    with TestClient(main.app) as test_client:
        yield test_client, redis_client, processor


def test_publish_message(client):
    """Ensure publish endpoint accepts and forwards message.

    :param client: Client fixture tuple.
    :return: None
    """
    test_client, redis_client, _ = client

    response = test_client.post("/publish/", json={"message": "hello"})

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert redis_client.published


def test_get_messages(client):
    """Ensure messages endpoint returns expected payload.

    :param client: Client fixture tuple.
    :return: None
    """
    test_client, _, _ = client

    response = test_client.get("/messages/?limit=2")

    assert response.status_code == 200
    assert response.json() == {"messages": ["m1", "m2"], "next_cursor": None}


def test_get_messages_invalid_cursor(client, monkeypatch):
    """Ensure invalid cursor maps to HTTP 400.

    :param client: Client fixture tuple.
    :param monkeypatch: Pytest monkeypatch fixture.
    :return: None
    """
    test_client, _, processor = client

    async def broken_get_messages(*args, **kwargs):
        raise ValueError("Invalid cursor")

    monkeypatch.setattr(processor, "get_messages", broken_get_messages)

    response = test_client.get("/messages/?cursor=bad")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid cursor"}


def test_health(client):
    """Ensure health endpoint reports both dependencies up.

    :param client: Client fixture tuple.
    :return: None
    """
    test_client, _, _ = client

    response = test_client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"redis": True, "mongo": True}
