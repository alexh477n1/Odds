"""
Test script to verify scraper integration with the database.
Run this after calling the scrape endpoint to verify URLs are stored.
"""
import asyncio
from backend.database.supabase_client import get_supabase_client

async def test_scraper_integration():
    """Check which offers have signup URLs after scraping."""
    supabase = get_supabase_client()
    
    # Get all offers with signup URLs
    result = supabase.table("offers_catalog")\
        .select("bookmaker, offer_name, signup_url")\
        .not_.is_("signup_url", "null")\
        .execute()
    
    offers_with_urls = result.data or []
    
    print("\n" + "="*70)
    print("OFFERS WITH SCRAPED SIGNUP URLS")
    print("="*70 + "\n")
    
    if not offers_with_urls:
        print("No offers with signup URLs found.")
        print("Run the scraper endpoint: POST /v3/offers/catalog/scrape")
    else:
        print(f"Found {len(offers_with_urls)} offers with signup URLs:\n")
        for i, offer in enumerate(offers_with_urls[:10], 1):  # Show first 10
            url = offer.get("signup_url", "")
            url_preview = url[:70] + "..." if len(url) > 70 else url
            print(f"{i}. {offer.get('bookmaker')}")
            print(f"   Offer: {offer.get('offer_name', 'N/A')}")
            print(f"   URL: {url_preview}")
            print()
        
        if len(offers_with_urls) > 10:
            print(f"... and {len(offers_with_urls) - 10} more\n")

if __name__ == "__main__":
    asyncio.run(test_scraper_integration())





