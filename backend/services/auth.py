"""Authentication service for user management."""
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from backend.database.supabase_client import get_supabase_client
from backend.models.user import UserRegister, UserLogin, UserProfile, TokenResponse, UserStats

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "matchcaddy-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, email: str) -> str:
    """Create a JWT token for a user."""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def register_user(data: UserRegister) -> TokenResponse:
    """Register a new user."""
    supabase = get_supabase_client()
    
    # Check if email already exists
    existing = supabase.table("users").select("id").eq("email", data.email).execute()
    if existing.data:
        raise ValueError("Email already registered")
    
    # Hash password and create user
    password_hash = hash_password(data.password)
    
    user_data = {
        "email": data.email,
        "password_hash": password_hash,
        "username": data.username or data.email.split("@")[0],
        "total_profit": 0.0,
    }
    
    result = supabase.table("users").insert(user_data).execute()
    
    if not result.data:
        raise ValueError("Failed to create user")
    
    user = result.data[0]
    
    # Create token
    token = create_token(user["id"], user["email"])
    
    # Build profile
    profile = UserProfile(
        id=user["id"],
        email=user["email"],
        username=user.get("username"),
        avatar_url=user.get("avatar_url"),
        total_profit=float(user.get("total_profit", 0)),
        created_at=user["created_at"],
    )
    
    return TokenResponse(
        access_token=token,
        user=profile,
    )


async def login_user(data: UserLogin) -> TokenResponse:
    """Log in a user."""
    supabase = get_supabase_client()
    
    # Find user by email
    result = supabase.table("users").select("*").eq("email", data.email).execute()
    
    if not result.data:
        raise ValueError("Invalid email or password")
    
    user = result.data[0]
    
    # Verify password
    if not verify_password(data.password, user["password_hash"]):
        raise ValueError("Invalid email or password")
    
    # Create token
    token = create_token(user["id"], user["email"])
    
    # Build profile
    profile = UserProfile(
        id=user["id"],
        email=user["email"],
        username=user.get("username"),
        avatar_url=user.get("avatar_url"),
        total_profit=float(user.get("total_profit", 0)),
        created_at=user["created_at"],
    )
    
    return TokenResponse(
        access_token=token,
        user=profile,
    )


async def get_user_profile(user_id: str) -> UserProfile:
    """Get a user's profile."""
    supabase = get_supabase_client()
    
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    
    if not result.data:
        raise ValueError("User not found")
    
    user = result.data[0]
    
    return UserProfile(
        id=user["id"],
        email=user["email"],
        username=user.get("username"),
        avatar_url=user.get("avatar_url"),
        total_profit=float(user.get("total_profit", 0)),
        created_at=user["created_at"],
    )


async def update_user_profile(user_id: str, username: Optional[str] = None, avatar_url: Optional[str] = None) -> UserProfile:
    """Update a user's profile."""
    supabase = get_supabase_client()
    
    update_data = {}
    if username is not None:
        update_data["username"] = username
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url
    
    if not update_data:
        return await get_user_profile(user_id)
    
    result = supabase.table("users").update(update_data).eq("id", user_id).execute()
    
    if not result.data:
        raise ValueError("Failed to update profile")
    
    return await get_user_profile(user_id)


async def get_user_stats(user_id: str) -> UserStats:
    """Get a user's statistics."""
    supabase = get_supabase_client()
    
    # Get offer stats from V1 saved_offers
    offers_result = supabase.table("saved_offers").select("status").eq("user_id", user_id).execute()
    v1_offers = offers_result.data or []
    
    v1_total = len(v1_offers)
    v1_completed = len([o for o in v1_offers if o["status"] == "completed"])
    
    # Get offer stats from V3 user_offer_progress
    progress_result = supabase.table("user_offer_progress").select("stage").eq("user_id", user_id).execute()
    v3_offers = progress_result.data or []
    
    v3_total = len(v3_offers)
    v3_completed = len([o for o in v3_offers if o["stage"] == "completed"])
    
    # Combine both systems
    total_offers = v1_total + v3_total
    completed_offers = v1_completed + v3_completed
    
    # Get bet stats with date info
    bets_result = supabase.table("bets").select("outcome, actual_profit, created_at").eq("user_id", user_id).execute()
    bets = bets_result.data or []
    
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    total_bets = len(bets)
    settled_bets = len([b for b in bets if b["outcome"] != "pending"])
    total_profit = sum(float(b.get("actual_profit", 0) or 0) for b in bets if b["outcome"] != "pending")
    
    # Calculate weekly and monthly profits
    weekly_profit = 0.0
    monthly_profit = 0.0
    
    for b in bets:
        if b["outcome"] != "pending":
            profit = float(b.get("actual_profit", 0) or 0)
            bet_date_str = b.get("created_at")
            if bet_date_str:
                try:
                    # Parse ISO format date
                    if 'T' in bet_date_str:
                        bet_date = datetime.fromisoformat(bet_date_str.replace('Z', '+00:00').split('+')[0])
                    else:
                        bet_date = datetime.strptime(bet_date_str[:10], '%Y-%m-%d')
                    
                    if bet_date >= week_ago:
                        weekly_profit += profit
                    if bet_date >= month_ago:
                        monthly_profit += profit
                except (ValueError, TypeError):
                    pass
    
    # Calculate averages
    avg_profit = total_profit / completed_offers if completed_offers > 0 else 0
    
    return UserStats(
        user_id=user_id,
        total_offers=total_offers,
        completed_offers=completed_offers,
        total_bets=total_bets,
        settled_bets=settled_bets,
        total_profit=round(total_profit, 2),
        monthly_profit=round(monthly_profit, 2),
        weekly_profit=round(weekly_profit, 2),
        avg_profit_per_offer=round(avg_profit, 2),
    )


def get_current_user(token: str) -> Optional[dict]:
    """Get the current user from a token."""
    payload = decode_token(token)
    if not payload:
        return None
    return {
        "user_id": payload["sub"],
        "email": payload["email"],
    }





