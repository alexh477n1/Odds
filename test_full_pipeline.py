"""Test the full pipeline: scrape -> parse -> rank -> save."""
import os
import sys
from datetime import datetime

print("=" * 60)
print("FULL PIPELINE TEST")
print("=" * 60)

# Step 1: Scrape offers
print("\n[1/4] Scraping offers from Oddschecker...")
from backend.scraper.oddschecker_scraper import scrape_offers
raw_offers = scrape_offers()
print(f"    [OK] Scraped {len(raw_offers)} raw offers")

if not raw_offers:
    print("    [FAIL] No offers found, stopping test")
    sys.exit(1)

# Step 2: Parse with Gemini (parse ALL offers)
print(f"\n[2/4] Parsing ALL {len(raw_offers)} offers with Gemini...")
from backend.scraper.parser import parse_offer_with_llm
import time

parsed_offers = []
failed_offers = []
raw_text_list = []

# Track statistics
start_parse_time = time.time()
success_count = 0
fail_count = 0

for idx, raw_offer in enumerate(raw_offers, 1):
    # Show progress every 10 offers or on last offer
    if idx % 10 == 0 or idx == len(raw_offers):
        elapsed = time.time() - start_parse_time
        rate = idx / elapsed if elapsed > 0 else 0
        remaining = (len(raw_offers) - idx) / rate if rate > 0 else 0
        print(f"    Progress: {idx}/{len(raw_offers)} ({success_count} success, {fail_count} failed) - ETA: {remaining:.0f}s")
    
    parsed = parse_offer_with_llm(raw_offer.raw_text, raw_offer.bookmaker_hint)
    
    if parsed:
        parsed_offers.append(parsed)
        raw_text_list.append(raw_offer.raw_text)
        success_count += 1
    else:
        failed_offers.append({
            "index": idx,
            "preview": raw_offer.raw_text[:100] + "..." if len(raw_offer.raw_text) > 100 else raw_offer.raw_text,
            "bookmaker_hint": raw_offer.bookmaker_hint
        })
        fail_count += 1
        # Small delay on failures to avoid rate limits
        time.sleep(0.5)

parse_duration = time.time() - start_parse_time
success_rate = (success_count / len(raw_offers) * 100) if raw_offers else 0

print(f"\n    [OK] Parsing complete!")
print(f"    Success: {success_count}/{len(raw_offers)} ({success_rate:.1f}%)")
print(f"    Failed: {fail_count}/{len(raw_offers)}")
print(f"    Duration: {parse_duration:.1f}s ({len(raw_offers)/parse_duration:.1f} offers/sec)")

# Show sample of successfully parsed offers
if parsed_offers:
    print(f"\n    Sample parsed offers:")
    for offer in parsed_offers[:5]:
        print(f"      - {offer.bookmaker}: Bet {offer.required_stake} Get {offer.offer_value} (Odds: {offer.min_odds}, Type: {offer.bet_type})")

# Show failed offers if any
if failed_offers:
    print(f"\n    Failed offers preview (first 5):")
    for fail in failed_offers[:5]:
        print(f"      [{fail['index']}] Hint: {fail['bookmaker_hint']} - {fail['preview']}")

if not parsed_offers:
    print("    [FAIL] No offers parsed successfully, stopping test")
    sys.exit(1)

# Step 3: Rank offers
print("\n[3/4] Ranking offers by Value Index...")
from backend.utils.ranking import rank_offers

ranked_offers = rank_offers(parsed_offers, raw_texts=raw_text_list)
print(f"    [OK] Ranked {len(ranked_offers)} offers")

# Show top 10 ranked offers
print(f"\n    Top 10 offers by Value Index:")
for offer in ranked_offers[:10]:
    print(f"      Rank {offer.rank}: {offer.bookmaker} - Value Index: {offer.value_index:.2f} (Bet {offer.required_stake} Get {offer.offer_value})")

# Step 4: Test Supabase connection and save
print("\n[4/4] Testing Supabase connection...")
try:
    from backend.database.supabase_client import init_supabase, save_offers
    client = init_supabase()
    print("    [OK] Supabase client initialized")
    
    # Try to save offers
    print("    Attempting to save offers to Supabase...")
    success = save_offers(ranked_offers)
    if success:
        print(f"    [OK] Successfully saved {len(ranked_offers)} offers to Supabase")
    else:
        print("    [FAIL] Failed to save offers (check Supabase table exists)")
except Exception as e:
    print(f"    [FAIL] Supabase error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("FULL PIPELINE TEST COMPLETE")
print("=" * 60)
print(f"Summary:")
print(f"  - Scraped: {len(raw_offers)} offers")
print(f"  - Parsed: {success_count} offers ({success_rate:.1f}% success rate)")
print(f"  - Failed: {fail_count} offers")
print(f"  - Ranked: {len(ranked_offers)} offers")
print(f"  - Saved to Supabase: {len(ranked_offers) if success else 0} offers")
print("=" * 60)

