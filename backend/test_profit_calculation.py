"""Test script to verify LLM profit calculation and sorting."""
import asyncio
import sys
from backend.services.offers_catalog import get_offers_catalog, update_offers_from_scraper
from backend.utils.offers_calculator import calculate_expected_profit_with_llm
from backend.models.offers_catalog import OfferCatalog, OfferType, OfferDifficulty
from datetime import datetime

async def test():
    print("=" * 60)
    print("TESTING PROFIT CALCULATION AND SORTING")
    print("=" * 60)
    
    # Test 1: Check current offers
    print("\n1. Checking current offers in catalog...")
    result = await get_offers_catalog(limit=10)
    print(f"Found {len(result.offers)} offers")
    print("\nFirst 10 bookmakers:")
    for i, offer in enumerate(result.offers[:10], 1):
        is_mainstream = offer.bookmaker.lower() in ["bet365", "betfair", "sky bet", "paddy power", "william hill", "betway", "coral", "ladbrokes", "betvictor", "unibet"]
        print(f"  {i}. {offer.bookmaker} - Profit: £{offer.expected_profit or 'N/A'} - Mainstream: {is_mainstream}")
    
    # Test 2: Test LLM calculation on a sample offer
    print("\n2. Testing LLM profit calculation...")
    if result.offers:
        test_offer = result.offers[0]
        print(f"Testing with: {test_offer.bookmaker} - {test_offer.offer_name}")
        print(f"  Offer Value: £{test_offer.offer_value}")
        print(f"  Required Stake: £{test_offer.required_stake}")
        print(f"  Current Profit: £{test_offer.expected_profit}")
        print(f"  Terms: {test_offer.terms_summary[:100] if test_offer.terms_summary else 'None'}...")
        
        llm_profit = calculate_expected_profit_with_llm(test_offer)
        if llm_profit:
            print(f"  ✓ LLM Calculated Profit: £{llm_profit}")
        else:
            print(f"  ✗ LLM calculation failed")
    
    print("\n" + "=" * 60)
    print("To fix profits, run: python -m backend.scraper.oddschecker_scraper")
    print("Or trigger scrape via API: POST /v3/offers/catalog/scrape")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test())





