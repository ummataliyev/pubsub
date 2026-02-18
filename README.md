# PubSub Example

This project is a small backend example that shows how to:

- publish messages through an API,
- process them through Redis Pub/Sub,
- store them in MongoDB,
- read them back with pagination.

It is intentionally simple and meant for learning/demo purposes.

## What Happens In This Project

1. Client sends `POST /publish/` with a message.
2. API publishes that message to a Redis channel.
3. Background listener receives the message from Redis.
4. Listener saves the message into MongoDB.
5. Client reads saved messages using `GET /messages/`.

## Tech Stack

- FastAPI: HTTP API
- Redis: Pub/Sub transport
- MongoDB (Motor): message storage

## API Endpoints

- `POST /publish/`
  - Body: `{"message":"hello world"}`
  - Result: publishes a message to Redis
- `GET /messages/?limit=10&cursor=<cursor>`
  - Result: returns saved messages and `next_cursor`
- `GET /health/`
  - Result: basic Redis and Mongo connectivity check

## Quick Start

1. Create env file:

```bash
cp .env.dist .env
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run API server:

```bash
uvicorn main:app --reload
```

## Example Requests

Publish:

```bash
curl -X POST http://127.0.0.1:8000/publish/ \
  -H "Content-Type: application/json" \
  -d '{"message":"hello world"}'
```

Read messages:

```bash
curl "http://127.0.0.1:8000/messages/?limit=10"
```

Health:

```bash
curl http://127.0.0.1:8000/health/
```

## Environment Variables

Defined in `.env.dist`:

- `MONGODB_URI`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB`
- `REDIS_CHANNEL`
- `DEFAULT_MESSAGES_LIMIT`
- `MAX_MESSAGES_LIMIT`

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```
