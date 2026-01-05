"""Service for managing saved offers."""
from datetime import datetime
from typing import List, Optional
from backend.database.supabase_client import get_supabase_client
from backend.models.saved_offer import (
    SaveOfferRequest,
    SavedOffer,
    UpdateOfferRequest,
    SavedOffersResponse,
    OfferStatus,
)


async def save_offer(user_id: str, data: SaveOfferRequest) -> SavedOffer:
    """Save a new offer for a user."""
    supabase = get_supabase_client()
    
    offer_data = {
        "user_id": user_id,
        "bookmaker": data.bookmaker,
        "offer_name": data.offer_name,
        "offer_value": data.offer_value,
        "required_stake": data.required_stake,
        "min_odds": data.min_odds,
        "notes": data.notes,
        "expected_profit": data.expected_profit,
        "status": "pending",
    }
    
    result = supabase.table("saved_offers").insert(offer_data).execute()
    
    if not result.data:
        raise ValueError("Failed to save offer")
    
    offer = result.data[0]
    return _parse_offer(offer)


async def get_saved_offers(
    user_id: str,
    status: Optional[OfferStatus] = None,
    limit: int = 50,
) -> SavedOffersResponse:
    """Get all saved offers for a user."""
    supabase = get_supabase_client()
    
    query = supabase.table("saved_offers").select("*").eq("user_id", user_id)
    
    if status:
        query = query.eq("status", status.value)
    
    query = query.order("created_at", desc=True).limit(limit)
    result = query.execute()
    
    offers = [_parse_offer(o) for o in (result.data or [])]
    
    # Get counts
    all_offers = supabase.table("saved_offers").select("status").eq("user_id", user_id).execute()
    all_data = all_offers.data or []
    
    pending_count = len([o for o in all_data if o["status"] == "pending"])
    in_progress_count = len([o for o in all_data if o["status"] == "in_progress"])
    completed_count = len([o for o in all_data if o["status"] == "completed"])
    
    return SavedOffersResponse(
        offers=offers,
        total=len(all_data),
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        completed_count=completed_count,
    )


async def get_offer(user_id: str, offer_id: str) -> SavedOffer:
    """Get a specific saved offer."""
    supabase = get_supabase_client()
    
    result = supabase.table("saved_offers").select("*").eq("id", offer_id).eq("user_id", user_id).execute()
    
    if not result.data:
        raise ValueError("Offer not found")
    
    return _parse_offer(result.data[0])


async def update_offer(user_id: str, offer_id: str, data: UpdateOfferRequest) -> SavedOffer:
    """Update a saved offer."""
    supabase = get_supabase_client()
    
    update_data = {}
    
    if data.status is not None:
        update_data["status"] = data.status.value
        if data.status == OfferStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow().isoformat()
    
    if data.notes is not None:
        update_data["notes"] = data.notes
    
    if data.actual_profit is not None:
        update_data["actual_profit"] = data.actual_profit
    
    if not update_data:
        return await get_offer(user_id, offer_id)
    
    result = supabase.table("saved_offers").update(update_data).eq("id", offer_id).eq("user_id", user_id).execute()
    
    if not result.data:
        raise ValueError("Failed to update offer")
    
    return _parse_offer(result.data[0])


async def delete_offer(user_id: str, offer_id: str) -> bool:
    """Delete a saved offer."""
    supabase = get_supabase_client()
    
    result = supabase.table("saved_offers").delete().eq("id", offer_id).eq("user_id", user_id).execute()
    
    return len(result.data or []) > 0


def _parse_offer(data: dict) -> SavedOffer:
    """Parse offer data from database."""
    return SavedOffer(
        id=data["id"],
        user_id=data["user_id"],
        bookmaker=data["bookmaker"],
        offer_name=data["offer_name"],
        offer_value=data.get("offer_value"),
        required_stake=data.get("required_stake"),
        min_odds=data.get("min_odds"),
        status=OfferStatus(data["status"]),
        notes=data.get("notes"),
        expected_profit=data.get("expected_profit"),
        actual_profit=data.get("actual_profit"),
        created_at=data["created_at"],
        completed_at=data.get("completed_at"),
    )





