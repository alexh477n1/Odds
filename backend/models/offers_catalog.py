"""Pydantic models for the offers catalog and user offer progress."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class OfferType(str, Enum):
    """Type of betting offer."""
    WELCOME = "welcome"
    RELOAD = "reload"
    FREE_BET = "free_bet"
    RISK_FREE = "risk_free"
    ENHANCED_ODDS = "enhanced_odds"
    CASHBACK = "cashback"
    OTHER = "other"


class OfferDifficulty(str, Enum):
    """Difficulty level of completing the offer."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class OfferStage(str, Enum):
    """Stage in the offer completion flow."""
    DISCOVERED = "discovered"
    SELECTED = "selected"
    SIGNING_UP = "signing_up"
    ACCOUNT_CREATED = "account_created"
    VERIFIED = "verified"
    QUALIFYING_PENDING = "qualifying_pending"
    QUALIFYING_PLACED = "qualifying_placed"
    QUALIFYING_SETTLED = "qualifying_settled"
    FREE_BET_PENDING = "free_bet_pending"
    FREE_BET_AVAILABLE = "free_bet_available"
    FREE_BET_PLACED = "free_bet_placed"
    FREE_BET_SETTLED = "free_bet_settled"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    EXPIRED = "expired"
    FAILED = "failed"


# ============================================================================
# OFFERS CATALOG MODELS
# ============================================================================

class OfferCatalogBase(BaseModel):
    """Base model for offer catalog entries."""
    bookmaker: str = Field(..., description="Bookmaker name")
    offer_name: str = Field(..., description="Offer title/name")
    offer_type: OfferType = Field(default=OfferType.WELCOME)
    
    # Value details
    offer_value: Optional[float] = Field(None, description="Value of free bet/bonus")
    required_stake: Optional[float] = Field(None, description="Stake required")
    min_odds: Optional[float] = Field(None, description="Minimum odds required")
    max_stake: Optional[float] = Field(None, description="Maximum qualifying stake")
    
    # Requirements
    wagering_requirement: Optional[float] = Field(None, description="Wagering multiplier (e.g., 1x, 3x)")
    is_stake_returned: bool = Field(default=False, description="SR vs SNR")
    qualifying_bet_required: bool = Field(default=True)
    
    # Terms
    terms_raw: Optional[str] = Field(None, description="Raw terms text")
    terms_summary: Optional[str] = Field(None, description="Parsed summary")
    expiry_days: Optional[int] = Field(None, description="Days until offer expires")
    eligible_sports: Optional[List[str]] = Field(default=None, description="Allowed sports")
    eligible_markets: Optional[List[str]] = Field(default=None, description="Allowed markets")
    
    # Links
    signup_url: Optional[str] = Field(None, description="Direct signup URL")
    referral_url: Optional[str] = Field(None, description="Referral/affiliate URL")
    oddschecker_url: Optional[str] = Field(None, description="Oddschecker comparison URL")
    
    # Metadata
    difficulty: Optional[OfferDifficulty] = Field(default=OfferDifficulty.EASY)
    expected_profit: Optional[float] = Field(None, description="Expected profit")
    estimated_time_minutes: Optional[int] = Field(None, description="Time to complete")


class OfferCatalogCreate(OfferCatalogBase):
    """Request model for creating an offer."""
    pass


class OfferCatalog(OfferCatalogBase):
    """Full offer catalog entry."""
    id: str
    is_active: bool = True
    priority_rank: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
    }


class OfferCatalogListResponse(BaseModel):
    """Response for listing offers."""
    offers: List[OfferCatalog]
    total: int


# ============================================================================
# USER OFFER PROGRESS MODELS
# ============================================================================

class UserOfferProgressBase(BaseModel):
    """Base model for user offer progress."""
    stage: OfferStage = Field(default=OfferStage.DISCOVERED)
    notes: Optional[str] = None


class UserOfferProgressCreate(BaseModel):
    """Request to start an offer."""
    offer_id: str


class UserOfferProgressUpdate(BaseModel):
    """Request to update offer progress."""
    stage: Optional[OfferStage] = None
    notes: Optional[str] = None
    qualifying_bet_id: Optional[str] = None
    qualifying_stake: Optional[float] = None
    qualifying_odds: Optional[float] = None
    qualifying_loss: Optional[float] = None
    free_bet_id: Optional[str] = None
    free_bet_value: Optional[float] = None
    free_bet_profit: Optional[float] = None


class UserOfferProgress(BaseModel):
    """Full user offer progress record."""
    id: str
    user_id: str
    offer_id: str
    offer: Optional[OfferCatalog] = None  # Joined offer data
    
    stage: OfferStage
    
    # Qualifying bet tracking
    qualifying_bet_id: Optional[str] = None
    qualifying_stake: Optional[float] = None
    qualifying_odds: Optional[float] = None
    qualifying_loss: Optional[float] = None
    
    # Free bet tracking
    free_bet_id: Optional[str] = None
    free_bet_value: Optional[float] = None
    free_bet_profit: Optional[float] = None
    
    # Totals
    total_profit: Optional[float] = None
    
    notes: Optional[str] = None
    
    # Timestamps
    started_at: datetime
    signed_up_at: Optional[datetime] = None
    qualifying_placed_at: Optional[datetime] = None
    free_bet_received_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ActiveOffersResponse(BaseModel):
    """Response for user's active offers."""
    offers: List[UserOfferProgress]
    total_active: int
    total_completed: int
    total_profit: float


# ============================================================================
# BOOKMAKER PREFERENCES
# ============================================================================

class BookmakerPreference(str, Enum):
    """Preference type for a bookmaker."""
    WHITELIST = "whitelist"
    BLACKLIST = "blacklist"


class BookmakerPreferenceItem(BaseModel):
    """Single bookmaker preference."""
    bookmaker: str
    preference: BookmakerPreference


class BookmakerPreferencesUpdate(BaseModel):
    """Request to update bookmaker preferences."""
    preferences: List[BookmakerPreferenceItem]


class BookmakerPreferencesResponse(BaseModel):
    """Response with user's bookmaker preferences."""
    whitelist: List[str]
    blacklist: List[str]


# ============================================================================
# ONBOARDING
# ============================================================================

class OnboardingStep(str, Enum):
    """Onboarding steps."""
    WELCOME = "welcome"
    BOOKMAKER_PREFS = "bookmaker_prefs"
    SELECT_OFFERS = "select_offers"
    COMPLETED = "completed"


class OnboardingStatus(BaseModel):
    """User's onboarding status."""
    completed: bool
    current_step: OnboardingStep


class OnboardingUpdate(BaseModel):
    """Request to update onboarding."""
    step: OnboardingStep
    completed: Optional[bool] = None


# ============================================================================
# STAGE TRANSITIONS
# ============================================================================

STAGE_TRANSITIONS = {
    OfferStage.DISCOVERED: [OfferStage.SELECTED, OfferStage.SKIPPED],
    OfferStage.SELECTED: [OfferStage.SIGNING_UP, OfferStage.SKIPPED],
    OfferStage.SIGNING_UP: [OfferStage.ACCOUNT_CREATED, OfferStage.FAILED],
    OfferStage.ACCOUNT_CREATED: [OfferStage.VERIFIED, OfferStage.QUALIFYING_PENDING, OfferStage.QUALIFYING_PLACED],
    OfferStage.VERIFIED: [OfferStage.QUALIFYING_PENDING, OfferStage.QUALIFYING_PLACED],  # Allow direct placement
    OfferStage.QUALIFYING_PENDING: [OfferStage.QUALIFYING_PLACED, OfferStage.SKIPPED],
    OfferStage.QUALIFYING_PLACED: [OfferStage.QUALIFYING_SETTLED],
    OfferStage.QUALIFYING_SETTLED: [OfferStage.FREE_BET_PENDING, OfferStage.FREE_BET_AVAILABLE],
    OfferStage.FREE_BET_PENDING: [OfferStage.FREE_BET_AVAILABLE, OfferStage.EXPIRED],
    OfferStage.FREE_BET_AVAILABLE: [OfferStage.FREE_BET_PLACED],
    OfferStage.FREE_BET_PLACED: [OfferStage.FREE_BET_SETTLED],
    OfferStage.FREE_BET_SETTLED: [OfferStage.COMPLETED],
    OfferStage.COMPLETED: [],
    OfferStage.SKIPPED: [],
    OfferStage.EXPIRED: [],
    OfferStage.FAILED: [OfferStage.SELECTED],  # Can retry
}


STAGE_ACTIONS = {
    OfferStage.DISCOVERED: "Start This Offer",
    OfferStage.SELECTED: "Sign Up Now",
    OfferStage.SIGNING_UP: "I've Signed Up",
    OfferStage.ACCOUNT_CREATED: "Mark as Verified",
    OfferStage.VERIFIED: "View Games",
    OfferStage.QUALIFYING_PENDING: "View Games",
    OfferStage.QUALIFYING_PLACED: "Confirm Result",
    OfferStage.QUALIFYING_SETTLED: "Check for Free Bet",
    OfferStage.FREE_BET_PENDING: "Confirm Free Bet Received",
    OfferStage.FREE_BET_AVAILABLE: "View Games",
    OfferStage.FREE_BET_PLACED: "Confirm Result",
    OfferStage.FREE_BET_SETTLED: "Complete Offer",
    OfferStage.COMPLETED: "View Summary",
}


