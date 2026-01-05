"""Pydantic models for saved offers."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class OfferStatus(str, Enum):
    """Status of a saved offer."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class SaveOfferRequest(BaseModel):
    """Request model for saving an offer."""
    bookmaker: str = Field(..., description="Bookmaker name")
    offer_name: str = Field(..., description="Name/description of the offer")
    offer_value: Optional[float] = Field(None, description="Value of free bet/bonus")
    required_stake: Optional[float] = Field(None, description="Stake required to qualify")
    min_odds: Optional[float] = Field(None, description="Minimum odds required")
    notes: Optional[str] = Field(None, description="User notes")
    expected_profit: Optional[float] = Field(None, description="Expected profit")


class SavedOffer(BaseModel):
    """Saved offer data."""
    id: str
    user_id: str
    bookmaker: str
    offer_name: str
    offer_value: Optional[float] = None
    required_stake: Optional[float] = None
    min_odds: Optional[float] = None
    status: OfferStatus = OfferStatus.PENDING
    notes: Optional[str] = None
    expected_profit: Optional[float] = None
    actual_profit: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class UpdateOfferRequest(BaseModel):
    """Request model for updating a saved offer."""
    status: Optional[OfferStatus] = None
    notes: Optional[str] = None
    actual_profit: Optional[float] = None


class SavedOffersResponse(BaseModel):
    """Response model for listing saved offers."""
    offers: List[SavedOffer]
    total: int
    pending_count: int
    in_progress_count: int
    completed_count: int





