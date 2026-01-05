"""Betting instruction generator utilities."""
from typing import List, Optional
import google.generativeai as genai
from backend.models.calculator import BetType
from backend.models.instruction import (
    InstructionStep,
    InstructionRequest,
    InstructionResponse,
    FullOfferInstructionRequest,
    FullOfferInstructionResponse,
)
from backend.models.offers_catalog import OfferCatalog
from backend.utils.calculator import (
    calculate_qualifying_bet,
    calculate_free_bet_snr,
)
from backend.config import Config


def get_outcome_name(request: InstructionRequest) -> str:
    """Get the display name for the outcome."""
    if request.outcome == "home":
        return request.home_team
    elif request.outcome == "away":
        return request.away_team
    else:
        return "Draw"


def generate_qualifying_instructions(request: InstructionRequest) -> InstructionResponse:
    """Generate instructions for a qualifying bet."""
    # Calculate the bet
    calc = calculate_qualifying_bet(
        request.back_odds,
        request.lay_odds,
        request.stake,
        request.commission,
    )
    
    outcome_name = get_outcome_name(request)
    match_name = f"{request.home_team} vs {request.away_team}"
    
    # Build steps
    steps = [
        InstructionStep(
            step_number=1,
            action="Place BACK bet",
            platform=request.bookmaker,
            details=f"Bet {calc.stake:.2f} on {outcome_name} to win @ {request.back_odds}",
            warning=f"Make sure odds are at least {request.min_odds_required}" if request.min_odds_required else None,
        ),
        InstructionStep(
            step_number=2,
            action="Place LAY bet",
            platform=request.exchange,
            details=f"Lay {outcome_name} for {calc.lay_stake:.2f} @ {request.lay_odds}",
            warning=f"Your liability will be {calc.liability:.2f}",
        ),
        InstructionStep(
            step_number=3,
            action="Confirm both bets are matched",
            platform="Both",
            details="Check that both bets show as 'matched' or 'placed'",
            warning=None,
        ),
    ]
    
    # Build warnings
    warnings = []
    if request.min_odds_required and request.back_odds < request.min_odds_required:
        warnings.append(f"WARNING: Back odds {request.back_odds} are below minimum required {request.min_odds_required}!")
    if calc.spread_percent > 3:
        warnings.append(f"Spread is {calc.spread_percent}% - consider finding tighter odds")
    
    # Build tips
    tips = [
        "Place the back bet first, then immediately place the lay bet",
        "If odds move significantly, recalculate before placing the lay bet",
        f"You need {calc.liability:.2f} available in your {request.exchange} account",
    ]
    
    # Result description
    result_desc = f"Qualifying loss of {abs(calc.guaranteed_profit):.2f}" if calc.guaranteed_profit < 0 else f"Profit of {calc.guaranteed_profit:.2f}"
    
    # Plain text version
    plain_text = f"""
QUALIFYING BET INSTRUCTIONS
===========================
Match: {match_name}
Offer: {request.offer_name or 'N/A'}

STEP 1: Go to {request.bookmaker}
   -> Place a {calc.stake:.2f} BACK bet on {outcome_name} @ {request.back_odds}

STEP 2: Go to {request.exchange}
   -> LAY {outcome_name} for {calc.lay_stake:.2f} @ {request.lay_odds}
   -> Liability: {calc.liability:.2f}

STEP 3: Confirm both bets are matched

EXPECTED RESULT: {result_desc}
""".strip()
    
    return InstructionResponse(
        title=f"Qualifying Bet: {match_name}",
        summary=f"Back {outcome_name} @ {request.bookmaker}, Lay @ {request.exchange}",
        steps=steps,
        lay_stake=calc.lay_stake,
        liability=calc.liability,
        expected_result=calc.guaranteed_profit,
        result_description=result_desc,
        warnings=warnings,
        tips=tips,
        plain_text=plain_text,
    )


def generate_free_bet_instructions(request: InstructionRequest) -> InstructionResponse:
    """Generate instructions for a free bet (SNR)."""
    # Calculate the bet
    calc = calculate_free_bet_snr(
        request.back_odds,
        request.lay_odds,
        request.stake,
        request.commission,
    )
    
    outcome_name = get_outcome_name(request)
    match_name = f"{request.home_team} vs {request.away_team}"
    
    # Build steps
    steps = [
        InstructionStep(
            step_number=1,
            action="Use FREE BET",
            platform=request.bookmaker,
            details=f"Place your {calc.stake:.2f} FREE BET on {outcome_name} @ {request.back_odds}",
            warning="Select 'Use Free Bet' - do NOT use real money!",
        ),
        InstructionStep(
            step_number=2,
            action="Place LAY bet",
            platform=request.exchange,
            details=f"Lay {outcome_name} for {calc.lay_stake:.2f} @ {request.lay_odds}",
            warning=f"Your liability will be {calc.liability:.2f}",
        ),
        InstructionStep(
            step_number=3,
            action="Confirm both bets are matched",
            platform="Both",
            details="Check that both bets show as 'matched' or 'placed'",
            warning=None,
        ),
        InstructionStep(
            step_number=4,
            action="Wait for result",
            platform="N/A",
            details=f"You'll profit {calc.guaranteed_profit:.2f} regardless of outcome!",
            warning=None,
        ),
    ]
    
    # Build warnings
    warnings = [
        "Make sure you select FREE BET, not real money!",
        "Free bets are usually Stake Not Returned (SNR)",
    ]
    if request.min_odds_required and request.back_odds < request.min_odds_required:
        warnings.append(f"WARNING: Back odds {request.back_odds} are below minimum required {request.min_odds_required}!")
    
    # Build tips
    tips = [
        "Free bets often have expiry dates - use before they expire",
        f"You need {calc.liability:.2f} available in your {request.exchange} account",
        "Lay stake is lower than qualifying bet because you only cover the profit portion",
    ]
    
    # Result description
    result_desc = f"Guaranteed profit of {calc.guaranteed_profit:.2f}"
    
    # Plain text version
    plain_text = f"""
FREE BET INSTRUCTIONS
=====================
Match: {match_name}
Free Bet Value: {calc.stake:.2f}

STEP 1: Go to {request.bookmaker}
   -> Use your {calc.stake:.2f} FREE BET on {outcome_name} @ {request.back_odds}
   -> IMPORTANT: Select 'Free Bet', NOT real money!

STEP 2: Go to {request.exchange}
   -> LAY {outcome_name} for {calc.lay_stake:.2f} @ {request.lay_odds}
   -> Liability: {calc.liability:.2f}

STEP 3: Confirm both bets are matched

STEP 4: Wait for result

GUARANTEED PROFIT: {calc.guaranteed_profit:.2f}
""".strip()
    
    return InstructionResponse(
        title=f"Free Bet: {match_name}",
        summary=f"Use {calc.stake:.2f} free bet on {outcome_name} @ {request.bookmaker}, Lay @ {request.exchange}",
        steps=steps,
        lay_stake=calc.lay_stake,
        liability=calc.liability,
        expected_result=calc.guaranteed_profit,
        result_description=result_desc,
        warnings=warnings,
        tips=tips,
        plain_text=plain_text,
    )


def generate_instructions(request: InstructionRequest) -> InstructionResponse:
    """Generate instructions based on bet type."""
    if request.bet_type == BetType.QUALIFYING:
        return generate_qualifying_instructions(request)
    elif request.bet_type in (BetType.FREE_BET_SNR, BetType.FREE_BET_SR):
        return generate_free_bet_instructions(request)
    else:
        raise ValueError(f"Unknown bet type: {request.bet_type}")


def generate_full_offer_instructions(request: FullOfferInstructionRequest) -> FullOfferInstructionResponse:
    """Generate complete instructions for an offer (qualifying + free bet)."""
    
    # Part 1: Qualifying bet
    qual_request = InstructionRequest(
        home_team=request.home_team,
        away_team=request.away_team,
        outcome=request.outcome,
        back_odds=request.back_odds,
        lay_odds=request.lay_odds,
        bookmaker=request.bookmaker,
        exchange=request.exchange,
        stake=request.qualifying_stake,
        bet_type=BetType.QUALIFYING,
        commission=request.commission,
        offer_name=request.offer_name,
        min_odds_required=request.min_odds_required,
    )
    qual_instructions = generate_qualifying_instructions(qual_request)
    
    # Part 2: Free bet
    fb_request = InstructionRequest(
        home_team=request.home_team,
        away_team=request.away_team,
        outcome=request.outcome,
        back_odds=request.back_odds,
        lay_odds=request.lay_odds,
        bookmaker=request.bookmaker,
        exchange=request.exchange,
        stake=request.free_bet_value,
        bet_type=BetType.FREE_BET_SNR,
        commission=request.commission,
        offer_name=request.offer_name,
        min_odds_required=request.min_odds_required,
    )
    fb_instructions = generate_free_bet_instructions(fb_request)
    
    # Calculate totals
    total_qual_loss = qual_instructions.expected_result
    total_fb_profit = fb_instructions.expected_result
    total_profit = total_qual_loss + total_fb_profit
    
    # Profit summary
    if total_profit > 0:
        profit_summary = f"Total profit from this offer: {total_profit:.2f}"
    else:
        profit_summary = f"Total loss from this offer: {abs(total_profit):.2f}"
    
    # Full plain text
    match_name = f"{request.home_team} vs {request.away_team}"
    outcome_name = request.home_team if request.outcome == "home" else (request.away_team if request.outcome == "away" else "Draw")
    
    full_plain_text = f"""
{'=' * 60}
COMPLETE OFFER INSTRUCTIONS: {request.offer_name}
{'=' * 60}

Match: {match_name}
Betting on: {outcome_name}
Bookmaker: {request.bookmaker}
Exchange: {request.exchange}

{'=' * 60}
PART 1: QUALIFYING BET
{'=' * 60}

{qual_instructions.plain_text}

>>> After the qualifying bet settles, you'll receive your free bet <<<

{'=' * 60}
PART 2: FREE BET
{'=' * 60}

{fb_instructions.plain_text}

{'=' * 60}
PROFIT SUMMARY
{'=' * 60}

Qualifying bet loss:  {total_qual_loss:+.2f}
Free bet profit:      {total_fb_profit:+.2f}
--------------------------
TOTAL PROFIT:         {total_profit:+.2f}

Total exchange funds needed: {max(qual_instructions.liability, fb_instructions.liability):.2f}
(Liability is released after each bet settles)
""".strip()
    
    return FullOfferInstructionResponse(
        offer_name=request.offer_name,
        qualifying_instructions=qual_instructions,
        free_bet_instructions=fb_instructions,
        total_qualifying_loss=round(total_qual_loss, 2),
        total_free_bet_profit=round(total_fb_profit, 2),
        total_profit=round(total_profit, 2),
        profit_summary=profit_summary,
        full_plain_text=full_plain_text,
    )


def get_bet_characteristics(offer: OfferCatalog, match_info: Optional[dict] = None) -> str:
    """
    Generate characteristics of good matched betting bets using LLM.
    
    Args:
        offer: The offer catalog item
        match_info: Optional match information (teams, league, odds, etc.)
    
    Returns:
        Formatted text with bet characteristics and tips
    """
    try:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        
        # Build context
        offer_context = f"""
Offer: {offer.offer_name}
Bookmaker: {offer.bookmaker}
Free Bet Value: £{offer.offer_value or 'N/A'}
Required Stake: £{offer.required_stake or 'N/A'}
Minimum Odds: {offer.min_odds or 'Not specified'}
Stake Returned: {'Yes (SR)' if offer.is_stake_returned else 'No (SNR)'}
Terms: {offer.terms_summary or 'Not provided'}
"""
        
        match_context = ""
        if match_info:
            match_context = f"""
Match: {match_info.get('home_team', '')} vs {match_info.get('away_team', '')}
League: {match_info.get('league', '')}
Back Odds: {match_info.get('back_odds', '')}
Lay Odds: {match_info.get('lay_odds', '')}
Spread: {match_info.get('spread_percent', '')}%
"""
        
        prompt = f"""You are a matched betting expert. Provide characteristics of good matched betting bets for this offer.

OFFER DETAILS:
{offer_context}
{match_context if match_context else ''}

Provide a clear, concise guide on what makes a good matched betting bet for this specific offer. Include:

1. **Spread Requirements**: What spread percentage is ideal? (typically under 2%)
2. **Odds Range**: What odds range works best for this offer? (consider min_odds requirement)
3. **Liquidity Considerations**: How to check Betfair Exchange liquidity
4. **Match Selection**: What types of matches/leagues are best?
5. **Timing**: When is the best time to place bets?
6. **Risk Factors**: What to watch out for with this specific offer
7. **Optimization Tips**: How to maximize profit from this offer

Format as clear, numbered points. Be specific to this offer's terms and requirements."""

        generation_config = {
            "temperature": 0.3,
        }
        
        model = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            generation_config=generation_config
        )
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Error generating bet characteristics: {e}")
        # Return default characteristics
        return """CHARACTERISTICS OF GOOD MATCHED BETTING BETS

1. **Tight Spread**
   - Look for spreads under 2%
   - Lower spread = less qualifying loss / more free bet profit

2. **Good Liquidity**
   - Ensure Betfair Exchange has enough money available
   - Check available to lay before placing back bet

3. **Odds Stability**
   - Choose matches where odds are less likely to change
   - Avoid matches with volatile odds

4. **Match Rating**
   - Higher rated matches (7+) typically offer better value
   - Top leagues generally have better liquidity

5. **Commission Impact**
   - Remember Betfair charges 2% commission on winning lay bets
   - Factor this into all calculations

6. **Timing**
   - Place bets when markets are most liquid
   - Avoid placing bets too close to match start

7. **Risk Management**
   - Always place back bet first, then lay immediately
   - Have sufficient funds in exchange account for liability"""


