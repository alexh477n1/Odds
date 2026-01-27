"""
Oddschecker Free Bets Scraper
Scrapes welcome offers from https://www.oddschecker.com/free-bets
Uses Playwright to handle JavaScript rendering and bypass bot protection.
"""
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import asyncio
from urllib.parse import unquote, parse_qs
from scraper.parser import parse_offer_with_llm
from models.offer import OfferRaw


async def scrape_oddschecker_offers() -> List[Dict]:
    """
    Scrape free bet offers from Oddschecker using a real browser.
    Returns a list of offer dictionaries with all parsed information.
    """
    url = "https://www.oddschecker.com/free-bets"
    offers = []
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        
        # Create a context with realistic settings
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            locale="en-GB",
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to the page
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            
            # Wait for content to load
            print("Waiting for page content...")
            await page.wait_for_timeout(5000)
            
            # Wait for offer elements to load
            try:
                await page.wait_for_selector('[data-testid="offer-details"]', timeout=30000)
            except:
                pass
            
            # Accept cookies if popup appears
            print("Checking for cookie popup...")
            try:
                selectors = [
                    "button:has-text('Accept')",
                    "button:has-text('I Accept')",
                    "#onetrust-accept-btn-handler",
                    "button[id*='accept']",
                    "button[class*='accept']",
                ]
                for selector in selectors:
                    try:
                        cookie_btn = page.locator(selector)
                        if await cookie_btn.count() > 0:
                            await cookie_btn.first.click()
                            print("Cookie popup accepted")
                            await page.wait_for_timeout(2000)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"Cookie handling: {e}")
            
            # Scroll down to trigger lazy loading
            print("Scrolling page to load content...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            
            # Get page content
            print("Extracting page content...")
            html = await page.content()
            print(f"Page HTML length: {len(html)} characters")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all offer detail containers
            print("Searching for offer cards...")
            offer_details = soup.find_all("div", {"data-testid": "offer-details"})
            print(f"Found {len(offer_details)} offer detail containers")
            
            # Process each offer
            for offer_detail in offer_details:
                try:
                    offer = parse_offer_card(offer_detail, soup)
                    if offer and offer.get("bookmaker"):
                        offers.append(offer)
                        url_preview = offer.get('signup_url', 'No URL')
                        if url_preview != 'No URL' and url_preview:
                            url_preview = url_preview[:60] + "..." if len(url_preview) > 60 else url_preview
                        print(f"  [OK] Found offer: {offer.get('bookmaker')} - {offer.get('offer_name', 'N/A')[:50]} - {url_preview}")
                except Exception as e:
                    print(f"  [ERROR] Error parsing offer: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
        except Exception as e:
            print(f"Error scraping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
            print("Browser closed")
    
    # Deduplicate by bookmaker + offer name
    seen = set()
    unique_offers = []
    for offer in offers:
        key = (offer.get("bookmaker", "").lower(), offer.get("offer_name", "").lower())
        if key not in seen and offer.get("bookmaker"):
            seen.add(key)
            unique_offers.append(offer)
    
    print(f"\nTotal unique offers found: {len(unique_offers)}")
    return unique_offers


def _build_raw_text(offer: Dict) -> str:
    """Build a consistent raw text payload for LLM parsing."""
    parts = []
    bookmaker = offer.get("bookmaker")
    offer_name = offer.get("offer_name")
    terms = offer.get("terms_summary")
    signup_url = offer.get("signup_url")
    required_stake = offer.get("required_stake")
    offer_value = offer.get("offer_value")
    min_odds = offer.get("min_odds")

    if bookmaker:
        parts.append(f"Bookmaker: {bookmaker}")
    if offer_name:
        parts.append(f"Offer: {offer_name}")
    if terms:
        parts.append(f"Terms: {terms}")
    if required_stake is not None:
        parts.append(f"Required stake: £{required_stake}")
    if offer_value is not None:
        parts.append(f"Offer value: £{offer_value}")
    if min_odds is not None:
        parts.append(f"Minimum odds: {min_odds}")
    if signup_url:
        parts.append(f"Signup URL: {signup_url}")

    return "\n".join(parts).strip()


def scrape_offers() -> List[OfferRaw]:
    """
    Synchronous wrapper for Oddschecker scraping.
    Returns OfferRaw objects for downstream parsing.
    """
    offers = asyncio.run(scrape_oddschecker_offers())
    raw_offers: List[OfferRaw] = []
    for offer in offers:
        raw_text = _build_raw_text(offer)
        if raw_text:
            raw_offers.append(
                OfferRaw(raw_text=raw_text, bookmaker_hint=offer.get("bookmaker"))
            )
    return raw_offers


def extract_bookmaker_name_from_logo(offer_detail, soup) -> Optional[str]:
    """Extract bookmaker name from logo image alt text."""
    # Find the bookmaker logo container - it's usually a sibling or nearby
    # Look for the bookie details container
    bookie_details = soup.find("div", {"data-testid": "offer-bookie-details"})
    if bookie_details:
        logo_img = bookie_details.find("img", alt=re.compile(r"logo", re.I))
        if logo_img:
            alt_text = logo_img.get("alt", "")
            # Extract bookmaker name from alt (e.g., "Betfair Logo" -> "Betfair")
            if "logo" in alt_text.lower():
                bookmaker = alt_text.replace(" Logo", "").replace(" logo", "").strip()
                return bookmaker
    
    # Try to find logo near the offer detail
    parent = offer_detail.parent
    for _ in range(5):  # Go up 5 levels
        if parent:
            logo_img = parent.find("img", alt=re.compile(r"logo", re.I))
            if logo_img:
                alt_text = logo_img.get("alt", "")
                if "logo" in alt_text.lower():
                    bookmaker = alt_text.replace(" Logo", "").replace(" logo", "").strip()
                    return bookmaker
            parent = parent.parent if hasattr(parent, 'parent') else None
    
    return None


def parse_offer_card(offer_detail, soup) -> Optional[Dict]:
    """Parse a single offer card element using the new structure."""
    offer = {
        "bookmaker": None,
        "offer_name": None,
        "signup_url": None,
        "terms_summary": None,
        "offer_value": None,
        "required_stake": None,
        "min_odds": None,
    }
    
    # Extract offer title/name
    title_elem = offer_detail.find("a", {"data-testid": "offer-title"})
    if title_elem:
        offer["offer_name"] = title_elem.get_text(strip=True)
        # Extract signup URL from title link
        href = title_elem.get("href", "")
        if href:
            offer["signup_url"] = href if href.startswith("http") else f"https://www.oddschecker.com{href}"
    
    # Also check claim-now link
    claim_elem = offer_detail.find("a", {"data-testid": "claim-now"})
    if claim_elem and not offer["signup_url"]:
        href = claim_elem.get("href", "")
        if href:
            offer["signup_url"] = href if href.startswith("http") else f"https://www.oddschecker.com{href}"
    
    # FIRST: Extract bookmaker from offer_name format "Bookmaker: Offer Details"
    if offer["offer_name"] and ":" in offer["offer_name"]:
        bookmaker_part = offer["offer_name"].split(":")[0].strip()
        # Clean up common suffixes and fix common misparsings
        bookmaker_part = re.sub(r'\s+(Logo|logo)$', '', bookmaker_part)
        # Fix common misparsings
        bookmaker_part = bookmaker_part.replace("betwright", "Betway").replace("BetWright", "Betway")
        bookmaker_part = bookmaker_part.replace("ak bets", "AK Bets").replace("AK bets", "AK Bets")
        offer["bookmaker"] = bookmaker_part
        # Remove bookmaker from offer_name for cleaner parsing
        offer_text = ":".join(offer["offer_name"].split(":")[1:]).strip()
    else:
        offer_text = offer["offer_name"] or ""
        # Try logo extraction as fallback
        bookmaker_from_logo = extract_bookmaker_name_from_logo(offer_detail, soup)
        # Fix common misparsings
        if bookmaker_from_logo:
            bookmaker_from_logo = bookmaker_from_logo.replace("betwright", "Betway").replace("BetWright", "Betway")
            bookmaker_from_logo = bookmaker_from_logo.replace("ak bets", "AK Bets").replace("AK bets", "AK Bets")
        offer["bookmaker"] = bookmaker_from_logo
    
    # Find the full offer card container to get detailed terms/description (the grey paragraph)
    card_container = offer_detail
    for _ in range(10):  # Go up to find the card container
        if card_container and card_container.parent:
            parent_class = str(card_container.parent.get("class", [])).lower()
            parent_id = str(card_container.parent.get("id", "")).lower()
            if any(x in parent_class for x in ["card", "offer", "row", "item"]) or "offer" in parent_id:
                card_container = card_container.parent
                break
            card_container = card_container.parent
        else:
            break
    
    # Extract detailed terms/description text from the card (the grey paragraph text)
    terms_texts = []
    
    # First, try to find the offer description paragraph (usually the longest text block)
    # Look for paragraphs that contain offer details
    all_paragraphs = card_container.find_all("p") if card_container else []
    for p in all_paragraphs:
        text = p.get_text(strip=True)
        # Filter out short text, navigation, buttons, etc.
        # Look for paragraphs that are detailed descriptions (usually 100+ chars, contain offer details)
        if (len(text) > 100 and 
            any(word in text.lower() for word in ["bet", "get", "free", "odds", "min", "stake", "deposit", "place", "customers", "t&c", "apply", "only"]) and
            "rating" not in text.lower() and
            "review" not in text.lower() and
            "valid today" not in text.lower() and
            "get offer" not in text.lower() and
            "payout speed" not in text.lower()):
            terms_texts.append(text)
    
    # Also look in divs with description/terms classes
    detail_divs = card_container.find_all("div") if card_container else []
    for div in detail_divs:
        classes = " ".join(div.get("class", [])).lower()
        # Skip if it's clearly not a description div
        if any(skip in classes for skip in ["rating", "review", "button", "link", "header", "logo"]):
            continue
        text = div.get_text(strip=True)
        if (len(text) > 100 and 
            any(word in text.lower() for word in ["bet", "get", "free", "odds", "min", "stake", "place", "customers"]) and
            "rating" not in text.lower() and
            "review" not in text.lower() and
            "valid today" not in text.lower()):
            if text not in terms_texts:
                terms_texts.append(text)
    
    # If still no good terms, search siblings
    if not terms_texts and card_container and card_container.parent:
        siblings = card_container.parent.find_all(["p", "div"], limit=20)
        for sib in siblings:
            text = sib.get_text(strip=True)
            if (len(text) > 100 and 
                any(word in text.lower() for word in ["bet", "get", "free", "odds", "min", "place", "customers", "only"]) and
                "rating" not in text.lower() and
                "review" not in text.lower() and
                "valid today" not in text.lower()):
                if text not in terms_texts:
                    terms_texts.append(text)
    
    # Combine all terms text
    full_terms_text = " ".join(terms_texts)
    if full_terms_text:
        offer["terms_summary"] = full_terms_text[:500]  # Max 500 chars
    
    # Parse offer details from BOTH offer_text AND terms_text (terms are more accurate!)
    all_text = f"{offer_text} {full_terms_text}".strip()
    
    if all_text:
        # Extract offer value - check terms FIRST (more accurate), then title
        # Patterns: "get £50", "4 X £10 bet tokens" = 40, "£50 in Free Bets", "up to £40"
        value_patterns = [
            r"(\d+)\s*x\s*£(\d+)\s*(?:bet|free|token)",  # "4 X £10 bet tokens" = 40
            r"(\d+)\s*×\s*£(\d+)",  # "4 × £10" (different × symbol)
            r"get\s*£?(\d+)\s*(?:in|free|bet)",  # "get £50 in Free Bets"
            r"£(\d+)\s*(?:in|of)\s*(?:free bets|bet tokens|bet credits)",  # "£50 in Free Bets"
            r"(?:receive|win|up to)\s*£?(\d+)",  # "receive £40", "up to £50"
            r"(\d+)%\s*(?:back|bonus|match)",  # "50% back" - calculate from stake
        ]
        
        total_value = None
        for pattern in value_patterns:
            matches = re.findall(pattern, all_text, re.I)
            if matches:
                if isinstance(matches[0], tuple) and len(matches[0]) == 2:  # "4 X £10" case
                    multiplier, amount = matches[0]
                    total_value = float(multiplier) * float(amount)
                    break
                elif pattern == r"(\d+)%\s*(?:back|bonus|match)":  # Percentage case
                    # Will calculate later if we have stake
                    pass
                else:
                    # Take the first/largest value found
                    values = [float(m[0] if isinstance(m, tuple) else m) for m in matches]
                    total_value = max(values) if values else None
                    if total_value:
                        break
        
        if total_value:
            offer["offer_value"] = total_value
        
        # Extract required stake - prioritize terms text, be careful not to match bookmaker names
        # "Place a min £10 bet", "Bet 5p & Get", "min deposit requirement", "when you bet £10"
        stake_patterns = [
            r"place\s+a\s+min\s+£?(\d+(?:\.\d+)?)\s*(?:p|pence)?\s+bet",  # "Place a min £10 bet" (from terms)
            r"min\s+£?(\d+(?:\.\d+)?)\s*(?:p|pence)?\s+bet",  # "min £10 bet"
            r"bet\s+£?(\d+(?:\.\d+)?)\s*(?:p|pence)?\s*(?:&|and|get)",  # "Bet 5p & Get" or "Bet £10 Get"
            r"bet\s+(\d+)\s*p\s*(?:&|and)",  # "Bet 5p &"
            r"when\s+you\s+bet\s+£?(\d+(?:\.\d+)?)\s*(?:p|pence)?",
            r"stake\s+£?(\d+(?:\.\d+)?)\s*(?:p|pence)?",
            r"min\s+deposit\s+£?(\d+(?:\.\d+)?)",
            r"deposit\s+£?(\d+(?:\.\d+)?)",
        ]
        
        for pattern in stake_patterns:
            stake_match = re.search(pattern, all_text, re.I)  # Search in all_text, not just offer_text
            if stake_match:
                stake_value = float(stake_match.group(1))
                # Convert pence to pounds - check context around the match
                match_text = stake_match.group(0).lower()
                if ("p" in match_text or "pence" in match_text) and stake_value < 10:
                    stake_value = stake_value / 100
                # Validate stake is reasonable (0.01 to 1000)
                if 0.01 <= stake_value <= 1000:
                    offer["required_stake"] = stake_value
                    break
        
        # Calculate percentage-based offer_value if we have stake
        if not offer["offer_value"] and offer["required_stake"]:
            pct_match = re.search(r"(\d+)%\s*(?:back|bonus|match)", all_text, re.I)
            if pct_match:
                pct = float(pct_match.group(1)) / 100
                offer["offer_value"] = offer["required_stake"] * pct
        
        # Extract minimum odds from terms (more accurate than title)
        # Check for: "EVS (2.0)", "1/1", "odds of min EVS (2.0)", "odds of 1/1 or greater"
        odds_patterns = [
            r"EVS\s*\((\d+\.?\d*)\)",  # "EVS (2.0)"
            r"odds\s+of\s+min\s+EVS\s*\((\d+\.?\d*)\)",  # "odds of min EVS (2.0)"
            r"odds\s+of\s+(\d+)/(\d+)",  # "odds of 1/1" = 2.0
            r"(\d+)/(\d+)\s+or\s+greater",  # "1/1 or greater"
            r"min(?:imum)?\s+odds?\s+(?:of|at|are)?\s*(\d+\.?\d*)\s*\+",  # "min odds 1.50+"
            r"odds?\s+(\d+\.?\d*)\s*\+\s*(?:or|and|minimum)",  # "odds 1.50+ or"
            r"at\s+least\s+(\d+\.?\d*)\s*odds",  # "at least 2.0 odds"
            r"(\d+\.?\d*)\s*\+\s*odds",  # "1.50+ odds"
            r"odds\s+(\d+\.?\d*)\s*\+",  # "odds 1.50+"
        ]
        
        for pattern in odds_patterns:
            odds_match = re.search(pattern, all_text, re.I)
            if odds_match:
                if len(odds_match.groups()) == 2:  # Fractional like "1/1"
                    num, den = float(odds_match.group(1)), float(odds_match.group(2))
                    if den > 0:
                        offer["min_odds"] = (num / den) + 1.0
                else:
                    odds_val = float(odds_match.group(1))
                    # Only accept reasonable odds (1.01 to 100)
                    if 1.01 <= odds_val <= 100:
                        offer["min_odds"] = odds_val
                if offer["min_odds"]:
                    break
    
    # Try to extract from URL parameters (the name parameter often has full offer details)
    if offer["signup_url"] and not offer["bookmaker"]:
        try:
            if "clickout.htm" in offer["signup_url"]:
                parsed_url = parse_qs(offer["signup_url"].split("?")[1] if "?" in offer["signup_url"] else "")
                if "name" in parsed_url:
                    name_param = unquote(parsed_url["name"][0])
                    # Format: "Bookmaker: Bet £X Get £Y"
                    if ":" in name_param:
                        parts = name_param.split(":", 1)
                        if not offer["bookmaker"]:
                            offer["bookmaker"] = parts[0].strip()
                        # Use URL name as offer_name if we don't have one
                        if not offer["offer_name"]:
                            offer["offer_name"] = name_param
                        
                        # Parse from name parameter if we haven't extracted yet
                        name_text = parts[1] if len(parts) > 1 else name_param
                        if not offer["offer_value"]:
                            value_match = re.search(r"get\s*£?(\d+)", name_text, re.I)
                            if value_match:
                                offer["offer_value"] = float(value_match.group(1))
                        if not offer["required_stake"]:
                            # Be careful - don't match "bet365" as stake
                            stake_match = re.search(r"bet\s+£?(\d+(?:\.\d+)?)\s*(?!\d)", name_text, re.I)
                            if stake_match:
                                stake_val = float(stake_match.group(1))
                                # Convert pence
                                if "p" in name_text.lower() and stake_val < 10:
                                    stake_val = stake_val / 100
                                offer["required_stake"] = stake_val
        except Exception as e:
            print(f"Error parsing URL params: {e}")
    
    # Final validation - must have bookmaker
    if not offer["bookmaker"]:
        return None
    
    # If we're missing critical fields, try LLM parsing as fallback
    if not offer["offer_value"] or not offer["required_stake"]:
        try:
            # Combine all text we have
            llm_text = f"{offer['offer_name']}"
            if offer["terms_summary"]:
                llm_text += f" | {offer['terms_summary']}"
            
            # Use LLM to parse
            parsed = parse_offer_with_llm(llm_text, offer["bookmaker"])
            if parsed:
                # Fill in missing fields from LLM
                if not offer["offer_value"] and parsed.offer_value:
                    offer["offer_value"] = parsed.offer_value
                if not offer["required_stake"] and parsed.required_stake:
                    offer["required_stake"] = parsed.required_stake
                if not offer["min_odds"] and parsed.min_odds:
                    offer["min_odds"] = parsed.min_odds
                if not offer["terms_summary"] and parsed.bet_type:
                    offer["terms_summary"] = f"Type: {parsed.bet_type}"
        except Exception as e:
            # LLM parsing failed, continue with what we have
            pass
    
    return offer


async def test_scraper():
    """Test the scraper."""
    print("Scraping Oddschecker free bets with Playwright...")
    offers = await scrape_oddschecker_offers()
    print(f"\nFound {len(offers)} offers:\n")
    
    for i, offer in enumerate(offers[:10], 1):  # Show first 10
        print(f"{i}. {offer.get('bookmaker', 'Unknown')}")
        print(f"   Offer: {offer.get('offer_name', 'N/A')}")
        signup_url = offer.get('signup_url')
        if signup_url:
            url_preview = signup_url[:80] + "..." if len(signup_url) > 80 else signup_url
            print(f"   URL: {url_preview}")
        else:
            print(f"   URL: N/A")
        offer_value = offer.get('offer_value')
        if offer_value:
            print(f"   Value: £{offer_value}")
        required_stake = offer.get('required_stake')
        if required_stake:
            print(f"   Stake: £{required_stake}")
        min_odds = offer.get('min_odds')
        if min_odds:
            print(f"   Min Odds: {min_odds}")
        print()
    
    return offers


if __name__ == "__main__":
    asyncio.run(test_scraper())

