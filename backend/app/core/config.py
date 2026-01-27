"""App configuration."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Runtime settings sourced from environment variables."""

    env: str = os.getenv("ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")


def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()

