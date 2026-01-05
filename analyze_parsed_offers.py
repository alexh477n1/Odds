"""Analyze the quality of parsed offers."""
from backend.database.supabase_client import get_latest_offers
import json

print("=" * 60)
print("PARSING QUALITY ANALYSIS")
print("=" * 60)

# Get offers from Supabase
offers = get_latest_offers(limit=200)

if not offers:
    print("[INFO] No offers found in database. Run test_full_pipeline.py first.")
    exit(0)

print(f"\nTotal offers in database: {len(offers)}")

# Analyze parsing quality
total = len(offers)
unknown_bookmaker = sum(1 for o in offers if o.get("bookmaker") == "Unknown" or not o.get("bookmaker"))
missing_offer_value = sum(1 for o in offers if not o.get("offer_value") or o.get("offer_value") is None)
missing_stake = sum(1 for o in offers if not o.get("required_stake") or o.get("required_stake") is None)
missing_odds = sum(1 for o in offers if not o.get("min_odds") or o.get("min_odds") is None)
missing_expiry = sum(1 for o in offers if not o.get("expiry_days") or o.get("expiry_days") is None)

print(f"\nParsing Quality Metrics:")
print(f"  - Unknown bookmaker: {unknown_bookmaker}/{total} ({unknown_bookmaker/total*100:.1f}%)")
print(f"  - Missing offer_value: {missing_offer_value}/{total} ({missing_offer_value/total*100:.1f}%)")
print(f"  - Missing required_stake: {missing_stake}/{total} ({missing_stake/total*100:.1f}%)")
print(f"  - Missing min_odds: {missing_odds}/{total} ({missing_odds/total*100:.1f}%)")
print(f"  - Missing expiry_days: {missing_expiry}/{total} ({missing_expiry/total*100:.1f}%)")

# Bookmaker distribution
bookmakers = {}
for offer in offers:
    bm = offer.get("bookmaker", "Unknown")
    bookmakers[bm] = bookmakers.get(bm, 0) + 1

print(f"\nTop 15 Bookmakers:")
sorted_bms = sorted(bookmakers.items(), key=lambda x: x[1], reverse=True)
for bm, count in sorted_bms[:15]:
    print(f"  - {bm}: {count} offers")

# Bet type distribution
bet_types = {}
for offer in offers:
    bt = offer.get("bet_type", "Unknown")
    bet_types[bt] = bet_types.get(bt, 0) + 1

print(f"\nBet Type Distribution:")
for bt, count in sorted(bet_types.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {bt}: {count} offers")

# Value index distribution
value_indices = [o.get("value_index", 0) for o in offers if o.get("value_index")]
if value_indices:
    print(f"\nValue Index Statistics:")
    print(f"  - Average: {sum(value_indices)/len(value_indices):.2f}")
    print(f"  - Max: {max(value_indices):.2f}")
    print(f"  - Min: {min(value_indices):.2f}")
    print(f"  - Offers with value_index > 5: {sum(1 for v in value_indices if v > 5)}")

# Show offers with missing critical data
print(f"\nOffers with Missing Critical Data:")
critical_missing = [o for o in offers if not o.get("offer_value") or not o.get("required_stake")]
if critical_missing:
    print(f"  Found {len(critical_missing)} offers missing offer_value or required_stake")
    for i, offer in enumerate(critical_missing[:5], 1):
        print(f"    {i}. {offer.get('bookmaker', 'Unknown')} - Missing: ", end="")
        missing = []
        if not offer.get("offer_value"): missing.append("offer_value")
        if not offer.get("required_stake"): missing.append("required_stake")
        print(", ".join(missing))
else:
    print("  [OK] All offers have critical data (offer_value and required_stake)")

print("\n" + "=" * 60)







