"""Match finder endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from config import Config
from models.match import FindMatchesResponse
from app.services.odds_api_client import OddsAPIClient
from utils.match_filtering import (
    filter_matches_by_league,
    filter_matches_by_odds_range,
    find_best_pairings,
    create_recommendations,
)


router = APIRouter(tags=["Matches"])


@router.get("/find-matches", response_model=FindMatchesResponse)
async def find_matches(
    offer_id: Optional[str] = Query(None, description="Offer ID to match against"),
    min_odds: Optional[float] = Query(None, description="Minimum odds filter (overrides offer)"),
    max_odds: float = Query(Config.DEFAULT_MAX_ODDS, description="Maximum odds filter"),
    max_spread: float = Query(Config.DEFAULT_MAX_SPREAD_PERCENT, description="Maximum spread percentage"),
    hours_ahead: int = Query(Config.DEFAULT_MAX_HOURS_AHEAD, description="Hours ahead to search"),
    stake: float = Query(10.0, description="Stake amount for calculations"),
    free_bet_value: Optional[float] = Query(None, description="Free bet value (if different from stake)"),
    limit: int = Query(10, description="Maximum number of results"),
    top_leagues_only: bool = Query(True, description="Only search top European leagues"),
):
    """Find the best matches for matched betting."""
    effective_min_odds = min_odds or Config.DEFAULT_MIN_ODDS
    try:
        client = OddsAPIClient()
        if top_leagues_only:
            matches = await client.get_upcoming_matches(
                leagues=Config.SUPPORTED_LEAGUES,
                hours_ahead=hours_ahead,
            )
        else:
            matches = await client.get_all_upcoming_odds(hours_ahead=hours_ahead)

        total_matches = len(matches)
        if top_leagues_only:
            matches = filter_matches_by_league(matches)
        matches = filter_matches_by_odds_range(matches, effective_min_odds, max_odds)

        matches_with_exchange = sum(
            1 for m in matches
            if any(b.bookmaker_key == Config.BETFAIR_EXCHANGE_KEY for b in m.bookmaker_odds)
        )

        pairings = find_best_pairings(
            matches,
            min_odds=effective_min_odds,
            max_odds=max_odds,
            max_spread=max_spread,
        )

        recommendations = create_recommendations(
            pairings,
            stake=stake,
            free_bet_value=free_bet_value,
            target_odds=effective_min_odds,
            limit=limit,
        )

        requests_remaining = None
        if client.requests_remaining:
            try:
                requests_remaining = int(client.requests_remaining)
            except (ValueError, TypeError):
                pass

        return FindMatchesResponse(
            success=True,
            offer_id=offer_id,
            min_odds_filter=effective_min_odds,
            matches_found=total_matches,
            matches_with_exchange=matches_with_exchange,
            recommendations=recommendations,
            api_requests_remaining=requests_remaining,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

