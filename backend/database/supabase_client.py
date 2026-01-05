"""Supabase database client and operations."""
from typing import List, Optional
from supabase import create_client, Client
from backend.models.offer import OfferRanked
from backend.config import Config

"""
Supabase Table Schema:

CREATE TABLE offers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bookmaker TEXT NOT NULL,
  offer_value DECIMAL(10,2),
  required_stake DECIMAL(10,2),
  min_odds DECIMAL(5,2),
  expiry_days INTEGER,
  bet_type TEXT,
  value_index DECIMAL(10,4),
  scraped_at TIMESTAMP DEFAULT NOW(),
  raw_text TEXT
);

Create index for faster queries:
CREATE INDEX idx_scraped_at ON offers(scraped_at DESC);
CREATE INDEX idx_value_index ON offers(value_index DESC);
"""

_client: Optional[Client] = None


def init_supabase() -> Client:
    """Initialize and return Supabase client."""
    global _client
    if _client is None:
        _client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    return _client


def get_supabase_client() -> Client:
    """Get the Supabase client (alias for init_supabase)."""
    return init_supabase()


def save_offers(offers: List[OfferRanked]) -> bool:
    """
    Save ranked offers to Supabase.
    
    Args:
        offers: List of ranked offers to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = init_supabase()
        
        # Convert offers to dict format for Supabase
        records = []
        for offer in offers:
            record = {
                "bookmaker": offer.bookmaker,
                "offer_value": offer.offer_value,
                "required_stake": offer.required_stake,
                "min_odds": offer.min_odds,
                "expiry_days": offer.expiry_days,
                "bet_type": offer.bet_type,
                "value_index": float(offer.value_index),
                "raw_text": offer.raw_text
            }
            records.append(record)
        
        # Batch insert
        if records:
            response = client.table("offers").insert(records).execute()
            print(f"Successfully saved {len(records)} offers to Supabase")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error saving offers to Supabase: {e}")
        return False


def get_latest_offers(limit: int = 50) -> List[dict]:
    """
    Retrieve latest offers from Supabase.
    
    Args:
        limit: Maximum number of offers to retrieve
        
    Returns:
        List of offer dictionaries
    """
    try:
        client = init_supabase()
        
        response = client.table("offers")\
            .select("*")\
            .order("scraped_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"Error retrieving offers from Supabase: {e}")
        return []



