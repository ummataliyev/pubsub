import asyncio

import pytest
from fastapi.testclient import TestClient

import main


class DummyRedisClient:
    def __init__(self):
        self.published = []
        self.closed = False

    async def publish(self, channel, message):
        self.published.append((channel, message))
        return 1

    async def ping(self):
        return True

    async def aclose(self):
        self.closed = True


class DummyStorageProcessor:
    def __init__(self):
        self.closed = False
        self.ensure_indexes_called = False
        self.messages = ["m1", "m2"]

    async def ensure_indexes(self):
        self.ensure_indexes_called = True

    async def ping(self):
        return True

    def close(self):
        self.closed = True

    async def get_messages(self, limit=50, cursor=None):
        return self.messages[:limit], None

    async def insert_message(self, message):
        return None


async def fake_listener():
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise


@pytest.fixture
def client(monkeypatch):
    redis_client = DummyRedisClient()
    processor = DummyStorageProcessor()

    monkeypatch.setattr(main.redis, "redis_client", redis_client)
    monkeypatch.setattr(main.redis, "listen_redis", fake_listener)
    monkeypatch.setattr(main.storage, "processor", processor)

    with TestClient(main.app) as test_client:
        yield test_client, redis_client, processor


def test_publish_message(client):
    test_client, redis_client, _ = client

    response = test_client.post("/publish/", json={"message": "hello"})

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert redis_client.published


def test_get_messages(client):
    test_client, _, _ = client

    response = test_client.get("/messages/?limit=2")

    assert response.status_code == 200
    assert response.json() == {"messages": ["m1", "m2"], "next_cursor": None}


def test_get_messages_invalid_cursor(client, monkeypatch):
    test_client, _, processor = client

    async def broken_get_messages(*args, **kwargs):
        raise ValueError("Invalid cursor")

    monkeypatch.setattr(processor, "get_messages", broken_get_messages)

    response = test_client.get("/messages/?cursor=bad")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid cursor"}


def test_health(client):
    test_client, _, _ = client

    response = test_client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"redis": True, "mongo": True}
