"""Generate detailed instructions for a specific offer using LLM."""
import json
import time
from typing import Optional
import google.generativeai as genai
from backend.config import Config
from backend.models.offers_catalog import OfferCatalog


_client_initialized = False


def init_gemini_client():
    """Initialize Gemini client."""
    global _client_initialized
    if not _client_initialized:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        _client_initialized = True


def generate_offer_instructions(offer: OfferCatalog) -> str:
    """
    Generate detailed step-by-step instructions for completing a specific offer.
    
    Returns a markdown-formatted string with comprehensive instructions.
    """
    init_gemini_client()
    
    prompt = _build_offer_instructions_prompt(offer)
    
    generation_config = {
        "temperature": 0.7,  # Slightly higher for more natural explanations
        "max_output_tokens": 2000,
    }
    
    model = genai.GenerativeModel(
        model_name=Config.GEMINI_MODEL,
        generation_config=generation_config
    )
    
    for attempt in range(Config.LLM_MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            instructions = response.text.strip()
            return instructions
        except Exception as e:
            print(f"LLM error (attempt {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}")
            if attempt < Config.LLM_MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return _get_fallback_instructions(offer)
    
    return _get_fallback_instructions(offer)


def _build_offer_instructions_prompt(offer: OfferCatalog) -> str:
    """Build the LLM prompt for generating offer instructions."""
    
    wagering = f"{offer.wagering_requirement}x" if offer.wagering_requirement else "1x (standard)"
    stake_returned = "Yes (SR)" if offer.is_stake_returned else "No (SNR)"
    
    offer_details = f"""
Bookmaker: {offer.bookmaker}
Offer: {offer.offer_name}
Offer Type: {offer.offer_type}
Free Bet Value: £{offer.offer_value if offer.offer_value else 'N/A'}
Required Stake: £{offer.required_stake if offer.required_stake else 'N/A'}
Minimum Odds: {offer.min_odds if offer.min_odds else 'Not specified'}
Wagering Requirement: {wagering}
Stake Returned: {stake_returned}
Terms: {offer.terms_summary or 'See offer details'}
Difficulty: {offer.difficulty or 'Easy'}
"""
    
    prompt = f"""You are a matched betting expert helping someone complete this bookmaker offer. Generate clear, step-by-step instructions.

OFFER DETAILS:
{offer_details}

Generate comprehensive instructions that explain:
1. What this offer is and how it works
2. Step-by-step process to complete it:
   - How to sign up (if welcome offer)
   - How to place the qualifying bet
   - How to find a good match using MatchCaddy
   - How to extract the free bet value
   - What to expect at each stage
3. Important tips and warnings specific to this offer
4. Expected profit/loss breakdown
5. Common mistakes to avoid

Write in a friendly, clear tone. Use numbered steps. Include specific amounts and odds where relevant.
Format as markdown with clear headings and bullet points.

Keep it practical and actionable - someone should be able to follow these instructions step-by-step."""
    
    return prompt


def _get_fallback_instructions(offer: OfferCatalog) -> str:
    """Fallback instructions if LLM fails."""
    return f"""# How to Complete: {offer.offer_name}

## Overview
This is a {offer.offer_type} offer from {offer.bookmaker}.

## Steps

1. **Sign Up**: Create an account at {offer.bookmaker}
   - Use the signup link provided
   - Complete registration

2. **Place Qualifying Bet**
   - Stake: £{offer.required_stake or '10'}
   - Minimum odds: {offer.min_odds or '1.50'}
   - Use MatchCaddy to find a good match
   - Place back bet at bookmaker
   - Place lay bet at exchange (Betfair)

3. **Wait for Settlement**
   - After match finishes, qualifying bet settles
   - Free bet will be credited to your account

4. **Extract Free Bet**
   - Use MatchCaddy calculator to find optimal odds
   - Place free bet at bookmaker
   - Lay the same bet at exchange
   - Extract {offer.offer_value or 'the'} free bet value

## Expected Profit
Approximately £{offer.expected_profit or '10-15'} after accounting for qualifying bet loss.

## Tips
- Always check minimum odds requirements
- Use MatchCaddy to find tight odds matches
- Keep exchange funds available for liability"""
