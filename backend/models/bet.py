"""Pydantic models for bet logging."""
from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field
from enum import Enum


class BetType(str, Enum):
    """Type of bet."""
    QUALIFYING = "qualifying"
    FREE_BET_SNR = "free_bet_snr"
    FREE_BET_SR = "free_bet_sr"


class BetOutcome(str, Enum):
    """Outcome of a bet."""
    PENDING = "pending"
    BACK_WON = "back_won"
    LAY_WON = "lay_won"


class LogBetRequest(BaseModel):
    """Request model for logging a new bet."""
    offer_id: Optional[str] = Field(None, description="Associated offer ID")
    bet_type: BetType = Field(..., description="Type of bet")
    bookmaker: str = Field(..., description="Bookmaker name")
    exchange: str = Field(default="Betfair", description="Exchange name")
    event_name: str = Field(..., description="Event name (e.g., 'Arsenal vs Chelsea')")
    selection: str = Field(..., description="Selection (e.g., 'Arsenal')")
    event_date: Optional[str] = Field(None, description="Event date/time (ISO format string)")
    back_odds: float = Field(..., gt=1.0, description="Back odds")
    back_stake: float = Field(..., gt=0, description="Back stake")
    lay_odds: float = Field(..., gt=1.0, description="Lay odds")
    lay_stake: float = Field(..., gt=0, description="Lay stake")
    liability: float = Field(..., gt=0, description="Exchange liability")
    commission: float = Field(default=0.05, description="Exchange commission rate")
    expected_profit: float = Field(..., description="Expected profit/loss")
    notes: Optional[str] = Field(None, description="Notes")


class Bet(BaseModel):
    """Bet record."""
    id: str
    user_id: str
    offer_id: Optional[str] = None
    bet_type: BetType
    bookmaker: str
    exchange: str
    event_name: str
    selection: str
    event_date: Optional[datetime] = None
    back_odds: float
    back_stake: float
    lay_odds: float
    lay_stake: float
    liability: float
    commission: float
    expected_profit: float
    actual_profit: Optional[float] = None
    outcome: BetOutcome = BetOutcome.PENDING
    notes: Optional[str] = None
    created_at: datetime
    settled_at: Optional[datetime] = None


class SettleBetRequest(BaseModel):
    """Request model for settling a bet."""
    outcome: BetOutcome = Field(..., description="Outcome of the bet")
    actual_profit: Optional[float] = Field(None, description="Actual profit (auto-calculated if not provided)")


class UpdateBetRequest(BaseModel):
    """Request model for updating a bet."""
    notes: Optional[str] = None
    event_date: Optional[datetime] = None


class BetsResponse(BaseModel):
    """Response model for listing bets."""
    bets: List[Bet]
    total: int
    pending_count: int
    settled_count: int
    total_profit: float


class BetStats(BaseModel):
    """Betting statistics."""
    total_bets: int = 0
    pending_bets: int = 0
    settled_bets: int = 0
    total_profit: float = 0.0
    total_stake: float = 0.0
    total_liability: float = 0.0
    avg_profit_per_bet: float = 0.0
    best_profit: float = 0.0
    worst_loss: float = 0.0
    qualifying_bets: int = 0
    free_bets: int = 0
    profit_by_bookmaker: dict = {}
    profit_by_month: List[dict] = []

