"""New FastAPI entrypoint for Railway deployment."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.db import models  # noqa: F401


settings = get_settings()

app = FastAPI(title="OutsideGroup Bets API", version="1.0.0")

allowed_origins = [
    origin.strip()
    for origin in (os.getenv("ALLOWED_ORIGINS", "")).split(",")
    if origin.strip()
]

if not allowed_origins:
    allowed_origins = [
        "https://bets.outsidegroup.co.uk",
        "https://outsidegroup.co.uk",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def _should_auto_create_tables() -> bool:
    value = os.getenv("AUTO_CREATE_TABLES", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


@app.on_event("startup")
def _startup_create_tables() -> None:
    if _should_auto_create_tables():
        Base.metadata.create_all(bind=engine)

