"""Pydantic models for betting offers."""
from typing import Optional
from pydantic import BaseModel, Field


class OfferRaw(BaseModel):
    """Raw offer data extracted from scraper."""
    raw_text: str = Field(..., description="Raw text content from the offer card")
    bookmaker_hint: Optional[str] = Field(None, description="Bookmaker name hint from logo/heading")


class OfferParsed(BaseModel):
    """Structured offer data parsed by LLM."""
    bookmaker: str = Field(..., description="Name of the bookmaker")
    offer_value: Optional[float] = Field(None, description="Total monetary value of free bets")
    required_stake: Optional[float] = Field(None, description="Amount user must stake to qualify")
    min_odds: Optional[float] = Field(None, description="Minimum odds required (decimal format)")
    expiry_days: Optional[int] = Field(None, description="Days until expiry")
    bet_type: str = Field(default="Unknown", description="Type of bet: SNR, Qualifying, Free Bet, Enhanced, Casino, Unknown")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bookmaker": "Bet365",
                "offer_value": 30.0,
                "required_stake": 10.0,
                "min_odds": 2.0,
                "expiry_days": 30,
                "bet_type": "SNR"
            }
        }


class OfferRanked(OfferParsed):
    """Offer with calculated value index and rank."""
    value_index: float = Field(..., description="Calculated value index (offer_value / required_stake)")
    rank: int = Field(..., description="Ranking position (1 = best value)")
    raw_text: Optional[str] = Field(None, description="Original raw text for reference")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bookmaker": "Bet365",
                "offer_value": 30.0,
                "required_stake": 10.0,
                "min_odds": 2.0,
                "expiry_days": 30,
                "bet_type": "SNR",
                "value_index": 3.0,
                "rank": 1
            }
        }










