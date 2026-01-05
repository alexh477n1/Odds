"""Quick test to check The-Odds-API quota/rate limits."""
import asyncio
import httpx
from backend.config import Config


async def test_odds_api_quota():
    """Test the odds API to check remaining requests."""
    api_key = Config.THE_ODDS_API_KEY
    base_url = Config.THE_ODDS_API_URL
    
    # Make a minimal request to check quota
    # Using the sports endpoint as it's lightweight
    url = f"{base_url}/sports"
    params = {"apiKey": api_key}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"Testing The-Odds-API quota...")
            print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
            print(f"URL: {url}")
            print()
            
            response = await client.get(url, params=params)
            
            # Check rate limit headers
            requests_remaining = response.headers.get("x-requests-remaining")
            requests_used = response.headers.get("x-requests-used")
            
            print("=" * 50)
            print("API QUOTA STATUS:")
            print("=" * 50)
            
            if requests_remaining is not None:
                remaining = int(requests_remaining)
                used = int(requests_used) if requests_used else 0
                
                print(f"Requests Remaining: {remaining}")
                print(f"Requests Used: {used}")
                
                if remaining == 0:
                    print("\n[!] WARNING: You're OUT OF REQUESTS!")
                    print("   You've hit your API quota limit.")
                elif remaining < 10:
                    print(f"\n[!] WARNING: Only {remaining} requests remaining!")
                    print("   You're running low on API quota.")
                else:
                    print(f"\n[OK] You have {remaining} requests remaining.")
            else:
                print("[!] Rate limit headers not found in response")
                print(f"   Status Code: {response.status_code}")
            
            print("=" * 50)
            
            # Also check if the request was successful
            if response.status_code == 200:
                print("\n[OK] API is responding successfully")
            elif response.status_code == 401:
                print("\n[ERROR] Authentication failed - check your API key")
            elif response.status_code == 429:
                print("\n[ERROR] Rate limit exceeded - you're out of requests!")
            else:
                print(f"\n[!] Unexpected status code: {response.status_code}")
            
            # Print response headers for debugging
            print("\nResponse Headers:")
            for key, value in response.headers.items():
                if 'x-requests' in key.lower() or 'x-ratelimit' in key.lower():
                    print(f"  {key}: {value}")
                    
        except httpx.HTTPStatusError as e:
            print(f"\n[ERROR] HTTP Error: {e}")
            print(f"   Status Code: {e.response.status_code}")
            if e.response.status_code == 429:
                print("   This means you're out of requests!")
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_odds_api_quota())

