"""API dependencies (auth, admin)."""
from typing import Optional
import jwt
from fastapi import Header, HTTPException
from app.core.config import get_settings


def _decode_token(token: str) -> dict:
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_JWT_SECRET")
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def get_current_user(authorization: str = Header(..., alias="Authorization")) -> dict:
    """Extract and validate user from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth format")
    token = authorization.split(" ")[1]
    return _decode_token(token)


def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[dict]:
    """Extract user if auth header present, otherwise None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    return _decode_token(token)


def require_admin(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> dict:
    """Require admin access via token role or admin API key."""
    settings = get_settings()
    if settings.admin_api_key and admin_key == settings.admin_api_key:
        return {"role": "admin", "via": "admin_key"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing admin auth")

    user = _decode_token(authorization.split(" ")[1])
    role = user.get("role") or user.get("app_metadata", {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user

