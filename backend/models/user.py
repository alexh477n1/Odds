"""Pydantic models for user authentication and profiles."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class UserRegister(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    username: Optional[str] = Field(None, description="Display name")


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")


class UserProfile(BaseModel):
    """User profile data."""
    id: str
    email: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    total_profit: float = 0.0
    created_at: datetime


class UserProfileUpdate(BaseModel):
    """Request model for updating user profile."""
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=604800, description="Token expiry in seconds (7 days)")
    user: UserProfile


class UserStats(BaseModel):
    """User statistics."""
    user_id: str
    total_offers: int = 0
    completed_offers: int = 0
    total_bets: int = 0
    settled_bets: int = 0
    total_profit: float = 0.0
    monthly_profit: float = 0.0
    weekly_profit: float = 0.0
    avg_profit_per_offer: float = 0.0





