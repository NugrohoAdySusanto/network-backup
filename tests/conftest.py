import os


# Safe test-only defaults so Settings can be imported without a real .env.
os.environ.setdefault("APP_SECRET", "test-secret-not-for-production")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SESSION_REDIS_URL", "redis://localhost:6379/14")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENABLE_MOCK_DRIVER", "false")
