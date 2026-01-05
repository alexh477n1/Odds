"""
ONE-TIME SCRIPT: Scrape all offers, calculate LLM profits, store in database.
Run this ONCE to populate the database with all offers and their LLM-calculated profits.

Run from project root: python backend/one_time_scrape_and_calculate.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.offers_catalog import update_offers_from_scraper
from backend.database.supabase_client import get_supabase_client
from backend.utils.offers_calculator import calculate_expected_profit_with_llm, calculate_terms_hash
from backend.services.offers_catalog import _parse_offer_catalog


async def main():
    """Scrape offers, calculate LLM profits, store in DB."""
    print("=" * 60)
    print("ONE-TIME SCRAPE AND LLM CALCULATION")
    print("=" * 60)
    
    supabase = get_supabase_client()
    
    # Step 1: Scrape and create/update offers
    print("\n[1/2] Scraping offers from Oddschecker...")
    try:
        result = await update_offers_from_scraper()
        print(f"✓ Scraped {result['scraped_count']} offers")
        print(f"✓ Created {result.get('created_count', 0)} new offers")
        print(f"✓ Updated {result.get('updated_count', 0)} existing offers")
    except Exception as e:
        print(f"✗ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Calculate LLM profits for ALL offers that don't have them
    print("\n[2/2] Calculating LLM profits for all offers...")
    
    # Get all offers
    all_offers = supabase.table("offers_catalog")\
        .select("*")\
        .eq("is_active", True)\
        .not_.is_("offer_value", "null")\
        .gt("offer_value", 0)\
        .execute()
    
    offers_data = all_offers.data or []
    print(f"Found {len(offers_data)} active offers")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, offer_data in enumerate(offers_data, 1):
        try:
            parsed = _parse_offer_catalog(offer_data)
            
            # Calculate current terms hash
            current_hash = calculate_terms_hash(parsed.terms_summary)
            stored_hash = offer_data.get("terms_hash")
            
            # Skip if already calculated and terms haven't changed
            if parsed.expected_profit is not None and current_hash == stored_hash:
                print(f"[{idx}/{len(offers_data)}] ✓ {parsed.bookmaker} - Already has profit: £{parsed.expected_profit}")
                skipped_count += 1
                continue
            
            # Calculate LLM profit
            print(f"[{idx}/{len(offers_data)}] Calculating LLM profit for {parsed.bookmaker}...")
            llm_profit = calculate_expected_profit_with_llm(parsed)
            
            if llm_profit is not None:
                # Update in database
                try:
                    supabase.table("offers_catalog").update({
                        "expected_profit": llm_profit,
                        "terms_hash": current_hash
                    }).eq("id", parsed.id).execute()
                    print(f"  ✓ Stored profit: £{llm_profit}")
                    updated_count += 1
                except Exception as e:
                    # If terms_hash column doesn't exist, try without it
                    if "terms_hash" in str(e) or "PGRST204" in str(e):
                        try:
                            supabase.table("offers_catalog").update({
                                "expected_profit": llm_profit,
                            }).eq("id", parsed.id).execute()
                            print(f"  ✓ Stored profit: £{llm_profit} (without terms_hash)")
                            updated_count += 1
                        except Exception as e2:
                            print(f"  ✗ Failed to update: {e2}")
                            error_count += 1
                    else:
                        print(f"  ✗ Failed to update: {e}")
                        error_count += 1
            else:
                print(f"  ⚠ LLM calculation failed, keeping existing profit or formula fallback")
                error_count += 1
                
        except Exception as e:
            print(f"  ✗ Error processing {offer_data.get('bookmaker', 'unknown')}: {e}")
            error_count += 1
            continue
    
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Total offers: {len(offers_data)}")
    print(f"Updated with LLM profit: {updated_count}")
    print(f"Skipped (already calculated): {skipped_count}")
    print(f"Errors: {error_count}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

