"""Pydantic models for matched betting calculator."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class BetType(str, Enum):
    """Type of matched bet."""
    QUALIFYING = "qualifying"  # Normal bet to unlock a free bet
    FREE_BET_SNR = "free_bet_snr"  # Free bet - Stake Not Returned
    FREE_BET_SR = "free_bet_sr"  # Free bet - Stake Returned (rare)


class CalcRequest(BaseModel):
    """Request model for matched betting calculator."""
    back_odds: float = Field(..., gt=1.0, description="Back odds at bookmaker")
    lay_odds: float = Field(..., gt=1.0, description="Lay odds at exchange")
    stake: float = Field(..., gt=0, description="Back stake amount")
    bet_type: BetType = Field(default=BetType.QUALIFYING, description="Type of bet")
    commission: float = Field(default=0.05, ge=0, le=0.2, description="Exchange commission (0.05 = 5%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "back_odds": 2.10,
                "lay_odds": 2.12,
                "stake": 10.0,
                "bet_type": "qualifying",
                "commission": 0.05
            }
        }


class OutcomeResult(BaseModel):
    """Profit/loss for a specific outcome."""
    outcome: str = Field(..., description="Outcome name (back_wins, lay_wins)")
    profit: float = Field(..., description="Profit if this outcome occurs (negative = loss)")
    description: str = Field(..., description="Human-readable description")


class CalcResponse(BaseModel):
    """Response model for matched betting calculator."""
    # Input echo
    back_odds: float
    lay_odds: float
    stake: float
    bet_type: BetType
    commission: float
    
    # Calculated values
    lay_stake: float = Field(..., description="Amount to lay at exchange")
    liability: float = Field(..., description="Potential loss at exchange if back bet wins")
    
    # Outcome breakdown
    outcomes: list[OutcomeResult] = Field(..., description="Profit/loss for each outcome")
    
    # Summary
    guaranteed_profit: float = Field(..., description="Minimum guaranteed profit (or max loss)")
    expected_value: float = Field(..., description="Expected value across outcomes")
    rating: str = Field(..., description="Quality rating: Excellent, Good, Fair, Poor")
    
    # Spread info
    spread_percent: float = Field(..., description="Spread between back and lay odds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "back_odds": 2.10,
                "lay_odds": 2.12,
                "stake": 10.0,
                "bet_type": "qualifying",
                "commission": 0.05,
                "lay_stake": 9.81,
                "liability": 10.98,
                "outcomes": [
                    {"outcome": "back_wins", "profit": -0.09, "description": "You win at bookmaker, lose at exchange"},
                    {"outcome": "lay_wins", "profit": -0.09, "description": "You lose at bookmaker, win at exchange"}
                ],
                "guaranteed_profit": -0.09,
                "expected_value": -0.09,
                "rating": "Excellent",
                "spread_percent": 0.95
            }
        }


class BatchCalcRequest(BaseModel):
    """Request for calculating multiple scenarios."""
    calculations: list[CalcRequest] = Field(..., min_length=1, max_length=20)


class BatchCalcResponse(BaseModel):
    """Response for batch calculations."""
    results: list[CalcResponse]
    total_guaranteed_profit: float
    best_opportunity: Optional[CalcResponse] = None










