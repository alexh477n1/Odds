"""LLM-based parser for extracting structured data from raw offer text."""
import json
import time
from typing import Optional
import google.generativeai as genai
from backend.models.offer import OfferParsed
from backend.config import Config


# Initialize Gemini client
_client_initialized = False


def init_gemini_client():
    """Initialize Gemini client."""
    global _client_initialized
    if not _client_initialized:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        _client_initialized = True


def parse_offer_with_llm(raw_text: str, bookmaker_hint: Optional[str] = None) -> Optional[OfferParsed]:
    """
    Parse raw offer text using Google Gemini.
    
    Args:
        raw_text: Raw text content from the offer card
        bookmaker_hint: Optional hint about the bookmaker name
        
    Returns:
        OfferParsed object or None if parsing fails
    """
    init_gemini_client()
    
    # Enhance prompt with bookmaker hint if available
    prompt = _build_parsing_prompt(raw_text, bookmaker_hint)
    
    # Configure the model for JSON output
    generation_config = {
        "temperature": 0.1,  # Low temperature for consistent parsing
        "response_mime_type": "application/json",
    }
    
    model = genai.GenerativeModel(
        model_name=Config.GEMINI_MODEL,
        generation_config=generation_config
    )
    
    for attempt in range(Config.LLM_MAX_RETRIES):
        try:
            # Generate content
            response = model.generate_content(prompt)
            
            # Extract JSON from response
            content = response.text.strip()
            
            # Remove markdown code blocks if present (sometimes Gemini adds them)
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed_data = json.loads(content)
            
            # Handle case where Gemini returns a list instead of object
            if isinstance(parsed_data, list):
                if len(parsed_data) > 0:
                    parsed_data = parsed_data[0]  # Take first item
                else:
                    raise ValueError("Empty list returned from Gemini")
            
            # Ensure parsed_data is a dict
            if not isinstance(parsed_data, dict):
                raise ValueError(f"Expected dict, got {type(parsed_data)}")
            
            # Handle null/missing bookmaker before validation
            bookmaker_value = parsed_data.get("bookmaker")
            
            # Try to extract bookmaker from raw text if missing
            if not bookmaker_value or bookmaker_value is None or bookmaker_value.lower() == "unknown":
                # Try to extract from raw text pattern (e.g., "Betfair: Bet £10 Get £50")
                if ":" in raw_text[:200]:  # Check first 200 chars
                    potential_name = raw_text.split(":")[0].strip()
                    # Clean up common patterns
                    potential_name = potential_name.replace(" Logo", "").replace(" logo", "")
                    # Check if it looks like a bookmaker name
                    if len(potential_name) < 50 and len(potential_name) > 2:
                        # Check against common bookmaker patterns
                        if any(word in potential_name.lower() for word in ["bet", "sports", "casino"]) or len(potential_name.split()) <= 3:
                            bookmaker_value = potential_name
            
            # Use hint if still missing
            if not bookmaker_value or bookmaker_value is None or bookmaker_value.lower() == "unknown":
                if bookmaker_hint:
                    bookmaker_value = bookmaker_hint
                else:
                    bookmaker_value = "Unknown"
            
            parsed_data["bookmaker"] = bookmaker_value
            
            # Validate and create OfferParsed object
            try:
                offer = OfferParsed(**parsed_data)
            except Exception as e:
                # If validation fails, try to fix common issues
                if "bookmaker" in str(e):
                    parsed_data["bookmaker"] = bookmaker_hint or "Unknown"
                    offer = OfferParsed(**parsed_data)
                else:
                    raise
            
            # Post-process: use bookmaker hint if bookmaker is still unclear
            if bookmaker_hint and (offer.bookmaker.lower() == "unknown" or not offer.bookmaker):
                offer.bookmaker = bookmaker_hint
            
            return offer
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error (attempt {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}")
            if attempt < Config.LLM_MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            return None
            
        except Exception as e:
            print(f"API error (attempt {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}")
            if attempt < Config.LLM_MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            return None
    
    return None


def _build_parsing_prompt(raw_text: str, bookmaker_hint: Optional[str] = None) -> str:
    """Build the LLM prompt for parsing offers."""
    hint_section = ""
    if bookmaker_hint:
        hint_section = f"\n\nNote: The bookmaker name might be: {bookmaker_hint}"
    
    # Common bookmaker names to help the LLM
    common_bookmakers = "Betfair, Sky Bet, bet365, Bet365, Betfred, Paddy Power, William Hill, Ladbrokes, Coral, BetVictor, Unibet, Betway, BetMGM, 10bet, BOYLE Sports, Bresbet, BetTOM, CopyBet, Dabble, FanTeam, Hot Streak, Kwiff, LiveScore Bet, Matchbook, Midnite, NetBet, Parimatch, Priced Up, QuinnBet, SBK, Smarkets, Spreadex, Stakemake, talkSPORT BET, Tote, Virgin Bet"
    
    prompt = f"""You are parsing a free bet offer from Oddschecker. Extract the following information from this text:

{raw_text}
{hint_section}

Return ONLY a valid JSON object with these exact fields:
- bookmaker: string (REQUIRED - name of the bookmaker. Look for it in the first line or heading. Common names: {common_bookmakers}. If you see a pattern like "BookmakerName: Bet £10 Get £50", extract "BookmakerName". NEVER use null - use "Unknown" only if absolutely impossible to determine)
- offer_value: float (total monetary value of free bets, e.g., 50.0 for £50 in free bets)
- required_stake: float (amount user must stake to qualify, e.g., 10.0 for £10)
- min_odds: float (minimum odds required, convert fractions to decimal: 1/2 = 1.5, EVS = 2.0, 1/1 = 2.0)
- expiry_days: integer (days until expiry, null if not specified or if "valid for X days" mentioned)
- bet_type: string (one of: "SNR" for Stake Not Returned, "Qualifying" for qualifying bet offers, "Free Bet" for standard free bets, "Enhanced" for enhanced odds offers, "Casino" for casino bonuses, or "Unknown")

Important parsing rules:
- If offer says "Bet £10 Get £50", offer_value is 50.0, required_stake is 10.0
- If offer says "Bet 5p Get £40", offer_value is 40.0, required_stake is 0.05
- If multiple free bets mentioned (e.g., "4 x £10"), sum them: offer_value = 40.0
- Convert fractional odds: 1/2 = 1.5, EVS = 2.0, 1/1 = 2.0, 2/1 = 3.0
- Look for expiry mentions: "valid for 7 days" = expiry_days: 7, "expires after 30 days" = expiry_days: 30
- If bet_type is unclear, infer from context (SNR if "stake not returned" mentioned)
- If offer_value or required_stake cannot be determined, use null
- If min_odds cannot be determined, use null
- ALWAYS provide a bookmaker name - this field is REQUIRED and cannot be null
- If bookmaker name is unclear, use the hint provided or extract from the text
- If you cannot find the bookmaker name, use "Unknown" (never use null for bookmaker)

If any field cannot be determined (except bookmaker), use null. Be precise with numbers."""
    
    return prompt

