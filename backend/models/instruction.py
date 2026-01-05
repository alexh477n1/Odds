"""Pydantic models for betting instruction generation."""
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.models.calculator import BetType


class InstructionStep(BaseModel):
    """A single step in the betting instructions."""
    step_number: int = Field(..., description="Step number")
    action: str = Field(..., description="What to do")
    platform: str = Field(..., description="Where to do it (bookmaker/exchange)")
    details: str = Field(..., description="Specific details (odds, stake, etc.)")
    warning: Optional[str] = Field(None, description="Important warning or note")


class InstructionRequest(BaseModel):
    """Request for generating betting instructions."""
    # Match details
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    outcome: str = Field(..., description="Outcome to bet on: 'home', 'draw', or 'away'")
    
    # Odds
    back_odds: float = Field(..., gt=1.0, description="Back odds at bookmaker")
    lay_odds: float = Field(..., gt=1.0, description="Lay odds at exchange")
    
    # Bookmaker/Exchange
    bookmaker: str = Field(..., description="Bookmaker name")
    exchange: str = Field(default="Betfair", description="Exchange name")
    
    # Bet details
    stake: float = Field(..., gt=0, description="Back stake amount")
    bet_type: BetType = Field(default=BetType.QUALIFYING, description="Type of bet")
    commission: float = Field(default=0.05, description="Exchange commission")
    
    # Optional offer context
    offer_name: Optional[str] = Field(None, description="Name of the offer (e.g., 'Bet £10 Get £10')")
    min_odds_required: Optional[float] = Field(None, description="Minimum odds required by offer")
    
    class Config:
        json_schema_extra = {
            "example": {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "outcome": "home",
                "back_odds": 2.10,
                "lay_odds": 2.12,
                "bookmaker": "Coral",
                "exchange": "Betfair",
                "stake": 10.0,
                "bet_type": "qualifying",
                "commission": 0.05,
                "offer_name": "Bet £10 Get £10 Free Bet",
                "min_odds_required": 2.0
            }
        }


class InstructionResponse(BaseModel):
    """Response with betting instructions."""
    # Summary
    title: str = Field(..., description="Instruction title")
    summary: str = Field(..., description="Quick summary of what you're doing")
    
    # The steps
    steps: List[InstructionStep] = Field(..., description="Step-by-step instructions")
    
    # Financial summary
    lay_stake: float = Field(..., description="Amount to lay")
    liability: float = Field(..., description="Exchange liability")
    expected_result: float = Field(..., description="Expected profit or loss")
    result_description: str = Field(..., description="Description of expected result")
    
    # Warnings and notes
    warnings: List[str] = Field(default_factory=list, description="Important warnings")
    tips: List[str] = Field(default_factory=list, description="Helpful tips")
    
    # Raw text version for copy/paste
    plain_text: str = Field(..., description="Plain text version of instructions")


class FullOfferInstructionRequest(BaseModel):
    """Request for full offer instructions (qualifying + free bet)."""
    # Match details
    home_team: str
    away_team: str
    outcome: str
    
    # Odds
    back_odds: float
    lay_odds: float
    
    # Bookmaker/Exchange
    bookmaker: str
    exchange: str = "Betfair"
    
    # Offer details
    qualifying_stake: float = Field(..., description="Amount to stake to qualify")
    free_bet_value: float = Field(..., description="Value of free bet received")
    commission: float = 0.05
    
    # Offer context
    offer_name: str = Field(..., description="Name of the offer")
    min_odds_required: Optional[float] = None


class FullOfferInstructionResponse(BaseModel):
    """Response with full offer instructions (qualifying + free bet)."""
    offer_name: str
    
    # Part 1: Qualifying bet
    qualifying_instructions: InstructionResponse
    
    # Part 2: Free bet
    free_bet_instructions: InstructionResponse
    
    # Total summary
    total_qualifying_loss: float
    total_free_bet_profit: float
    total_profit: float
    profit_summary: str
    
    # Full plain text
    full_plain_text: str







