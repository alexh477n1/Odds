"""Script to update Betway and Betwright offer values to £10."""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.supabase_client import get_supabase_client


def update_betway_values():
    """Update Betway and Betwright offers to have £10 values."""
    supabase = get_supabase_client()
    
    # Find all Betway and Betwright offers
    result = supabase.table("offers_catalog").select("id, bookmaker, offer_name, offer_value, required_stake, expected_profit").execute()
    
    updated_count = 0
    for offer in result.data or []:
        bookmaker = offer.get("bookmaker", "").lower()
        
        # Check if it's Betway or Betwright
        if "betway" in bookmaker or "betwright" in bookmaker:
            print(f"Found: {offer['bookmaker']} - {offer['offer_name']}")
            print(f"  Current values: offer_value={offer['offer_value']}, required_stake={offer['required_stake']}, expected_profit={offer['expected_profit']}")
            
            # Update to £10 values
            update_data = {
                "offer_value": 10.0,
                "required_stake": 10.0,
                "expected_profit": 7.0,  # ~70% of free bet value is typical profit
            }
            
            supabase.table("offers_catalog").update(update_data).eq("id", offer["id"]).execute()
            print(f"  Updated to: offer_value=10.0, required_stake=10.0, expected_profit=7.0")
            updated_count += 1
    
    print(f"\nTotal offers updated: {updated_count}")
    return updated_count


if __name__ == "__main__":
    update_betway_values()

