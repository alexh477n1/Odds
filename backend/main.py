"""FastAPI application entry point."""
import json
import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from backend.scraper import scrape_offers as scrape_offers_func, parse_offer_with_llm
from backend.models.offer import OfferRaw, OfferParsed, OfferRanked
from backend.models.match import FindMatchesResponse, MatchRecommendation
from backend.models.calculator import (
    CalcRequest, 
    CalcResponse, 
    BatchCalcRequest, 
    BatchCalcResponse,
    BetType,
)
from backend.models.instruction import (
    InstructionRequest,
    InstructionResponse,
    FullOfferInstructionRequest,
    FullOfferInstructionResponse,
)
from backend.models.user import (
    UserRegister,
    UserLogin,
    UserProfile,
    UserProfileUpdate,
    TokenResponse,
    UserStats,
)
from backend.models.saved_offer import (
    SaveOfferRequest,
    SavedOffer,
    UpdateOfferRequest,
    SavedOffersResponse,
    OfferStatus,
)
from backend.models.bet import (
    LogBetRequest,
    Bet,
    SettleBetRequest,
    UpdateBetRequest,
    BetsResponse,
    BetStats,
    BetOutcome,
)
from backend.utils.ranking import rank_offers
from backend.utils.match_filtering import (
    filter_matches_by_odds_range,
    filter_matches_by_league,
    find_best_pairings,
    create_recommendations,
)
from backend.utils.calculator import calculate, calculate_batch, calculate_retention_rate
from backend.utils.instructions import generate_instructions, generate_full_offer_instructions
from backend.services.odds_api_client import OddsAPIClient
from backend.services import auth as auth_service
from backend.services import offers as offers_service
from backend.services import bets as bets_service
from backend.database import save_offers as save_offers_to_db
from backend.config import Config

app = FastAPI(title="MatchCaddy API", version="3.0.0")

# CORS Middleware - Allow mobile app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your app domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V3 Offer-Centric Routes
from backend.routers.offers_v3 import router as offers_v3_router
app.include_router(offers_v3_router)


# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to extract and validate JWT token from Authorization header.
    Returns user info dict with 'user_id' and 'email'.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.split(" ")[1]
    user = auth_service.get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


def save_to_json(offers: List[OfferRanked], filename: Optional[str] = None) -> str:
    """
    Save ranked offers to JSON file.
    
    Args:
        offers: List of ranked offers
        filename: Optional filename (defaults to timestamp-based name)
        
    Returns:
        Path to saved file
    """
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/offers_{timestamp}.json"
    
    # Prepare data for JSON
    data = {
        "scraped_at": datetime.now().isoformat(),
        "total_offers": len(offers),
        "offers": [offer.model_dump() for offer in offers]
    }
    
    # Write to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return filename


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "MatchCaddy Scraper API", "version": "1.0.0"}


@app.get("/scrape-offers")
def scrape_offers():
    """
    Scrape offers from Oddschecker, parse them, rank them, and save to JSON and Supabase.
    
    Returns:
        JSON response with ranked offers and metadata
    """
    start_time = datetime.now()
    
    try:
        # Validate configuration
        Config.validate()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Step 1: Scrape offers
    print("Starting scrape...")
    raw_offers: List[OfferRaw] = scrape_offers_func()
    
    if not raw_offers:
        raise HTTPException(status_code=500, detail="Failed to scrape any offers")
    
    print(f"Scraped {len(raw_offers)} raw offers")
    
    # Step 2: Parse offers with LLM
    print("Parsing offers with LLM...")
    parsed_offers: List[OfferParsed] = []
    raw_text_list: List[str] = []  # Store raw text in same order as parsed offers
    
    for idx, raw_offer in enumerate(raw_offers, 1):
        print(f"Parsing offer {idx}/{len(raw_offers)}...")
        parsed = parse_offer_with_llm(
            raw_offer.raw_text,
            raw_offer.bookmaker_hint
        )
        
        if parsed:
            parsed_offers.append(parsed)
            raw_text_list.append(raw_offer.raw_text)
        else:
            print(f"Failed to parse offer {idx}")
    
    print(f"Successfully parsed {len(parsed_offers)}/{len(raw_offers)} offers")
    
    # Step 3: Rank offers
    print("Ranking offers...")
    ranked_offers: List[OfferRanked] = rank_offers(parsed_offers, raw_texts=raw_text_list)
    
    # Step 4: Save to JSON
    print("Saving to JSON...")
    json_filename = save_to_json(ranked_offers)
    
    # Step 5: Save to Supabase
    print("Saving to Supabase...")
    db_success = save_offers_to_db(ranked_offers)
    
    # Calculate duration
    duration = (datetime.now() - start_time).total_seconds()
    
    # Prepare response
    response = {
        "success": True,
        "total_offers": len(ranked_offers),
        "scraped_at": start_time.isoformat(),
        "duration_seconds": round(duration, 2),
        "json_file": json_filename,
        "database_saved": db_success,
        "offers": [offer.model_dump() for offer in ranked_offers[:50]]  # Return top 50
    }
    
    return JSONResponse(content=response)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# CALCULATOR ENDPOINTS
# ============================================================================

@app.post("/calculate", response_model=CalcResponse)
def calculate_matched_bet(request: CalcRequest):
    """
    Calculate optimal stakes for a matched bet.
    
    Supports three bet types:
    - **qualifying**: Normal bet to unlock a free bet (minimize loss)
    - **free_bet_snr**: Free bet with Stake Not Returned (most common)
    - **free_bet_sr**: Free bet with Stake Returned (rare, more valuable)
    
    Example request:
    ```json
    {
        "back_odds": 2.10,
        "lay_odds": 2.12,
        "stake": 10.0,
        "bet_type": "qualifying",
        "commission": 0.05
    }
    ```
    
    Returns calculated lay stake, liability, and profit for each outcome.
    """
    try:
        return calculate(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/calculate/batch", response_model=BatchCalcResponse)
def calculate_batch_bets(request: BatchCalcRequest):
    """
    Calculate multiple matched bets at once.
    
    Useful for comparing different scenarios or calculating a complete offer
    (qualifying bet + free bet).
    
    Returns individual results plus total guaranteed profit.
    """
    try:
        return calculate_batch(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/calculate/retention")
def calculate_free_bet_retention(
    free_bet_value: float = Query(..., description="Value of the free bet"),
    back_odds: float = Query(..., description="Back odds at bookmaker"),
    lay_odds: float = Query(..., description="Lay odds at exchange"),
    commission: float = Query(0.05, description="Exchange commission"),
):
    """
    Calculate what percentage of a free bet's value you can extract.
    
    Quick way to evaluate an offer:
    - 70-80%: Good retention
    - 60-70%: Average retention  
    - Below 60%: Poor retention (wide spread)
    
    Example: A £10 free bet with 75% retention = £7.50 guaranteed profit.
    """
    try:
        retention = calculate_retention_rate(free_bet_value, back_odds, lay_odds, commission)
        profit = (retention / 100) * free_bet_value
        
        return {
            "free_bet_value": free_bet_value,
            "back_odds": back_odds,
            "lay_odds": lay_odds,
            "commission": commission,
            "retention_percent": round(retention, 1),
            "guaranteed_profit": round(profit, 2),
            "rating": (
                "Excellent" if retention >= 75 else
                "Good" if retention >= 70 else
                "Fair" if retention >= 60 else
                "Poor"
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/find-matches", response_model=FindMatchesResponse)
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
    """
    Find the best matches for matched betting.
    
    This endpoint:
    1. Fetches upcoming matches from The-Odds-API
    2. Filters by league, time window, and odds range
    3. Finds Back/Lay pairings with Betfair Exchange
    4. Calculates spreads and filters to tight spreads only
    5. Ranks matches by rating and returns top recommendations
    
    Returns:
        FindMatchesResponse with ranked match recommendations
    """
    # Determine minimum odds
    effective_min_odds = min_odds or Config.DEFAULT_MIN_ODDS
    
    # If offer_id provided, look up offer and use its min_odds
    # TODO: Implement offer lookup from database
    # For now, use the provided min_odds or default
    
    try:
        # Initialize API client
        client = OddsAPIClient()
        
        # Fetch matches
        if top_leagues_only:
            matches = await client.get_upcoming_matches(
                leagues=Config.SUPPORTED_LEAGUES,
                hours_ahead=hours_ahead,
            )
        else:
            matches = await client.get_all_upcoming_odds(hours_ahead=hours_ahead)
        
        total_matches = len(matches)
        
        # Filter by league (if not already done)
        if top_leagues_only:
            matches = filter_matches_by_league(matches)
        
        # Filter by odds range
        matches = filter_matches_by_odds_range(matches, effective_min_odds, max_odds)
        
        # Count matches with Betfair Exchange odds
        matches_with_exchange = sum(
            1 for m in matches 
            if any(b.bookmaker_key == Config.BETFAIR_EXCHANGE_KEY for b in m.bookmaker_odds)
        )
        
        # Find best Back/Lay pairings
        pairings = find_best_pairings(
            matches,
            min_odds=effective_min_odds,
            max_odds=max_odds,
            max_spread=max_spread,
        )
        
        # Create recommendations with profit calculations
        recommendations = create_recommendations(
            pairings,
            stake=stake,
            free_bet_value=free_bet_value,
            target_odds=effective_min_odds,
            limit=limit,
        )
        
        # Parse API requests remaining
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
        
    except Exception as e:
        print(f"Error in find_matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INSTRUCTION GENERATOR ENDPOINTS
# ============================================================================

@app.post("/generate-instructions", response_model=InstructionResponse)
def generate_betting_instructions(request: InstructionRequest):
    """
    Generate step-by-step betting instructions.
    
    Takes match details, odds, and bet type, returns clear instructions
    your friends can follow to place the matched bet correctly.
    
    Supports bet_type: "qualifying", "free_bet_snr", "free_bet_sr"
    """
    try:
        return generate_instructions(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate-instructions/full-offer", response_model=FullOfferInstructionResponse)
def generate_full_offer_betting_instructions(request: FullOfferInstructionRequest):
    """
    Generate complete instructions for an entire offer (qualifying + free bet).
    
    This is the main endpoint your friends will use. It generates:
    1. Qualifying bet instructions (how to unlock the free bet)
    2. Free bet instructions (how to extract the value)
    3. Total profit summary
    """
    try:
        return generate_full_offer_instructions(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"])
async def register(data: UserRegister):
    """
    Register a new user account.
    
    Creates a new user with email/password and returns a JWT token.
    """
    try:
        return await auth_service.register_user(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(data: UserLogin):
    """
    Log in with email and password.
    
    Returns a JWT token valid for 7 days.
    """
    try:
        return await auth_service.login_user(data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.post("/auth/logout", tags=["Authentication"])
async def logout(user: dict = Depends(get_current_user)):
    """
    Log out the current user.
    
    Note: Since we use stateless JWTs, this is a client-side operation.
    The token should be discarded by the client.
    """
    return {"message": "Logged out successfully"}


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================

@app.get("/user/profile", response_model=UserProfile, tags=["User"])
async def get_profile(user: dict = Depends(get_current_user)):
    """Get the current user's profile."""
    try:
        return await auth_service.get_user_profile(user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/user/profile", response_model=UserProfile, tags=["User"])
async def update_profile(
    data: UserProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update the current user's profile."""
    try:
        return await auth_service.update_user_profile(
            user["user_id"],
            username=data.username,
            avatar_url=data.avatar_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/user/stats", response_model=UserStats, tags=["User"])
async def get_user_stats(user: dict = Depends(get_current_user)):
    """Get the current user's betting statistics."""
    try:
        return await auth_service.get_user_stats(user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SAVED OFFERS ENDPOINTS
# ============================================================================

@app.get("/offers/saved", response_model=SavedOffersResponse, tags=["Offers"])
async def get_saved_offers(
    status: Optional[OfferStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of results"),
    user: dict = Depends(get_current_user),
):
    """Get all saved offers for the current user."""
    try:
        return await offers_service.get_saved_offers(
            user["user_id"],
            status=status,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/offers/save", response_model=SavedOffer, tags=["Offers"])
async def save_offer(
    data: SaveOfferRequest,
    user: dict = Depends(get_current_user),
):
    """Save a new offer to track."""
    try:
        return await offers_service.save_offer(user["user_id"], data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/offers/{offer_id}", response_model=SavedOffer, tags=["Offers"])
async def get_offer(
    offer_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a specific saved offer."""
    try:
        return await offers_service.get_offer(user["user_id"], offer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/offers/{offer_id}", response_model=SavedOffer, tags=["Offers"])
async def update_offer(
    offer_id: str,
    data: UpdateOfferRequest,
    user: dict = Depends(get_current_user),
):
    """Update a saved offer's status, notes, or actual profit."""
    try:
        return await offers_service.update_offer(user["user_id"], offer_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/offers/{offer_id}", tags=["Offers"])
async def delete_offer(
    offer_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a saved offer."""
    success = await offers_service.delete_offer(user["user_id"], offer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"message": "Offer deleted"}


# ============================================================================
# BET LOGGING ENDPOINTS
# ============================================================================

@app.get("/bets", response_model=BetsResponse, tags=["Bets"])
async def get_bets(
    outcome: Optional[BetOutcome] = Query(None, description="Filter by outcome"),
    limit: int = Query(50, description="Maximum number of results"),
    user: dict = Depends(get_current_user),
):
    """Get all bets for the current user."""
    try:
        return await bets_service.get_bets(
            user["user_id"],
            outcome=outcome,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    print(f"Validation errors: {errors}")
    return JSONResponse(
        status_code=422,
        content={"detail": [{"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]} for e in errors]}
    )

@app.post("/bets", response_model=Bet, tags=["Bets"])
async def log_bet(
    data: LogBetRequest,
    user: dict = Depends(get_current_user),
):
    """Log a new bet."""
    try:
        print(f"Received bet data: {data.model_dump() if hasattr(data, 'model_dump') else data.dict()}")
        return await bets_service.log_bet(user["user_id"], data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error logging bet: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to log bet: {error_detail}")


@app.get("/bets/stats", response_model=BetStats, tags=["Bets"])
async def get_bet_stats(user: dict = Depends(get_current_user)):
    """Get detailed betting statistics."""
    try:
        return await bets_service.get_bet_stats(user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bets/{bet_id}", response_model=Bet, tags=["Bets"])
async def get_bet(
    bet_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a specific bet."""
    try:
        return await bets_service.get_bet(user["user_id"], bet_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/bets/{bet_id}", response_model=Bet, tags=["Bets"])
async def update_bet(
    bet_id: str,
    data: UpdateBetRequest,
    user: dict = Depends(get_current_user),
):
    """Update a bet's notes or event date."""
    try:
        return await bets_service.update_bet(user["user_id"], bet_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/bets/{bet_id}/settle", response_model=Bet, tags=["Bets"])
async def settle_bet(
    bet_id: str,
    data: SettleBetRequest,
    user: dict = Depends(get_current_user),
):
    """Settle a bet with the outcome."""
    try:
        return await bets_service.settle_bet(user["user_id"], bet_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/bets/{bet_id}", tags=["Bets"])
async def delete_bet(
    bet_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a bet."""
    success = await bets_service.delete_bet(user["user_id"], bet_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bet not found")
    return {"message": "Bet deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

