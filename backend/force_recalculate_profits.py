"""Force re-calculate all offer profits using LLM."""
import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from backend.database.supabase_client import get_supabase_client
from backend.services.offers_catalog import _parse_offer_catalog
from backend.utils.offers_calculator import calculate_expected_profit_with_llm
from backend.models.offers_catalog import OfferCatalog

async def force_recalculate_all():
    """Force re-calculate profits for all offers using LLM."""
    supabase = get_supabase_client()
    
    # Top 10 mainstream bookmakers to prioritize
    TOP_10 = ["bet365", "betfair", "sky bet", "paddy power", "william hill", "betway", "coral", "ladbrokes", "betvictor", "unibet"]
    
    # Get all active offers
    result = supabase.table("offers_catalog")\
        .select("*")\
        .eq("is_active", True)\
        .execute()
    
    offers_data = result.data or []
    print(f"Found {len(offers_data)} active offers to recalculate")
    
    # Sort: top 10 first, then others
    def is_top_10(bookmaker):
        if not bookmaker:
            return False
        bm_lower = bookmaker.lower().strip()
        return any(top in bm_lower or bm_lower in top for top in TOP_10)
    
    offers_data.sort(key=lambda x: (0 if is_top_10(x.get("bookmaker", "")) else 1, x.get("expected_profit") or 0), reverse=True)
    print(f"Prioritizing top 10 mainstream bookmakers first...")
    
    updated = 0
    skipped = 0
    failed = 0
    
    for offer_data in offers_data:
        try:
            parsed = _parse_offer_catalog(offer_data)
            
            # Skip if no offer_value
            if not parsed.offer_value or parsed.offer_value <= 0:
                print(f"Skipping {parsed.bookmaker} - no offer_value")
                skipped += 1
                continue
            
            # Force LLM calculation
            print(f"Calculating profit for {parsed.bookmaker}...")
            new_profit = calculate_expected_profit_with_llm(parsed)
            
            if new_profit is not None:
                # Update in database
                supabase.table("offers_catalog")\
                    .update({"expected_profit": new_profit})\
                    .eq("id", parsed.id)\
                    .execute()
                print(f"  [OK] Updated {parsed.bookmaker}: ${new_profit}")
                updated += 1
            else:
                print(f"  [FAIL] Failed to calculate for {parsed.bookmaker}")
                failed += 1
                
        except Exception as e:
            print(f"  [ERROR] Error processing {offer_data.get('bookmaker', 'unknown')}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Summary: {updated} updated, {skipped} skipped, {failed} failed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(force_recalculate_all())

