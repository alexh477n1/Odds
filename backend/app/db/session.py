"""SQLAlchemy engine/session helpers."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import get_settings


_settings = get_settings()


def _normalize_database_url(url: str) -> str:
    if not url:
        raise RuntimeError("DATABASE_URL is not set.")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)

    if "pooler.supabase.com" in url and "sslmode=" not in url:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}sslmode=require"

    return url


_database_url = _normalize_database_url(_settings.database_url)
_engine_kwargs = {"pool_pre_ping": True, "future": True}

if _database_url.startswith("sqlite") and ":memory:" in _database_url:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(
    _database_url,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency to provide a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

