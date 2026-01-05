"""Utility functions for calculating expected profit from offers."""
import json
import time
import hashlib
from typing import Optional
import google.generativeai as genai
from backend.models.offers_catalog import OfferCatalog
from backend.utils.match_filtering import calculate_qualifying_loss, calculate_free_bet_profit
from backend.config import Config


def calculate_terms_hash(terms_summary: Optional[str]) -> str:
    """Calculate hash of terms summary to detect changes."""
    if not terms_summary:
        return ""
    return hashlib.md5(terms_summary.encode()).hexdigest()


def calculate_expected_profit_with_llm(offer: OfferCatalog) -> Optional[float]:
    """Calculate expected profit using LLM interpretation of offer terms."""
    # Skip if no offer value - can't calculate profit
    if not offer.offer_value or offer.offer_value <= 0:
        print(f"Skipping LLM calculation for {offer.bookmaker} - no offer_value")
        return None
        
    try:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        print(f"Calling LLM for {offer.bookmaker} - offer_value={offer.offer_value}, required_stake={offer.required_stake}")
        
        # Build comprehensive offer details like in instructions
        wagering = f"{offer.wagering_requirement}x" if offer.wagering_requirement else "1x (standard)"
        stake_returned = "Yes (SR)" if offer.is_stake_returned else "No (SNR)"
        
        offer_details = f"""
Bookmaker: {offer.bookmaker}
Offer Name: {offer.offer_name}
Offer Type: {offer.offer_type}
Free Bet Value: £{offer.offer_value if offer.offer_value else 'N/A'}
Required Stake: £{offer.required_stake if offer.required_stake else 'N/A'}
Minimum Odds: {offer.min_odds if offer.min_odds else 'Not specified'}
Wagering Requirement: {wagering}
Stake Returned: {stake_returned}
Terms Summary: {offer.terms_summary or 'Not provided'}
Raw Terms: {offer.terms_raw or 'Not provided'}
Eligible Sports: {', '.join(offer.eligible_sports) if offer.eligible_sports else 'All sports'}
Eligible Markets: {', '.join(offer.eligible_markets) if offer.eligible_markets else 'All markets'}
Expiry Days: {offer.expiry_days if offer.expiry_days else 'Not specified'}
"""
        
        prompt = f"""You are a matched betting expert. Calculate the ACTUAL expected profit for this offer by analyzing ALL the terms and conditions.

OFFER DETAILS:
{offer_details}

IMPORTANT CALCULATION REQUIREMENTS:

1. **Qualifying Bet Loss**: Calculate the cost to unlock the free bet(s)
   - Use standard matched betting: back odds ~2.0, lay odds ~2.02, commission 2%
   - Typical qualifying loss: £1-3 for standard £10 stakes
   - Formula: Lay stake = (back_stake × back_odds) / (lay_odds - commission)
   - Loss = back_stake - (lay_stake × (1 - commission)) when lay wins

2. **Free Bet Extraction**: Calculate the ACTUAL extractable value from free bets
   - NOT all free bets are fully extractable - discount based on terms
   - For SNR (Stake Not Returned) free bets: typically extract 70-80% of face value
   - For SR (Stake Returned) free bets: typically extract 90-95% of face value
   - Consider: multiple free bets, wagering requirements, expiry restrictions, odds restrictions
   - If terms say "3x £10 free bets", calculate extraction for EACH bet separately
   - If terms restrict markets/sports, discount further (e.g., 10-20% reduction)
   - If expiry is very short (<7 days), discount 5-10%

3. **Total Expected Profit**: Free bet profit - Qualifying loss
   - This is the REALISTIC profit after all discounts and costs

EXAMPLES:
- "Bet £10 Get £50 in free bets" (SNR, no restrictions): 
  Qualifying loss: ~£2, Free bet extraction: £50 × 0.75 = £37.50, Profit: £35.50
  
- "Bet 5p Get £40" (SNR, no restrictions):
  Qualifying loss: ~£0.01, Free bet extraction: £40 × 0.75 = £30, Profit: £29.99

- "Bet £10 Get 3x £10 free bets" (SNR, horse racing only):
  Qualifying loss: ~£2, Free bet extraction: (3 × £10) × 0.70 = £21 (discounted for market restriction), Profit: £19

Return ONLY a JSON object with this exact structure:
{{
  "expected_profit": <float>,
  "qualifying_loss": <float>,
  "free_bet_profit": <float>,
  "discount_applied": <float or null>,
  "reasoning": "<brief explanation of calculation>"
}}

Be precise and realistic. Do not overestimate free bet extraction."""

        generation_config = {
            "temperature": 0.1,
            "response_mime_type": "application/json",
        }
        
        model = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            generation_config=generation_config
        )
        
        for attempt in range(Config.LLM_MAX_RETRIES):
            try:
                response = model.generate_content(prompt)
                content = response.text.strip()
                
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                parsed_data = json.loads(content)
                
                # Handle case where Gemini returns a list
                if isinstance(parsed_data, list):
                    if len(parsed_data) > 0:
                        parsed_data = parsed_data[0]
                    else:
                        raise ValueError("Empty list returned from Gemini")
                
                if not isinstance(parsed_data, dict):
                    raise ValueError(f"Expected dict, got {type(parsed_data)}")
                
                expected_profit = parsed_data.get("expected_profit")
                if expected_profit is not None:
                    return float(expected_profit)
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error (attempt {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}")
                if attempt < Config.LLM_MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
                
            except Exception as e:
                print(f"LLM calculation error (attempt {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}")
                if attempt < Config.LLM_MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        
        return None
        
    except Exception as e:
        print(f"Error in LLM profit calculation: {e}")
        return None


def calculate_expected_profit_formula(
    offer_value: Optional[float],
    required_stake: Optional[float],
    min_odds: Optional[float],
    is_stake_returned: bool = False,
    commission: float = 0.02
) -> Optional[float]:
    """Calculate expected profit using formula-based approach (fallback)."""
    if not offer_value or not required_stake:
        return None
    
    # Use min_odds if provided, otherwise default to 2.0
    back_odds = min_odds if min_odds and min_odds >= 1.5 else 2.0
    lay_odds = back_odds + 0.02  # Typical spread
    
    # Calculate qualifying loss
    qual_loss = calculate_qualifying_loss(required_stake, back_odds, lay_odds, commission)
    
    # Calculate free bet profit
    fb_profit = calculate_free_bet_profit(offer_value, back_odds, lay_odds, commission, is_snr=not is_stake_returned)
    
    return round(fb_profit - abs(qual_loss), 2)


def calculate_expected_profit(
    offer: OfferCatalog,
    use_llm: bool = True,
    terms_hash: Optional[str] = None,
    existing_hash: Optional[str] = None
) -> Optional[float]:
    """
    Calculate expected profit for an offer.
    
    Args:
        offer: The offer catalog item
        use_llm: Whether to use LLM calculation (default True)
        terms_hash: Current hash of terms_summary
        existing_hash: Previous hash of terms_summary (to check if recalculation needed)
    
    Returns:
        Expected profit value or None if calculation fails
    """
    # If terms haven't changed and we have existing profit, return existing profit
    if terms_hash and existing_hash and terms_hash == existing_hash and offer.expected_profit is not None:
        return offer.expected_profit
    
    # If we have existing profit and terms haven't changed, keep it
    if not use_llm and offer.expected_profit is not None:
        return offer.expected_profit
    
    # Try LLM calculation if enabled
    if use_llm:
        llm_result = calculate_expected_profit_with_llm(offer)
        if llm_result is not None:
            return llm_result
    
    # Fallback to formula-based calculation only if no existing profit
    if offer.expected_profit is None:
        return calculate_expected_profit_formula(
            offer.offer_value,
            offer.required_stake,
            offer.min_odds,
            offer.is_stake_returned,
            commission=0.02  # Standard Betfair commission (2%)
        )
    
    # Return existing profit if available
    return offer.expected_profit

