"""Pydantic models for match data and matched betting pairings."""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class BookmakerOdds(BaseModel):
    """Odds from a single bookmaker for a match."""
    bookmaker_key: str = Field(..., description="Bookmaker identifier")
    bookmaker_title: str = Field(..., description="Bookmaker display name")
    home_odds: float = Field(..., description="Odds for home team win")
    draw_odds: Optional[float] = Field(None, description="Odds for draw (if applicable)")
    away_odds: float = Field(..., description="Odds for away team win")
    last_update: datetime = Field(..., description="When odds were last updated")


class Match(BaseModel):
    """Basic match information from The-Odds-API."""
    match_id: str = Field(..., description="Unique match identifier")
    sport_key: str = Field(..., description="Sport/league identifier")
    sport_title: str = Field(..., description="Sport/league display name")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    commence_time: datetime = Field(..., description="Match start time")
    bookmaker_odds: List[BookmakerOdds] = Field(default_factory=list, description="Odds from all bookmakers")
    
    @property
    def display_name(self) -> str:
        """Return formatted match name."""
        return f"{self.home_team} vs {self.away_team}"
    
    @property
    def hours_until_start(self) -> float:
        """Hours until match starts."""
        delta = self.commence_time - datetime.now(self.commence_time.tzinfo)
        return delta.total_seconds() / 3600


class MatchPairing(BaseModel):
    """A Back/Lay pairing for matched betting."""
    match_id: str = Field(..., description="Match identifier")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    league: str = Field(..., description="League name")
    commence_time: datetime = Field(..., description="Match start time")
    
    # The outcome we're betting on
    outcome: str = Field(..., description="Outcome: 'home', 'draw', or 'away'")
    outcome_name: str = Field(..., description="Team/outcome display name")
    
    # Back bet details (at bookmaker)
    back_bookmaker: str = Field(..., description="Bookmaker for back bet")
    back_odds: float = Field(..., description="Back odds at bookmaker")
    
    # Lay bet details (at exchange)
    lay_exchange: str = Field(default="Betfair", description="Exchange for lay bet")
    lay_odds: float = Field(..., description="Lay odds at exchange")
    
    # Calculated values
    spread_percent: float = Field(..., description="Percentage difference between back and lay")
    
    @property
    def display_name(self) -> str:
        """Return formatted match name."""
        return f"{self.home_team} vs {self.away_team}"


class MatchRecommendation(MatchPairing):
    """Match pairing with profit calculations and rating."""
    # Rating and ranking
    match_rating: float = Field(..., description="Overall match rating (0-10)")
    
    # Profit calculations (for a given stake)
    stake: float = Field(default=10.0, description="Back stake amount")
    lay_stake: float = Field(..., description="Calculated lay stake")
    liability: float = Field(..., description="Exchange liability")
    
    # Profit scenarios
    qualifying_loss: float = Field(..., description="Loss when qualifying (normal bet)")
    free_bet_profit: float = Field(..., description="Profit when using free bet (SNR)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "match_id": "abc123",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "Premier League",
                "commence_time": "2024-01-15T15:00:00Z",
                "outcome": "home",
                "outcome_name": "Arsenal",
                "back_bookmaker": "Coral",
                "back_odds": 2.10,
                "lay_exchange": "Betfair",
                "lay_odds": 2.12,
                "spread_percent": 0.95,
                "match_rating": 9.5,
                "stake": 10.0,
                "lay_stake": 9.81,
                "liability": 10.98,
                "qualifying_loss": 0.10,
                "free_bet_profit": 4.50
            }
        }


class FindMatchesResponse(BaseModel):
    """Response model for /find-matches endpoint."""
    success: bool = Field(default=True)
    offer_id: Optional[str] = Field(None, description="Offer ID if specified")
    min_odds_filter: float = Field(..., description="Minimum odds filter applied")
    matches_found: int = Field(..., description="Total matches found before filtering")
    matches_with_exchange: int = Field(..., description="Matches with Betfair Exchange odds")
    recommendations: List[MatchRecommendation] = Field(..., description="Ranked match recommendations")
    api_requests_remaining: Optional[int] = Field(None, description="The-Odds-API requests remaining")







