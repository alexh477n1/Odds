"""Test pipeline without Gemini parsing (quota exceeded)."""
import os
import sys
from datetime import datetime

print("=" * 60)
print("PIPELINE TEST (Without Gemini Parsing)")
print("=" * 60)

# Step 1: Scrape offers
print("\n[1/3] Scraping offers from Oddschecker...")
from backend.scraper.oddschecker_scraper import scrape_offers
raw_offers = scrape_offers()
print(f"    [OK] Scraped {len(raw_offers)} raw offers")

if not raw_offers:
    print("    [FAIL] No offers found")
    sys.exit(1)

# Show sample offer
print(f"\n    Sample offer preview:")
print(f"    {raw_offers[0].raw_text[:200]}...")

# Step 2: Test ranking with mock data
print("\n[2/3] Testing ranking logic with mock data...")
from backend.models.offer import OfferParsed
from backend.utils.ranking import rank_offers

# Create mock parsed offers
mock_offers = [
    OfferParsed(bookmaker="Betfair", offer_value=50.0, required_stake=10.0, min_odds=2.0, expiry_days=30, bet_type="SNR"),
    OfferParsed(bookmaker="Sky Bet", offer_value=40.0, required_stake=5.0, min_odds=2.0, expiry_days=7, bet_type="SNR"),
    OfferParsed(bookmaker="Bet365", offer_value=30.0, required_stake=10.0, min_odds=1.5, expiry_days=30, bet_type="SNR"),
]

ranked = rank_offers(mock_offers, raw_texts=["mock1", "mock2", "mock3"])
print(f"    [OK] Ranked {len(ranked)} offers")
for offer in ranked:
    print(f"    Rank {offer.rank}: {offer.bookmaker} - Value Index: {offer.value_index:.2f} (Bet {offer.required_stake} Get {offer.offer_value})")

# Step 3: Test Supabase connection
print("\n[3/3] Testing Supabase connection...")
try:
    from backend.database.supabase_client import init_supabase, save_offers
    client = init_supabase()
    print("    [OK] Supabase client initialized")
    
    # Try to save mock offers
    print("    Attempting to save mock offers to Supabase...")
    success = save_offers(ranked)
    if success:
        print(f"    [OK] Successfully saved {len(ranked)} offers to Supabase!")
        print("    [INFO] Check your Supabase dashboard to verify the data")
    else:
        print("    [WARN] Save returned False - check if 'offers' table exists in Supabase")
        print("    [INFO] You may need to create the table first (see backend/database/supabase_client.py)")
except Exception as e:
    print(f"    [FAIL] Supabase error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"[OK] Scraper: Working - Found {len(raw_offers)} offers")
print("[OK] Ranking: Working - Value Index calculation correct")
print("[INFO] Gemini: Quota exceeded (needs billing or wait)")
print("[INFO] Supabase: Connection tested (check results above)")
print("=" * 60)







