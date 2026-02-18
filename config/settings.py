"""Application settings loaded from environment variables."""

from environs import Env


class Settings:
    """Typed settings container for service configuration."""

    def __init__(self):
        """Load configuration from environment or default values.

        :return: None
        """
        env = Env()
        env.read_env()

        self.MONGODB_URI = env.str("MONGODB_URI", "mongodb://localhost:27017")
        self.REDIS_HOST = env.str("REDIS_HOST", "localhost")
        self.REDIS_PORT = env.int("REDIS_PORT", 6379)
        self.REDIS_DB = env.int("REDIS_DB", 0)
        self.REDIS_CHANNEL = env.str("REDIS_CHANNEL", "messages")
        self.DEFAULT_MESSAGES_LIMIT = env.int("DEFAULT_MESSAGES_LIMIT", 50)
        self.MAX_MESSAGES_LIMIT = env.int("MAX_MESSAGES_LIMIT", 200)


settings = Settings()
