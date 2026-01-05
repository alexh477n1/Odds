"""Service for managing the offers catalog and user offer progress."""
from datetime import datetime
from typing import List, Optional
from backend.database.supabase_client import get_supabase_client
from backend.models.offers_catalog import (
    OfferCatalog,
    OfferCatalogCreate,
    OfferCatalogListResponse,
    UserOfferProgress,
    UserOfferProgressUpdate,
    ActiveOffersResponse,
    OfferStage,
    BookmakerPreference,
    BookmakerPreferenceItem,
    BookmakerPreferencesResponse,
    OnboardingStatus,
    OnboardingStep,
    STAGE_TRANSITIONS,
    OfferDifficulty,
    OfferType,
)
from backend.utils.offers_calculator import (
    calculate_expected_profit,
    calculate_expected_profit_with_llm,
    calculate_terms_hash,
)


# ============================================================================
# OFFERS CATALOG
# ============================================================================

async def get_offers_catalog(
    user_id: Optional[str] = None,
    limit: int = 200,
    offer_type: Optional[str] = None,
    bookmaker: Optional[str] = None,
    active_only: bool = True,
) -> OfferCatalogListResponse:
    """Get available offers, filtered by user preferences if provided."""
    supabase = get_supabase_client()
    
    query = supabase.table("offers_catalog").select("*")
    
    if active_only:
        query = query.eq("is_active", True)
    
    # CRITICAL: Filter out offers without free bets at database level
    query = query.not_.is_("offer_value", "null")
    query = query.gt("offer_value", 0)
    
    if offer_type:
        query = query.eq("offer_type", offer_type)
    
    if bookmaker:
        query = query.eq("bookmaker", bookmaker)
    
    # Don't order here - we'll sort in Python after applying prioritization logic
    # Get enough offers to sort from (we'll limit after sorting)
    query = query.limit(500)  # Get enough to ensure we have top 10 mainstream
    
    result = query.execute()
    offers_data = result.data or []
    
    # Apply user preferences if user_id provided
    if user_id:
        prefs = await get_bookmaker_preferences(user_id)
        
        # If whitelist exists, only show those
        if prefs.whitelist:
            offers_data = [o for o in offers_data if o["bookmaker"] in prefs.whitelist]
        
        # Remove blacklisted bookmakers
        if prefs.blacklist:
            offers_data = [o for o in offers_data if o["bookmaker"] not in prefs.blacklist]
        
        # Remove offers user has already started
        started = supabase.table("user_offer_progress")\
            .select("offer_id")\
            .eq("user_id", user_id)\
            .execute()
        started_ids = {p["offer_id"] for p in (started.data or [])}
        offers_data = [o for o in offers_data if o["id"] not in started_ids]
    
    # Parse offers with error handling
    offers = []
    for o in offers_data:
        try:
            parsed = _parse_offer_catalog(o)
            
            # FILTER OUT offers without free bets (no offer_value)
            if not parsed.offer_value or parsed.offer_value <= 0:
                print(f"Skipping {parsed.bookmaker} - no free bet value (offer_value={parsed.offer_value})")
                continue
            
            # Use stored expected_profit from database ONLY
            # NO calculations during GET requests - all profits pre-calculated and stored
            # If profit is None, leave it as None (don't calculate fallback)
            
            offers.append(parsed)
        except Exception as e:
            print(f"Error parsing offer {o.get('id', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            # Skip invalid offers instead of crashing
            continue
    
    # Sort offers: mainstream > easy > high profit
    MAINSTREAM_BOOKMAKERS_LOWER = [
        "bet365", "betfair", "sky bet", "paddy power", "william hill",
        "betway", "coral", "ladbrokes", "betvictor", "unibet"
    ]
    
    DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}
    
    def get_difficulty_rank(offer: OfferCatalog) -> int:
        """Get difficulty rank for sorting."""
        if offer.difficulty is None:
            return 1
        difficulty_str = offer.difficulty.value if hasattr(offer.difficulty, 'value') else str(offer.difficulty)
        return DIFFICULTY_RANK.get(difficulty_str.lower(), 1)
    
    def is_top_10_mainstream(offer: OfferCatalog) -> bool:
        """Check if bookmaker is in top 10 mainstream (case-insensitive, robust matching)."""
        if not offer.bookmaker:
            return False
            
        bookmaker_lower = offer.bookmaker.lower().strip()
        # Normalize bookmaker name (remove common suffixes and clean up)
        bookmaker_normalized = bookmaker_lower.replace(" sportsbook", "").replace(" exchange", "").replace(" uk", "").replace("  ", " ").strip()
        
        # Fix common misparsings BEFORE checking
        bookmaker_normalized = bookmaker_normalized.replace("betwright", "betway").replace("bet wright", "betway")
        
        # Check exact match first
        if bookmaker_normalized in MAINSTREAM_BOOKMAKERS_LOWER:
            return True
        
        # Check if any mainstream name matches (contains or is contained)
        for mainstream in MAINSTREAM_BOOKMAKERS_LOWER:
            # Mainstream name is in bookmaker name (e.g., "bet365" in "bet365 sportsbook")
            if mainstream in bookmaker_normalized:
                return True
            # Bookmaker name matches mainstream exactly
            if bookmaker_normalized == mainstream:
                return True
        
        return False
    
    # Sort: Top 10 mainstream first (0), then others (1), then by profit descending
    # CRITICAL: Sort by mainstream status FIRST to ensure top 10 appear at top
    def get_sort_key(offer: OfferCatalog):
        is_mainstream = is_top_10_mainstream(offer)
        return (
            0 if is_mainstream else 1,  # Top 10 mainstream first (0 = first, 1 = second)
            -(offer.expected_profit or 0),  # Higher profit = better (negative for descending)
            get_difficulty_rank(offer),  # Easier first (tiebreaker)
            offer.priority_rank or 999,  # Lower rank = higher priority (final tiebreaker)
        )
    
    offers.sort(key=get_sort_key)
    
    # Debug: Print first 10 to verify sorting
    if offers:
        print(f"DEBUG SORTING: First 10 bookmakers after sort:")
        for i, o in enumerate(offers[:10]):
            is_mainstream = is_top_10_mainstream(o)
            print(f"  {i+1}. {o.bookmaker} (mainstream={is_mainstream}, profit={o.expected_profit})")
    
    # Limit to requested limit AFTER sorting
    offers = offers[:limit]
    
    return OfferCatalogListResponse(
        offers=offers,
        total=len(offers),
    )


async def get_offer_by_id(offer_id: str) -> OfferCatalog:
    """Get a specific offer by ID."""
    supabase = get_supabase_client()
    
    result = supabase.table("offers_catalog").select("*").eq("id", offer_id).execute()
    
    if not result.data:
        raise ValueError("Offer not found")
    
    return _parse_offer_catalog(result.data[0])


async def create_offer(data: OfferCatalogCreate) -> OfferCatalog:
    """Create a new offer in the catalog."""
    supabase = get_supabase_client()
    
    offer_data = data.model_dump(exclude_none=True)
    
    result = supabase.table("offers_catalog").insert(offer_data).execute()
    
    if not result.data:
        raise ValueError("Failed to create offer")
    
    return _parse_offer_catalog(result.data[0])


async def clear_and_reseed_offers():
    """Clear all offers and reseed with fresh data."""
    supabase = get_supabase_client()
    # Delete all existing offers (gt created_at means all rows)
    supabase.table("offers_catalog").delete().gt("created_at", "1970-01-01").execute()
    # Seed fresh - force insert by not checking existing
    await _insert_sample_offers(supabase)


async def seed_sample_offers():
    """Seed the catalog with sample offers if none exist."""
    supabase = get_supabase_client()
    
    # Check if offers already exist
    existing = supabase.table("offers_catalog").select("id").limit(1).execute()
    if existing.data:
        return  # Already seeded
    
    await _insert_sample_offers(supabase)


async def update_offers_from_scraper():
    """Scrape Oddschecker and create/update offers catalog with all scraped offers."""
    from backend.scraper.oddschecker_scraper import scrape_oddschecker_offers
    
    supabase = get_supabase_client()
    
    # Scrape offers
    scraped_offers = await scrape_oddschecker_offers()
    
    # Get all existing offers for matching (include offer_name for better matching)
    all_offers = supabase.table("offers_catalog")\
        .select("id, bookmaker, offer_name")\
        .execute()
    
    # Create mapping: bookmaker -> list of (id, offer_name)
    existing_bookmakers = {}
    existing_offers_by_bookmaker = {}
    for o in (all_offers.data or []):
        bookmaker_lower = o["bookmaker"].lower()
        bookmaker_normalized = bookmaker_lower.replace(" sportsbook", "").replace(" exchange", "").strip()
        
        # Store by both exact and normalized name
        if bookmaker_lower not in existing_offers_by_bookmaker:
            existing_offers_by_bookmaker[bookmaker_lower] = []
        existing_offers_by_bookmaker[bookmaker_lower].append((o["id"], o.get("offer_name", "").lower()))
        
        # Also store by normalized name
        if bookmaker_normalized not in existing_offers_by_bookmaker:
            existing_offers_by_bookmaker[bookmaker_normalized] = []
        existing_offers_by_bookmaker[bookmaker_normalized].append((o["id"], o.get("offer_name", "").lower()))
        
        # Also keep simple mapping for exact matches
        existing_bookmakers[bookmaker_lower] = o["id"]
    
    updated_count = 0
    created_count = 0
    
    for scraped in scraped_offers:
        bookmaker = scraped.get("bookmaker")
        signup_url = scraped.get("signup_url")
        
        # Skip if no bookmaker or URL
        if not bookmaker or not signup_url:
            continue
        
        # Skip "UK Licenced" and other non-bookmaker entries
        if bookmaker.lower() in ["uk licenced", "close icon"]:
            continue
        
        bookmaker_lower = bookmaker.lower().strip()
        scraped_offer_name = scraped.get("offer_name", "").lower()
        
        # Normalize bookmaker names (remove "sportsbook", "exchange" suffixes)
        bookmaker_normalized = bookmaker_lower.replace(" sportsbook", "").replace(" exchange", "").strip()
        
        # Try to find existing offer - exact match first
        offer_id = existing_bookmakers.get(bookmaker_lower)
        
        # If multiple offers exist for this bookmaker, try to match by offer name similarity
        if not offer_id and bookmaker_normalized in existing_offers_by_bookmaker:
            # Look for offers with similar names (prioritize welcome offers)
            candidates = existing_offers_by_bookmaker[bookmaker_normalized]
            for oid, existing_name in candidates:
                # Check if offer names are similar (both mention bet/get amounts)
                if "bet" in scraped_offer_name and "bet" in existing_name:
                    if "get" in scraped_offer_name and "get" in existing_name:
                        # Both are "bet X get Y" offers - likely the same
                        offer_id = oid
                        break
                # Or if exact bookmaker match and it's a welcome offer
                if bookmaker_lower == bookmaker_normalized and "welcome" in existing_name:
                    offer_id = oid
                    break
        
        # Try normalized match (e.g., "betfair" matches "betfair sportsbook")
        if not offer_id:
            for existing_name, oid in existing_bookmakers.items():
                existing_normalized = existing_name.replace(" sportsbook", "").replace(" exchange", "").strip()
                if bookmaker_normalized == existing_normalized:
                    offer_id = oid
                    break
        
        # Try partial match if still no match
        if not offer_id:
            for existing_name, oid in existing_bookmakers.items():
                existing_normalized = existing_name.replace(" sportsbook", "").replace(" exchange", "").strip()
                if bookmaker_normalized in existing_normalized or existing_normalized in bookmaker_normalized:
                    if len(bookmaker_normalized) >= 4 and len(existing_normalized) >= 4:
                        offer_id = oid
                        break
        
        if offer_id:
            # Get existing offer to check if terms changed
            existing_offer_data = supabase.table("offers_catalog")\
                .select("terms_summary, expected_profit")\
                .eq("id", offer_id)\
                .execute()
            
            existing_terms = existing_offer_data.data[0].get("terms_summary") if existing_offer_data.data else None
            new_terms = scraped.get("terms_summary")
            terms_changed = existing_terms != new_terms
            
            # Update existing offer with ALL scraped data
            update_data = {
                "signup_url": signup_url,
                "updated_at": "now()",  # Force update timestamp
            }
            
            # Update all available fields from scraper
            if scraped.get("offer_name"):
                update_data["offer_name"] = scraped.get("offer_name")
            if scraped.get("offer_value") is not None:
                update_data["offer_value"] = scraped.get("offer_value")
            if scraped.get("required_stake") is not None:
                update_data["required_stake"] = scraped.get("required_stake")
            if scraped.get("min_odds") is not None:
                update_data["min_odds"] = scraped.get("min_odds")
            if scraped.get("terms_summary"):
                update_data["terms_summary"] = scraped.get("terms_summary")
            if scraped.get("terms_raw"):
                update_data["terms_raw"] = scraped.get("terms_raw")
            
            # ALWAYS recalculate profit with LLM when updating from scraper
            # This ensures we have accurate profit based on latest scraped data
            # Get full offer data for calculation
            full_offer_data = supabase.table("offers_catalog")\
                .select("*")\
                .eq("id", offer_id)\
                .execute()
            
            if full_offer_data.data:
                # Merge update_data into full_offer_data for calculation
                temp_offer_data = {**full_offer_data.data[0], **update_data}
                # Remove 'now()' string and use actual datetime for parsing
                if temp_offer_data.get("updated_at") == "now()":
                    from datetime import datetime
                    temp_offer_data["updated_at"] = datetime.utcnow().isoformat()
                # Also include terms_raw if available from scraper
                if scraped.get("terms_raw"):
                    temp_offer_data["terms_raw"] = scraped.get("terms_raw")
                temp_offer = _parse_offer_catalog(temp_offer_data)
                
                # ALWAYS use LLM to calculate profit from scraped data
                from backend.utils.offers_calculator import calculate_expected_profit, calculate_terms_hash
                current_terms_hash = calculate_terms_hash(temp_offer.terms_summary)
                existing_terms_hash = full_offer_data.data[0].get("terms_hash")
                
                print(f"Calculating profit with LLM for {bookmaker} (offer_value={temp_offer.offer_value}, required_stake={temp_offer.required_stake})")
                new_profit = calculate_expected_profit(
                    temp_offer,
                    use_llm=True,
                    terms_hash=current_terms_hash,
                    existing_hash=existing_terms_hash
                )
                
                if new_profit is not None:
                    update_data["expected_profit"] = new_profit
                    # Include terms_hash if column exists
                    update_data["terms_hash"] = current_terms_hash
                    print(f"✓ Stored LLM profit for {bookmaker}: £{new_profit}")
                else:
                    # Fallback to formula if LLM fails
                    from backend.utils.offers_calculator import calculate_expected_profit_formula
                    fallback_profit = calculate_expected_profit_formula(
                        temp_offer.offer_value,
                        temp_offer.required_stake,
                        temp_offer.min_odds,
                        temp_offer.is_stake_returned,
                        commission=0.02
                    )
                    if fallback_profit is not None:
                        update_data["expected_profit"] = fallback_profit
                        update_data["terms_hash"] = current_terms_hash
                        print(f"⚠ LLM failed, used formula for {bookmaker}: £{fallback_profit}")
                    else:
                        print(f"✗ Failed to calculate profit for {bookmaker}")
            
            try:
                supabase.table("offers_catalog")\
                    .update(update_data)\
                    .eq("id", offer_id)\
                    .execute()
                updated_count += 1
            except Exception as e:
                # If terms_hash column doesn't exist, try without it
                if "terms_hash" in str(e):
                    update_data_without_hash = {k: v for k, v in update_data.items() if k != "terms_hash"}
                    try:
                        supabase.table("offers_catalog")\
                            .update(update_data_without_hash)\
                            .eq("id", offer_id)\
                            .execute()
                        updated_count += 1
                        print(f"✓ Updated {bookmaker} (without terms_hash column)")
                    except Exception as e2:
                        print(f"Error updating offer {bookmaker}: {e2}")
                else:
                    print(f"Error updating offer {bookmaker}: {e}")
                continue
            
            try:
                supabase.table("offers_catalog")\
                    .update(update_data)\
                    .eq("id", offer_id)\
                    .execute()
                updated_count += 1
            except Exception as e:
                print(f"Error updating offer {bookmaker}: {e}")
                continue
        else:
            # Create new offer from scraped data
            try:
                new_offer = {
                    "bookmaker": bookmaker,
                    "offer_name": scraped.get("offer_name") or f"{bookmaker} Welcome Offer",
                    "offer_type": "welcome",
                    "signup_url": signup_url,
                    "oddschecker_url": "https://www.oddschecker.com/free-bets",
                    "offer_value": scraped.get("offer_value"),
                    "required_stake": scraped.get("required_stake"),
                    "min_odds": scraped.get("min_odds"),
                    "terms_summary": scraped.get("terms_summary"),
                    "terms_raw": scraped.get("terms_raw"),
                    "difficulty": "easy",
                    "is_active": True,
                    "priority_rank": 999,  # Lower priority for auto-created offers
                    "is_stake_returned": False,
                    "qualifying_bet_required": True,
                }
                
                # Skip if no offer_value (no free bets)
                if not new_offer.get("offer_value") or new_offer.get("offer_value") <= 0:
                    print(f"Skipping {bookmaker} - no free bet value")
                    continue
                
                # Calculate expected profit for new offer (always use LLM directly)
                temp_offer = OfferCatalog(
                    id="temp",
                    bookmaker=new_offer["bookmaker"],
                    offer_name=new_offer["offer_name"],
                    offer_type=OfferType.WELCOME,
                    offer_value=new_offer.get("offer_value"),
                    required_stake=new_offer.get("required_stake"),
                    min_odds=new_offer.get("min_odds"),
                    terms_summary=new_offer.get("terms_summary"),
                    terms_raw=scraped.get("terms_raw"),  # Include raw terms
                    is_stake_returned=new_offer["is_stake_returned"],
                    difficulty=OfferDifficulty.EASY,
                    expected_profit=None,
                    is_active=True,
                    priority_rank=999,
                    created_at=datetime.utcnow().isoformat(),
                    updated_at=datetime.utcnow().isoformat(),
                )
                
                # ALWAYS use LLM directly for accurate profit calculation
                from backend.utils.offers_calculator import calculate_expected_profit, calculate_terms_hash
                current_terms_hash = calculate_terms_hash(temp_offer.terms_summary)
                
                print(f"Calculating NEW offer profit with LLM for {bookmaker}")
                new_profit = calculate_expected_profit(
                    temp_offer,
                    use_llm=True,
                    terms_hash=current_terms_hash,
                    existing_hash=None
                )
                if new_profit is not None:
                    new_offer["expected_profit"] = new_profit
                    new_offer["terms_hash"] = current_terms_hash
                    print(f"✓ Stored LLM profit for NEW {bookmaker}: £{new_profit}")
                else:
                    # Fallback to formula
                    from backend.utils.offers_calculator import calculate_expected_profit_formula
                    fallback_profit = calculate_expected_profit_formula(
                        temp_offer.offer_value,
                        temp_offer.required_stake,
                        temp_offer.min_odds,
                        temp_offer.is_stake_returned,
                        commission=0.02
                    )
                    if fallback_profit is not None:
                        new_offer["expected_profit"] = fallback_profit
                        new_offer["terms_hash"] = current_terms_hash
                        print(f"⚠ LLM failed, used formula for NEW {bookmaker}: £{fallback_profit}")
                
                result = supabase.table("offers_catalog")\
                    .insert(new_offer)\
                    .execute()
                
                if result.data:
                    created_count += 1
            except Exception as e:
                # Skip if insert fails (e.g., duplicate, constraint violation)
                print(f"Error creating offer {bookmaker}: {e}")
                continue
    
    return {
        "scraped_count": len(scraped_offers),
        "created_count": created_count,
        "updated_count": updated_count,
    }


async def _insert_sample_offers(supabase):
    """Insert sample offers into database with real Oddschecker links."""
    sample_offers = [
        # TOP TIER - Best value, easiest
        {
            "bookmaker": "Bet365",
            "offer_name": "Bet £10 Get £30 in Free Bets",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 10.0,
            "min_odds": 1.20,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Place £10+ at odds 1.20+. Get 3x £10 free bets within 30 days.",
            "difficulty": "easy",
            "expected_profit": 22.0,
            "estimated_time_minutes": 30,
            "priority_rank": 1,
            "is_active": True,
            "signup_url": None,  # User finds on Oddschecker
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Sky Bet",
            "offer_name": "Bet £10 Get £40 in Free Bets",
            "offer_type": "welcome",
            "offer_value": 40.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10+ at 1.50+. Get £40 in free bets.",
            "difficulty": "easy",
            "expected_profit": 29.0,
            "estimated_time_minutes": 30,
            "priority_rank": 2,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "William Hill",
            "offer_name": "Bet £10 Get £30 Free Bets",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Place £10+ at odds 1.50+. Get £30 in free bets.",
            "difficulty": "easy",
            "expected_profit": 21.0,
            "estimated_time_minutes": 30,
            "priority_rank": 3,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Coral",
            "offer_name": "Bet £5 Get £20 in Free Bets",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 5.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £5+ at 1.50+. Get 4x £5 free bets.",
            "difficulty": "easy",
            "expected_profit": 14.5,
            "estimated_time_minutes": 20,
            "priority_rank": 4,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Ladbrokes",
            "offer_name": "Bet £5 Get £20 in Free Bets",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 5.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £5+ at 1.50+. Get 4x £5 free bets.",
            "difficulty": "easy",
            "expected_profit": 14.5,
            "estimated_time_minutes": 20,
            "priority_rank": 5,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Paddy Power",
            "offer_name": "Bet £20 Get £20 in Free Bets",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 20.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Place £20+ at odds 1.50+. Free bet awarded after settlement.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 6,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "888sport",
            "offer_name": "Bet £10 Get £30 + £10 Casino",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10+ at 1.50+. Get 3x £10 free bets.",
            "difficulty": "easy",
            "expected_profit": 21.0,
            "estimated_time_minutes": 30,
            "priority_rank": 7,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Betfair Sportsbook",
            "offer_name": "Get up to £100 in Free Bets",
            "offer_type": "welcome",
            "offer_value": 100.0,
            "required_stake": 50.0,
            "min_odds": 2.00,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £50 at 2.0+, get 5x £20 free bets. Expires 30 days.",
            "difficulty": "medium",
            "expected_profit": 68.0,
            "estimated_time_minutes": 60,
            "priority_rank": 8,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Betway",
            "offer_name": "Bet £10 Get £10 Free Bet",
            "offer_type": "welcome",
            "offer_value": 10.0,
            "required_stake": 10.0,
            "min_odds": 1.75,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10, get £10 matched free bet. Min odds 1.75.",
            "difficulty": "easy",
            "expected_profit": 7.0,
            "estimated_time_minutes": 25,
            "priority_rank": 9,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "BetVictor",
            "offer_name": "Bet £5 Get £30 in Bonuses",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 5.0,
            "min_odds": 2.00,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £5 at 2.0+. Get £20 sports + £10 casino bonus.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 10,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Betfred",
            "offer_name": "Bet £10 Get £40 in Bonuses",
            "offer_type": "welcome",
            "offer_value": 40.0,
            "required_stake": 10.0,
            "min_odds": 2.00,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 2.0+. Get £30 free bets + £10 casino.",
            "difficulty": "easy",
            "expected_profit": 21.0,
            "estimated_time_minutes": 30,
            "priority_rank": 11,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "BoyleSports",
            "offer_name": "Bet £10 Get £20 Free Bets",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get 2x £10 free bets.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 12,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Virgin Bet",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 13,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "LiveScore Bet",
            "offer_name": "Bet £10 Get £20 Free Bets",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get 2x £10 free bets.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 14,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "SpreadEx",
            "offer_name": "Bet £10 Get £30 Free Bet",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £30 free bet if it loses.",
            "difficulty": "medium",
            "expected_profit": 12.0,
            "estimated_time_minutes": 30,
            "priority_rank": 15,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Unibet",
            "offer_name": "£40 Money Back as Bonus",
            "offer_type": "welcome",
            "offer_value": 40.0,
            "required_stake": 40.0,
            "min_odds": 1.40,
            "wagering_requirement": 3.0,
            "is_stake_returned": False,
            "terms_summary": "If first bet loses, get £40 bonus. 3x wagering on bonus.",
            "difficulty": "hard",
            "expected_profit": 12.0,
            "estimated_time_minutes": 60,
            "priority_rank": 16,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Novibet",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 17,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Kwiff",
            "offer_name": "Get a £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 20,
            "priority_rank": 18,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "10Bet",
            "offer_name": "100% up to £50 Free Bet",
            "offer_type": "welcome",
            "offer_value": 50.0,
            "required_stake": 50.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet up to £50, get 100% matched free bet.",
            "difficulty": "medium",
            "expected_profit": 35.0,
            "estimated_time_minutes": 40,
            "priority_rank": 19,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Mansion Bet",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.80,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.80+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 20,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        # Additional Welcome Offers (21-30)
        {
            "bookmaker": "BetUK",
            "offer_name": "Bet £10 Get £30 Free Bet",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £30 free bet.",
            "difficulty": "easy",
            "expected_profit": 21.0,
            "estimated_time_minutes": 30,
            "priority_rank": 21,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "BetMGM",
            "offer_name": "Bet £10 Get £40 in Free Bets",
            "offer_type": "welcome",
            "offer_value": 40.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get 4x £10 free bets.",
            "difficulty": "easy",
            "expected_profit": 29.0,
            "estimated_time_minutes": 30,
            "priority_rank": 22,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Parimatch",
            "offer_name": "Bet £10 Get £30 Free Bet",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £30 free bet.",
            "difficulty": "easy",
            "expected_profit": 21.0,
            "estimated_time_minutes": 30,
            "priority_rank": 23,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "BetRegal",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 24,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "LeoVegas",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 25,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Mr Play",
            "offer_name": "Bet £10 Get £30 Free Bet",
            "offer_type": "welcome",
            "offer_value": 30.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £30 free bet.",
            "difficulty": "easy",
            "expected_profit": 21.0,
            "estimated_time_minutes": 30,
            "priority_rank": 26,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "BetGoodwin",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 27,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Grosvenor",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 28,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "BetBull",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 29,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "QuinnBet",
            "offer_name": "Bet £10 Get £20 Free Bet",
            "offer_type": "welcome",
            "offer_value": 20.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Bet £10 at 1.50+. Get £20 free bet.",
            "difficulty": "easy",
            "expected_profit": 14.0,
            "estimated_time_minutes": 25,
            "priority_rank": 30,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        # Reload Offers (31-40)
        {
            "bookmaker": "Bet365",
            "offer_name": "Acca Insurance - Up to £50",
            "offer_type": "reload",
            "offer_value": 50.0,
            "required_stake": None,
            "min_odds": 2.00,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "If one leg of 5+ fold acca loses, get stake back as free bet.",
            "difficulty": "easy",
            "expected_profit": 35.0,
            "estimated_time_minutes": 20,
            "priority_rank": 31,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Sky Bet",
            "offer_name": "Super 6 - Free to Play",
            "offer_type": "reload",
            "offer_value": 250000.0,
            "required_stake": 0.0,
            "min_odds": None,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Predict 6 scores correctly to win £250k. Free weekly entry.",
            "difficulty": "hard",
            "expected_profit": 0.0,
            "estimated_time_minutes": 5,
            "priority_rank": 32,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Paddy Power",
            "offer_name": "Money Back Specials",
            "offer_type": "reload",
            "offer_value": 10.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Selected matches - money back if your bet loses.",
            "difficulty": "easy",
            "expected_profit": 7.0,
            "estimated_time_minutes": 15,
            "priority_rank": 33,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "William Hill",
            "offer_name": "Bet £10 Get £5 Free Bet",
            "offer_type": "reload",
            "offer_value": 5.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Weekly reload offer. Bet £10+ get £5 free bet.",
            "difficulty": "easy",
            "expected_profit": 3.5,
            "estimated_time_minutes": 15,
            "priority_rank": 34,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Coral",
            "offer_name": "Price Boost - Enhanced Odds",
            "offer_type": "reload",
            "offer_value": 5.0,
            "required_stake": 5.0,
            "min_odds": 2.00,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Daily enhanced odds on selected matches.",
            "difficulty": "easy",
            "expected_profit": 2.5,
            "estimated_time_minutes": 10,
            "priority_rank": 35,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Ladbrokes",
            "offer_name": "5-A-Side Free Bet",
            "offer_type": "reload",
            "offer_value": 5.0,
            "required_stake": 0.0,
            "min_odds": None,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Free £5 bet when you pick 5 players. Weekly offer.",
            "difficulty": "easy",
            "expected_profit": 3.5,
            "estimated_time_minutes": 10,
            "priority_rank": 36,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Betfair Sportsbook",
            "offer_name": "Odds Boost - Selected Events",
            "offer_type": "reload",
            "offer_value": 10.0,
            "required_stake": 10.0,
            "min_odds": 2.00,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Enhanced odds on featured matches.",
            "difficulty": "easy",
            "expected_profit": 5.0,
            "estimated_time_minutes": 15,
            "priority_rank": 37,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "888sport",
            "offer_name": "Bet £10 Get £5 Free Bet",
            "offer_type": "reload",
            "offer_value": 5.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Weekly reload offer for existing customers.",
            "difficulty": "easy",
            "expected_profit": 3.5,
            "estimated_time_minutes": 15,
            "priority_rank": 38,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Betway",
            "offer_name": "Accumulator Bonus",
            "offer_type": "reload",
            "offer_value": 10.0,
            "required_stake": 10.0,
            "min_odds": 2.00,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Up to 10% bonus on acca winnings. 4+ selections.",
            "difficulty": "easy",
            "expected_profit": 5.0,
            "estimated_time_minutes": 20,
            "priority_rank": 39,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "BetVictor",
            "offer_name": "Bet £10 Get £5 Free Bet",
            "offer_type": "reload",
            "offer_value": 5.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Weekly reload offer.",
            "difficulty": "easy",
            "expected_profit": 3.5,
            "estimated_time_minutes": 15,
            "priority_rank": 40,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        # Horse Racing Offers (41-45)
        {
            "bookmaker": "Bet365",
            "offer_name": "Best Odds Guaranteed",
            "offer_type": "other",
            "offer_value": None,
            "required_stake": None,
            "min_odds": None,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Get best odds on all UK & Irish horse racing. SP or price taken.",
            "difficulty": "easy",
            "expected_profit": 2.0,
            "estimated_time_minutes": 5,
            "priority_rank": 41,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Sky Bet",
            "offer_name": "Extra Place Races",
            "offer_type": "other",
            "offer_value": None,
            "required_stake": None,
            "min_odds": None,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Selected races pay extra places. Each-way value.",
            "difficulty": "easy",
            "expected_profit": 3.0,
            "estimated_time_minutes": 10,
            "priority_rank": 42,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Paddy Power",
            "offer_name": "Money Back if 2nd",
            "offer_type": "other",
            "offer_value": 10.0,
            "required_stake": 10.0,
            "min_odds": 1.50,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Selected races - money back if your horse finishes 2nd.",
            "difficulty": "easy",
            "expected_profit": 5.0,
            "estimated_time_minutes": 15,
            "priority_rank": 43,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "William Hill",
            "offer_name": "Best Odds Guaranteed",
            "offer_type": "other",
            "offer_value": None,
            "required_stake": None,
            "min_odds": None,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Best odds guaranteed on all UK & Irish racing.",
            "difficulty": "easy",
            "expected_profit": 2.0,
            "estimated_time_minutes": 5,
            "priority_rank": 44,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Coral",
            "offer_name": "Each-Way Extra",
            "offer_type": "other",
            "offer_value": None,
            "required_stake": None,
            "min_odds": None,
            "wagering_requirement": 1.0,
            "is_stake_returned": False,
            "terms_summary": "Extra places on selected races. Enhanced each-way value.",
            "difficulty": "easy",
            "expected_profit": 3.0,
            "estimated_time_minutes": 10,
            "priority_rank": 45,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        # Casino Offers (46-50)
        {
            "bookmaker": "Bet365",
            "offer_name": "100% Deposit Match up to £100",
            "offer_type": "other",
            "offer_value": 100.0,
            "required_stake": 100.0,
            "min_odds": None,
            "wagering_requirement": 35.0,
            "is_stake_returned": False,
            "terms_summary": "Deposit £100, get £100 bonus. 35x wagering required.",
            "difficulty": "hard",
            "expected_profit": 50.0,
            "estimated_time_minutes": 120,
            "priority_rank": 46,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Sky Bet",
            "offer_name": "50 Free Spins",
            "offer_type": "other",
            "offer_value": 50.0,
            "required_stake": 10.0,
            "min_odds": None,
            "wagering_requirement": 35.0,
            "is_stake_returned": False,
            "terms_summary": "Deposit £10, get 50 free spins. 35x wagering.",
            "difficulty": "hard",
            "expected_profit": 15.0,
            "estimated_time_minutes": 90,
            "priority_rank": 47,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Paddy Power",
            "offer_name": "£10 Casino Bonus",
            "offer_type": "other",
            "offer_value": 10.0,
            "required_stake": 10.0,
            "min_odds": None,
            "wagering_requirement": 30.0,
            "is_stake_returned": False,
            "terms_summary": "Deposit £10, get £10 bonus. 30x wagering.",
            "difficulty": "hard",
            "expected_profit": 5.0,
            "estimated_time_minutes": 60,
            "priority_rank": 48,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "888sport",
            "offer_name": "100% Match + 50 Spins",
            "offer_type": "other",
            "offer_value": 50.0,
            "required_stake": 50.0,
            "min_odds": None,
            "wagering_requirement": 35.0,
            "is_stake_returned": False,
            "terms_summary": "Deposit £50, get £50 bonus + 50 spins. 35x wagering.",
            "difficulty": "hard",
            "expected_profit": 25.0,
            "estimated_time_minutes": 120,
            "priority_rank": 49,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
        {
            "bookmaker": "Betway",
            "offer_name": "Bet £10 Get £10 Casino Bonus",
            "offer_type": "other",
            "offer_value": 10.0,
            "required_stake": 10.0,
            "min_odds": None,
            "wagering_requirement": 35.0,
            "is_stake_returned": False,
            "terms_summary": "Deposit £10, get £10 bonus. 35x wagering required.",
            "difficulty": "medium",
            "expected_profit": 5.0,
            "estimated_time_minutes": 60,
            "priority_rank": 50,
            "is_active": True,
            "signup_url": None,
            "oddschecker_url": "https://www.oddschecker.com/free-bets",
        },
    ]
    supabase.table("offers_catalog").insert(sample_offers).execute()


# ============================================================================
# USER OFFER PROGRESS
# ============================================================================

async def get_active_offers(user_id: str) -> ActiveOffersResponse:
    """Get user's active and completed offers."""
    supabase = get_supabase_client()
    
    # Get all user offer progress
    result = supabase.table("user_offer_progress")\
        .select("*, offers_catalog(*)")\
        .eq("user_id", user_id)\
        .order("started_at", desc=True)\
        .execute()
    
    progress_data = result.data or []
    
    offers = []
    total_profit = 0.0
    active_count = 0
    completed_count = 0
    
    for p in progress_data:
        offer_data = p.pop("offers_catalog", None)
        progress = _parse_user_progress(p)
        if offer_data:
            progress.offer = _parse_offer_catalog(offer_data)
        offers.append(progress)
        
        if p["stage"] == "completed":
            completed_count += 1
            total_profit += float(p.get("total_profit", 0) or 0)
        elif p["stage"] not in ("skipped", "expired", "failed"):
            active_count += 1
    
    return ActiveOffersResponse(
        offers=offers,
        total_active=active_count,
        total_completed=completed_count,
        total_profit=round(total_profit, 2),
    )


async def get_offer_progress(user_id: str, offer_id: str) -> UserOfferProgress:
    """Get user's progress on a specific offer."""
    supabase = get_supabase_client()
    
    result = supabase.table("user_offer_progress")\
        .select("*, offers_catalog(*)")\
        .eq("user_id", user_id)\
        .eq("offer_id", offer_id)\
        .execute()
    
    if not result.data:
        raise ValueError("Offer progress not found")
    
    p = result.data[0]
    offer_data = p.pop("offers_catalog", None)
    progress = _parse_user_progress(p)
    if offer_data:
        progress.offer = _parse_offer_catalog(offer_data)
    
    return progress


async def start_offer(user_id: str, offer_id: str) -> UserOfferProgress:
    """Start a new offer for a user."""
    supabase = get_supabase_client()
    
    # Check offer exists
    offer = await get_offer_by_id(offer_id)
    
    # Check not already started
    existing = supabase.table("user_offer_progress")\
        .select("id")\
        .eq("user_id", user_id)\
        .eq("offer_id", offer_id)\
        .execute()
    
    if existing.data:
        raise ValueError("Offer already started")
    
    # Create progress record
    progress_data = {
        "user_id": user_id,
        "offer_id": offer_id,
        "stage": "selected",
        "free_bet_value": offer.offer_value,
    }
    
    result = supabase.table("user_offer_progress").insert(progress_data).execute()
    
    if not result.data:
        raise ValueError("Failed to start offer")
    
    progress = _parse_user_progress(result.data[0])
    progress.offer = offer
    
    return progress


async def update_offer_progress(
    user_id: str,
    offer_id: str,
    update: UserOfferProgressUpdate,
) -> UserOfferProgress:
    """Update user's offer progress."""
    supabase = get_supabase_client()
    
    # Get current progress
    current = await get_offer_progress(user_id, offer_id)
    
    update_data = update.model_dump(exclude_none=True)
    
    # Validate stage transition
    if "stage" in update_data:
        new_stage = OfferStage(update_data["stage"])
        current_stage = OfferStage(current.stage)
        
        allowed = STAGE_TRANSITIONS.get(current_stage, [])
        if new_stage not in allowed:
            raise ValueError(f"Cannot transition from {current_stage} to {new_stage}")
        
        # Set timestamps based on stage
        now = datetime.utcnow().isoformat()
        if new_stage == OfferStage.ACCOUNT_CREATED:
            update_data["signed_up_at"] = now
        elif new_stage == OfferStage.VERIFIED:
            # Store verified_at in notes or add field if needed
            # For now, we'll use signed_up_at as a proxy if verified_at doesn't exist
            pass
        elif new_stage == OfferStage.QUALIFYING_PLACED:
            update_data["qualifying_placed_at"] = now
        elif new_stage == OfferStage.FREE_BET_AVAILABLE:
            update_data["free_bet_received_at"] = now
        elif new_stage == OfferStage.COMPLETED:
            update_data["completed_at"] = now
            # Calculate total profit (free bet profit minus qualifying loss)
            q_loss = current.qualifying_loss or 0
            fb_profit = update_data.get("free_bet_profit") or current.free_bet_profit or 0
            total_profit = round(fb_profit - abs(q_loss), 2)
            update_data["total_profit"] = total_profit
            
            # Update user's total profit
            await _update_user_total_profit(user_id, total_profit)
    
    result = supabase.table("user_offer_progress")\
        .update(update_data)\
        .eq("user_id", user_id)\
        .eq("offer_id", offer_id)\
        .execute()
    
    if not result.data:
        raise ValueError("Failed to update progress")
    
    return await get_offer_progress(user_id, offer_id)


# ============================================================================
# BOOKMAKER PREFERENCES
# ============================================================================

async def get_bookmaker_preferences(user_id: str) -> BookmakerPreferencesResponse:
    """Get user's bookmaker preferences."""
    supabase = get_supabase_client()
    
    result = supabase.table("user_bookmaker_preferences")\
        .select("bookmaker, preference")\
        .eq("user_id", user_id)\
        .execute()
    
    whitelist = []
    blacklist = []
    
    for p in (result.data or []):
        if p["preference"] == "whitelist":
            whitelist.append(p["bookmaker"])
        else:
            blacklist.append(p["bookmaker"])
    
    return BookmakerPreferencesResponse(whitelist=whitelist, blacklist=blacklist)


async def set_bookmaker_preferences(
    user_id: str,
    preferences: List[BookmakerPreferenceItem],
) -> BookmakerPreferencesResponse:
    """Set user's bookmaker preferences (replaces existing)."""
    supabase = get_supabase_client()
    
    # Delete existing preferences
    supabase.table("user_bookmaker_preferences")\
        .delete()\
        .eq("user_id", user_id)\
        .execute()
    
    # Insert new preferences
    if preferences:
        records = [
            {"user_id": user_id, "bookmaker": p.bookmaker, "preference": p.preference.value}
            for p in preferences
        ]
        supabase.table("user_bookmaker_preferences").insert(records).execute()
    
    return await get_bookmaker_preferences(user_id)


# ============================================================================
# ONBOARDING
# ============================================================================

async def get_onboarding_status(user_id: str) -> OnboardingStatus:
    """Get user's onboarding status."""
    supabase = get_supabase_client()
    
    result = supabase.table("users")\
        .select("onboarding_completed, onboarding_step")\
        .eq("id", user_id)\
        .execute()
    
    if not result.data:
        raise ValueError("User not found")
    
    user = result.data[0]
    
    return OnboardingStatus(
        completed=user.get("onboarding_completed", False),
        current_step=OnboardingStep(user.get("onboarding_step", "welcome")),
    )


async def update_onboarding(user_id: str, step: OnboardingStep, completed: bool = False) -> OnboardingStatus:
    """Update user's onboarding status."""
    supabase = get_supabase_client()
    
    update_data = {"onboarding_step": step.value}
    if completed or step == OnboardingStep.COMPLETED:
        update_data["onboarding_completed"] = True
        update_data["onboarding_step"] = OnboardingStep.COMPLETED.value
    
    supabase.table("users").update(update_data).eq("id", user_id).execute()
    
    return await get_onboarding_status(user_id)


# ============================================================================
# HELPERS
# ============================================================================

async def _update_user_total_profit(user_id: str, profit_to_add: float):
    """Update user's total profit by adding the new profit amount."""
    supabase = get_supabase_client()
    
    # Get current total profit
    result = supabase.table("users").select("total_profit").eq("id", user_id).execute()
    
    if result.data:
        current_profit = float(result.data[0].get("total_profit", 0) or 0)
        new_total = round(current_profit + profit_to_add, 2)
        
        # Update the user's total profit
        supabase.table("users").update({"total_profit": new_total}).eq("id", user_id).execute()
        print(f"Updated user {user_id} total profit: {current_profit} + {profit_to_add} = {new_total}")


def _parse_offer_catalog(data: dict) -> OfferCatalog:
    """Parse offer catalog from database."""
    from decimal import Decimal
    
    # Convert string to enum for difficulty (handle None) - keep as string for serialization
    difficulty_str = data.get("difficulty", "easy")
    if not difficulty_str:
        difficulty_str = "easy"
    try:
        difficulty = OfferDifficulty(difficulty_str.lower())
    except (ValueError, AttributeError):
        difficulty = OfferDifficulty.EASY
    
    # Convert string to enum for offer_type - keep as string for serialization
    offer_type_str = data.get("offer_type", "welcome")
    if not offer_type_str:
        offer_type_str = "welcome"
    try:
        offer_type = OfferType(offer_type_str.lower())
    except (ValueError, AttributeError):
        offer_type = OfferType.WELCOME
    
    # Convert Decimal to float for numeric fields
    def to_float(value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        return value
    
    def to_int(value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return int(value)
        return value
    
    return OfferCatalog(
        id=str(data["id"]),
        bookmaker=str(data["bookmaker"]),
        offer_name=str(data["offer_name"]),
        offer_type=offer_type,
        offer_value=to_float(data.get("offer_value")),
        required_stake=to_float(data.get("required_stake")),
        min_odds=to_float(data.get("min_odds")),
        max_stake=to_float(data.get("max_stake")),
        wagering_requirement=to_float(data.get("wagering_requirement")),
        is_stake_returned=bool(data.get("is_stake_returned", False)),
        qualifying_bet_required=bool(data.get("qualifying_bet_required", True)),
        terms_raw=data.get("terms_raw"),
        terms_summary=data.get("terms_summary"),
        expiry_days=to_int(data.get("expiry_days")),
        eligible_sports=data.get("eligible_sports"),
        eligible_markets=data.get("eligible_markets"),
        signup_url=data.get("signup_url"),
        referral_url=data.get("referral_url"),
        oddschecker_url=data.get("oddschecker_url"),
        difficulty=difficulty,
        expected_profit=to_float(data.get("expected_profit")),
        estimated_time_minutes=to_int(data.get("estimated_time_minutes")),
        is_active=bool(data.get("is_active", True)),
        priority_rank=to_int(data.get("priority_rank")),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _parse_user_progress(data: dict) -> UserOfferProgress:
    """Parse user offer progress from database."""
    return UserOfferProgress(
        id=data["id"],
        user_id=data["user_id"],
        offer_id=data["offer_id"],
        stage=data["stage"],
        qualifying_bet_id=data.get("qualifying_bet_id"),
        qualifying_stake=data.get("qualifying_stake"),
        qualifying_odds=data.get("qualifying_odds"),
        qualifying_loss=data.get("qualifying_loss"),
        free_bet_id=data.get("free_bet_id"),
        free_bet_value=data.get("free_bet_value"),
        free_bet_profit=data.get("free_bet_profit"),
        total_profit=data.get("total_profit"),
        notes=data.get("notes"),
        started_at=data["started_at"],
        signed_up_at=data.get("signed_up_at"),
        qualifying_placed_at=data.get("qualifying_placed_at"),
        free_bet_received_at=data.get("free_bet_received_at"),
        completed_at=data.get("completed_at"),
    )

