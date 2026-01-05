"""Check current sorting and bookmaker names."""
import asyncio
from backend.services.offers_catalog import get_offers_catalog

async def check():
    result = await get_offers_catalog(limit=30)
    
    print("=" * 60)
    print("CURRENT OFFERS IN CATALOG (First 30)")
    print("=" * 60)
    
    MAINSTREAM = ["bet365", "betfair", "sky bet", "paddy power", "william hill", "betway", "coral", "ladbrokes", "betvictor", "unibet"]
    
    for i, offer in enumerate(result.offers[:30], 1):
        bm_lower = offer.bookmaker.lower() if offer.bookmaker else ""
        is_mainstream = any(m in bm_lower or bm_lower in m for m in MAINSTREAM)
        has_profit = offer.expected_profit is not None and offer.expected_profit > 0
        has_value = offer.offer_value is not None and offer.offer_value > 0
        
        status = []
        if is_mainstream:
            status.append("MAINSTREAM")
        if not has_profit:
            status.append("NO_PROFIT")
        if not has_value:
            status.append("NO_VALUE")
        
        print(f"{i:2}. {offer.bookmaker:20} | Profit: ${offer.expected_profit or 'N/A':>8} | Value: ${offer.offer_value or 'N/A':>6} | {' '.join(status)}")

if __name__ == "__main__":
    asyncio.run(check())





