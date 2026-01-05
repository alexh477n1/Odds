"""API routes for V3 offer-centric flow."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from backend.models.offers_catalog import (
    OfferCatalog,
    OfferCatalogCreate,
    OfferCatalogListResponse,
    UserOfferProgress,
    UserOfferProgressUpdate,
    ActiveOffersResponse,
    BookmakerPreferencesUpdate,
    BookmakerPreferencesResponse,
    OnboardingStatus,
    OnboardingUpdate,
    STAGE_ACTIONS,
)
from backend.services import offers_catalog as catalog_service
from backend.services.auth import get_current_user as auth_get_user

router = APIRouter(prefix="/v3", tags=["V3 Offers"])


# Dependency to get current user
async def get_current_user(authorization: str = Header(..., alias="Authorization")) -> dict:
    """Extract and validate user from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth format")
    token = authorization.split(" ")[1]
    user = auth_get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# Optional auth - returns user or None
async def get_optional_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> Optional[dict]:
    """Extract user if auth header present, otherwise None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    return auth_get_user(token)


# ============================================================================
# OFFERS CATALOG
# ============================================================================

@router.get("/offers/catalog", response_model=OfferCatalogListResponse)
async def get_offers_catalog(
    limit: int = Query(200, le=200),
    offer_type: Optional[str] = None,
    bookmaker: Optional[str] = None,
    user: Optional[dict] = Depends(get_optional_user),
):
    """
    Get available offers from the catalog.
    
    If authenticated, filters by user's bookmaker preferences
    and excludes already started offers.
    """
    user_id = user["user_id"] if user else None
    
    try:
        result = await catalog_service.get_offers_catalog(
            user_id=user_id,
            limit=limit,
            offer_type=offer_type,
            bookmaker=bookmaker,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/offers/catalog/{offer_id}", response_model=OfferCatalog)
async def get_offer_details(offer_id: str):
    """Get detailed information about a specific offer."""
    try:
        return await catalog_service.get_offer_by_id(offer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/offers/catalog", response_model=OfferCatalog)
async def create_offer(data: OfferCatalogCreate):
    """Admin: Create a new offer in the catalog."""
    try:
        return await catalog_service.create_offer(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/offers/catalog/seed")
async def seed_offers(force: bool = False):
    """Admin: Seed sample offers for testing. Use force=true to clear and reseed."""
    try:
        if force:
            await catalog_service.clear_and_reseed_offers()
        else:
            await catalog_service.seed_sample_offers()
        return {"message": "Sample offers seeded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/offers/catalog/scrape")
async def scrape_and_update_offers():
    """Admin: Scrape Oddschecker and create/update all offers with signup URLs."""
    try:
        result = await catalog_service.update_offers_from_scraper()
        return {
            "message": "Scraping completed",
            "scraped_count": result["scraped_count"],
            "created_count": result.get("created_count", 0),
            "updated_count": result.get("updated_count", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USER OFFER PROGRESS
# ============================================================================

@router.get("/user/offers", response_model=ActiveOffersResponse)
async def get_user_offers(user: dict = Depends(get_current_user)):
    """Get user's active and completed offers."""
    try:
        return await catalog_service.get_active_offers(user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/offers/{offer_id}", response_model=UserOfferProgress)
async def get_user_offer_progress(
    offer_id: str,
    user: dict = Depends(get_current_user),
):
    """Get user's progress on a specific offer."""
    try:
        return await catalog_service.get_offer_progress(user["user_id"], offer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/user/offers/{offer_id}/start", response_model=UserOfferProgress)
async def start_offer(
    offer_id: str,
    user: dict = Depends(get_current_user),
):
    """Start working on an offer."""
    try:
        return await catalog_service.start_offer(user["user_id"], offer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/user/offers/{offer_id}", response_model=UserOfferProgress)
async def update_offer_progress(
    offer_id: str,
    update: UserOfferProgressUpdate,
    user: dict = Depends(get_current_user),
):
    """Update progress on an offer (change stage, add notes, etc)."""
    try:
        return await catalog_service.update_offer_progress(
            user["user_id"], offer_id, update
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/offers/stages/actions")
async def get_stage_actions():
    """Get the action text for each offer stage."""
    return STAGE_ACTIONS


# ============================================================================
# BOOKMAKER PREFERENCES
# ============================================================================

@router.get("/user/preferences/bookmakers", response_model=BookmakerPreferencesResponse)
async def get_bookmaker_preferences(user: dict = Depends(get_current_user)):
    """Get user's bookmaker whitelist/blacklist."""
    try:
        return await catalog_service.get_bookmaker_preferences(user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/preferences/bookmakers", response_model=BookmakerPreferencesResponse)
async def set_bookmaker_preferences(
    data: BookmakerPreferencesUpdate,
    user: dict = Depends(get_current_user),
):
    """Set user's bookmaker preferences."""
    try:
        return await catalog_service.set_bookmaker_preferences(
            user["user_id"], data.preferences
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ONBOARDING
# ============================================================================

@router.get("/user/onboarding", response_model=OnboardingStatus)
async def get_onboarding_status(user: dict = Depends(get_current_user)):
    """Get user's onboarding status."""
    try:
        return await catalog_service.get_onboarding_status(user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/user/onboarding", response_model=OnboardingStatus)
async def update_onboarding(
    update: OnboardingUpdate,
    user: dict = Depends(get_current_user),
):
    """Update user's onboarding progress."""
    try:
        return await catalog_service.update_onboarding(
            user["user_id"], update.step, update.completed or False
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# AVAILABLE BOOKMAKERS
# ============================================================================

BOOKMAKERS = [
    "Bet365",
    "William Hill",
    "Paddy Power",
    "Betfair Sportsbook",
    "Coral",
    "Ladbrokes",
    "Sky Bet",
    "888sport",
    "Betway",
    "Unibet",
    "BetVictor",
    "Betfred",
    "BoyleSports",
    "SpreadEx",
    "Mansion Bet",
    "10Bet",
    "LiveScore Bet",
    "Virgin Bet",
    "Novibet",
    "Kwiff",
]


@router.get("/bookmakers")
async def get_available_bookmakers():
    """Get list of all available bookmakers."""
    return {"bookmakers": BOOKMAKERS}


# ============================================================================
# OFFER INSTRUCTIONS
# ============================================================================

@router.get("/offers/catalog/{offer_id}/instructions")
async def get_offer_instructions(offer_id: str):
    """Generate detailed LLM instructions for completing a specific offer."""
    try:
        offer = await catalog_service.get_offer_by_id(offer_id)
        
        from backend.utils.offer_instructions import generate_offer_instructions
        instructions = generate_offer_instructions(offer)
        
        return {
            "offer_id": offer_id,
            "offer_name": offer.offer_name,
            "bookmaker": offer.bookmaker,
            "instructions": instructions,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate instructions: {error_detail}")


@router.post("/offers/{offer_id}/suggest-bet")
async def suggest_bet(
    offer_id: str,
    match_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Get bet suggestions for an offer using LLM + odds API.
    Returns suggested back/lay odds, expected profit, and bet characteristics.
    """
    from backend.utils.instructions import get_bet_characteristics
    from backend.services.odds_api_client import OddsAPIClient
    from backend.utils.match_filtering import find_best_pairings
    
    try:
        # Get offer details
        offer = await catalog_service.get_offer_by_id(offer_id)
        
        # If match_id provided, get match details
        match_info = None
        if match_id:
            client = OddsAPIClient()
            # This would need to fetch specific match - simplified for now
            # In production, you'd fetch the match by ID from your matches
            pass
        
        # Get bet characteristics
        characteristics = get_bet_characteristics(offer, match_info)
        
        # Return suggestions
        return {
            "offer_id": offer_id,
            "suggested_back_odds": offer.min_odds or 2.0,
            "suggested_lay_odds": (offer.min_odds or 2.0) + 0.02,
            "expected_profit": offer.expected_profit,
            "characteristics": characteristics,
            "tips": [
                f"Use odds of at least {offer.min_odds or 2.0} to meet offer requirements",
                "Look for spreads under 2% for best value",
                "Ensure Betfair Exchange has sufficient liquidity",
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
