"""Service for managing bet logging."""
from datetime import datetime
from typing import List, Optional
from backend.database.supabase_client import get_supabase_client
from backend.models.bet import (
    LogBetRequest,
    Bet,
    SettleBetRequest,
    UpdateBetRequest,
    BetsResponse,
    BetStats,
    BetType,
    BetOutcome,
)


async def log_bet(user_id: str, data: LogBetRequest) -> Bet:
    """Log a new bet."""
    supabase = get_supabase_client()
    
    # Handle event_date conversion safely (now always a string or None)
    event_date_str = None
    if data.event_date and data.event_date.strip():
        try:
            # Try parsing ISO format strings and reformatting for database
            if "T" in data.event_date or " " in data.event_date:
                # Handle ISO format with or without timezone
                v_clean = data.event_date.replace("Z", "+00:00")
                dt = datetime.fromisoformat(v_clean)
                event_date_str = dt.isoformat()
            else:
                # If it's not a recognizable format, use as-is (database might accept it)
                event_date_str = data.event_date
        except (ValueError, AttributeError) as e:
            # If parsing fails, log but still try to use the string
            print(f"Warning: Could not parse event_date '{data.event_date}': {e}")
            event_date_str = data.event_date
    
    # Build bet_data with proper type conversions and None handling
    bet_data = {
        "user_id": user_id,  # Keep as UUID string, don't convert
        "offer_id": data.offer_id if data.offer_id else None,
        "bet_type": data.bet_type.value,
        "bookmaker": str(data.bookmaker).strip(),
        "exchange": str(data.exchange).strip() if data.exchange else "Betfair",
        "event_name": str(data.event_name).strip(),
        "selection": str(data.selection).strip(),
        "event_date": event_date_str,
        "back_odds": float(data.back_odds),
        "back_stake": float(data.back_stake),
        "lay_odds": float(data.lay_odds),
        "lay_stake": float(data.lay_stake),
        "liability": float(data.liability),
        "commission": float(data.commission) if data.commission is not None else 0.05,
        "expected_profit": float(data.expected_profit),
        "outcome": "pending",
        "notes": str(data.notes).strip() if data.notes else None,
    }
    
    try:
        print(f"Inserting bet with data: {bet_data}")
        result = supabase.table("bets").insert(bet_data).execute()
        
        # Check for Supabase errors
        if hasattr(result, 'error') and result.error:
            error_msg = str(result.error)
            print(f"Supabase error: {error_msg}")
            raise ValueError(f"Database error: {error_msg}")
        
        if not result.data or len(result.data) == 0:
            raise ValueError("Failed to log bet: No data returned from database")
        
        return _parse_bet(result.data[0])
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        # Log the error with more context
        import traceback
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"Error inserting bet: {error_msg}")
        print(f"Error type: {error_type}")
        print(f"Bet data: {bet_data}")
        traceback.print_exc()
        
        # Check if it's a foreign key violation on offer_id (V3 offers_catalog IDs)
        # This happens when offer_id references offers_catalog instead of saved_offers
        if "foreign key" in error_msg.lower() or "violates foreign key constraint" in error_msg.lower() or "bets_offer_id_fkey" in error_msg.lower():
            print("Foreign key error detected - retrying without offer_id")
            # Retry without the offer_id (the relationship is tracked in user_offer_progress)
            bet_data["offer_id"] = None
            try:
                result = supabase.table("bets").insert(bet_data).execute()
                if result.data and len(result.data) > 0:
                    return _parse_bet(result.data[0])
            except Exception as retry_error:
                print(f"Retry also failed: {retry_error}")
        
        # Check if it's a Supabase client error
        if "supabase" in error_type.lower() or "postgres" in error_msg.lower():
            raise ValueError(f"Database error: {error_msg}")
        raise ValueError(f"Failed to log bet: {error_msg}")


async def get_bets(
    user_id: str,
    outcome: Optional[BetOutcome] = None,
    limit: int = 50,
) -> BetsResponse:
    """Get all bets for a user."""
    supabase = get_supabase_client()
    
    query = supabase.table("bets").select("*").eq("user_id", user_id)
    
    if outcome:
        query = query.eq("outcome", outcome.value)
    
    query = query.order("created_at", desc=True).limit(limit)
    result = query.execute()
    
    bets = [_parse_bet(b) for b in (result.data or [])]
    
    # Get counts and totals
    all_bets = supabase.table("bets").select("outcome, actual_profit").eq("user_id", user_id).execute()
    all_data = all_bets.data or []
    
    pending_count = len([b for b in all_data if b["outcome"] == "pending"])
    settled_count = len([b for b in all_data if b["outcome"] != "pending"])
    total_profit = sum(float(b.get("actual_profit", 0) or 0) for b in all_data if b["outcome"] != "pending")
    
    return BetsResponse(
        bets=bets,
        total=len(all_data),
        pending_count=pending_count,
        settled_count=settled_count,
        total_profit=round(total_profit, 2),
    )


async def get_bet(user_id: str, bet_id: str) -> Bet:
    """Get a specific bet."""
    supabase = get_supabase_client()
    
    result = supabase.table("bets").select("*").eq("id", bet_id).eq("user_id", user_id).execute()
    
    if not result.data:
        raise ValueError("Bet not found")
    
    return _parse_bet(result.data[0])


async def settle_bet(user_id: str, bet_id: str, data: SettleBetRequest) -> Bet:
    """Settle a bet with the outcome."""
    supabase = get_supabase_client()
    
    # Get the bet first
    bet = await get_bet(user_id, bet_id)
    
    # Calculate actual profit based on outcome
    if data.actual_profit is not None:
        actual_profit = data.actual_profit
    else:
        # Auto-calculate based on outcome
        if data.outcome == BetOutcome.BACK_WON:
            # Back bet won: profit = back_stake * (back_odds - 1) - liability
            actual_profit = bet.back_stake * (bet.back_odds - 1) - bet.liability
        else:
            # Lay bet won: profit = lay_stake * (1 - commission) - back_stake
            actual_profit = bet.lay_stake * (1 - bet.commission) - bet.back_stake
        
        # For free bets, the calculation is different
        if bet.bet_type == BetType.FREE_BET_SNR:
            if data.outcome == BetOutcome.BACK_WON:
                actual_profit = bet.back_stake * (bet.back_odds - 1) - bet.liability
            else:
                actual_profit = bet.lay_stake * (1 - bet.commission)
    
    update_data = {
        "outcome": data.outcome.value,
        "actual_profit": round(actual_profit, 2),
        "settled_at": datetime.utcnow().isoformat(),
    }
    
    result = supabase.table("bets").update(update_data).eq("id", bet_id).eq("user_id", user_id).execute()
    
    if not result.data:
        raise ValueError("Failed to settle bet")
    
    # Update user's total profit
    await _update_user_profit(user_id)
    
    return _parse_bet(result.data[0])


async def update_bet(user_id: str, bet_id: str, data: UpdateBetRequest) -> Bet:
    """Update a bet's notes or event date."""
    supabase = get_supabase_client()
    
    update_data = {}
    
    if data.notes is not None:
        update_data["notes"] = data.notes
    
    if data.event_date is not None:
        update_data["event_date"] = data.event_date.isoformat()
    
    if not update_data:
        return await get_bet(user_id, bet_id)
    
    result = supabase.table("bets").update(update_data).eq("id", bet_id).eq("user_id", user_id).execute()
    
    if not result.data:
        raise ValueError("Failed to update bet")
    
    return _parse_bet(result.data[0])


async def delete_bet(user_id: str, bet_id: str) -> bool:
    """Delete a bet."""
    supabase = get_supabase_client()
    
    result = supabase.table("bets").delete().eq("id", bet_id).eq("user_id", user_id).execute()
    
    if result.data:
        await _update_user_profit(user_id)
    
    return len(result.data or []) > 0


async def get_bet_stats(user_id: str) -> BetStats:
    """Get detailed betting statistics."""
    supabase = get_supabase_client()
    
    result = supabase.table("bets").select("*").eq("user_id", user_id).execute()
    bets = result.data or []
    
    total_bets = len(bets)
    pending_bets = len([b for b in bets if b["outcome"] == "pending"])
    settled_bets = total_bets - pending_bets
    
    settled = [b for b in bets if b["outcome"] != "pending"]
    
    total_profit = sum(float(b.get("actual_profit", 0) or 0) for b in settled)
    total_stake = sum(float(b.get("back_stake", 0) or 0) for b in bets)
    total_liability = sum(float(b.get("liability", 0) or 0) for b in bets)
    
    profits = [float(b.get("actual_profit", 0) or 0) for b in settled]
    best_profit = max(profits) if profits else 0
    worst_loss = min(profits) if profits else 0
    
    qualifying_bets = len([b for b in bets if b["bet_type"] == "qualifying"])
    free_bets = len([b for b in bets if b["bet_type"] in ["free_bet_snr", "free_bet_sr"]])
    
    # Profit by bookmaker
    profit_by_bookmaker = {}
    for b in settled:
        bm = b.get("bookmaker", "Unknown")
        profit = float(b.get("actual_profit", 0) or 0)
        profit_by_bookmaker[bm] = profit_by_bookmaker.get(bm, 0) + profit
    
    # Round values
    for k in profit_by_bookmaker:
        profit_by_bookmaker[k] = round(profit_by_bookmaker[k], 2)
    
    return BetStats(
        total_bets=total_bets,
        pending_bets=pending_bets,
        settled_bets=settled_bets,
        total_profit=round(total_profit, 2),
        total_stake=round(total_stake, 2),
        total_liability=round(total_liability, 2),
        avg_profit_per_bet=round(total_profit / settled_bets, 2) if settled_bets > 0 else 0,
        best_profit=round(best_profit, 2),
        worst_loss=round(worst_loss, 2),
        qualifying_bets=qualifying_bets,
        free_bets=free_bets,
        profit_by_bookmaker=profit_by_bookmaker,
    )


async def _update_user_profit(user_id: str):
    """Update user's total profit from settled bets."""
    supabase = get_supabase_client()
    
    result = supabase.table("bets").select("actual_profit").eq("user_id", user_id).neq("outcome", "pending").execute()
    
    total = sum(float(b.get("actual_profit", 0) or 0) for b in (result.data or []))
    
    supabase.table("users").update({"total_profit": round(total, 2)}).eq("id", user_id).execute()


def _parse_bet(data: dict) -> Bet:
    """Parse bet data from database."""
    # Parse event_date from string to datetime if needed
    event_date = None
    if data.get("event_date"):
        try:
            if isinstance(data["event_date"], str):
                # Parse ISO format string
                event_date_str = data["event_date"].replace("Z", "+00:00")
                event_date = datetime.fromisoformat(event_date_str)
            elif isinstance(data["event_date"], datetime):
                event_date = data["event_date"]
        except (ValueError, AttributeError, TypeError) as e:
            print(f"Warning: Could not parse event_date: {e}")
            event_date = None
    
    # Parse created_at - must be valid datetime
    created_at = data.get("created_at")
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError, TypeError):
            # Fallback to current time if parsing fails
            print(f"Warning: Could not parse created_at '{created_at}', using current time")
            created_at = datetime.utcnow()
    elif not isinstance(created_at, datetime):
        created_at = datetime.utcnow()
    
    # Parse settled_at
    settled_at = data.get("settled_at")
    if settled_at:
        if isinstance(settled_at, str):
            try:
                settled_at = datetime.fromisoformat(settled_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError, TypeError):
                settled_at = None
        elif not isinstance(settled_at, datetime):
            settled_at = None
    
    return Bet(
        id=str(data["id"]),
        user_id=str(data["user_id"]),
        offer_id=str(data["offer_id"]) if data.get("offer_id") else None,
        bet_type=BetType(data["bet_type"]),
        bookmaker=str(data["bookmaker"]),
        exchange=str(data.get("exchange", "Betfair")),
        event_name=str(data["event_name"]),
        selection=str(data["selection"]),
        event_date=event_date,
        back_odds=float(data["back_odds"]),
        back_stake=float(data["back_stake"]),
        lay_odds=float(data["lay_odds"]),
        lay_stake=float(data["lay_stake"]),
        liability=float(data["liability"]),
        commission=float(data.get("commission", 0.05)),
        expected_profit=float(data["expected_profit"]),
        actual_profit=float(data["actual_profit"]) if data.get("actual_profit") else None,
        outcome=BetOutcome(data["outcome"]),
        notes=data.get("notes"),
        created_at=created_at,
        settled_at=settled_at,
    )

