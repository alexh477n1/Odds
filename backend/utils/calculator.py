"""Matched betting calculator utilities."""
from models.calculator import (
    BetType, 
    CalcRequest, 
    CalcResponse, 
    OutcomeResult,
    BatchCalcRequest,
    BatchCalcResponse,
)


def calculate_spread(back_odds: float, lay_odds: float) -> float:
    """Calculate spread percentage between back and lay odds."""
    return abs(lay_odds - back_odds) / back_odds * 100


def get_rating(spread: float, bet_type: BetType) -> str:
    """
    Get quality rating based on spread.
    
    For qualifying bets, tighter spreads are better (less loss).
    For free bets, we're more tolerant of spreads since we're profiting anyway.
    """
    if bet_type == BetType.QUALIFYING:
        if spread <= 1.0:
            return "Excellent"
        elif spread <= 2.0:
            return "Good"
        elif spread <= 3.5:
            return "Fair"
        else:
            return "Poor"
    else:  # Free bets
        if spread <= 2.0:
            return "Excellent"
        elif spread <= 4.0:
            return "Good"
        elif spread <= 6.0:
            return "Fair"
        else:
            return "Poor"


def calculate_qualifying_bet(
    back_odds: float,
    lay_odds: float,
    stake: float,
    commission: float,
) -> CalcResponse:
    """
    Calculate a qualifying bet (normal bet to unlock a free bet).
    
    Goal: Minimize loss while covering all outcomes.
    
    Formula for lay stake:
        lay_stake = (back_stake * back_odds) / (lay_odds - commission)
    
    This ensures roughly equal loss regardless of outcome.
    """
    # Calculate lay stake to balance outcomes
    lay_stake = (stake * back_odds) / (lay_odds - commission)
    liability = lay_stake * (lay_odds - 1)
    
    # If back bet wins (bookmaker pays out):
    # Profit = stake * (back_odds - 1) - liability
    back_wins_profit = stake * (back_odds - 1) - liability
    
    # If lay bet wins (you keep the lay stake minus commission):
    # Profit = lay_stake * (1 - commission) - stake
    lay_wins_profit = lay_stake * (1 - commission) - stake
    
    # The guaranteed profit is the minimum of both outcomes
    guaranteed = min(back_wins_profit, lay_wins_profit)
    
    # Expected value (average of outcomes, roughly 50/50)
    expected = (back_wins_profit + lay_wins_profit) / 2
    
    spread = calculate_spread(back_odds, lay_odds)
    rating = get_rating(spread, BetType.QUALIFYING)
    
    return CalcResponse(
        back_odds=back_odds,
        lay_odds=lay_odds,
        stake=stake,
        bet_type=BetType.QUALIFYING,
        commission=commission,
        lay_stake=round(lay_stake, 2),
        liability=round(liability, 2),
        outcomes=[
            OutcomeResult(
                outcome="back_wins",
                profit=round(back_wins_profit, 2),
                description=f"Bookmaker pays {stake * (back_odds - 1):.2f}, exchange takes {liability:.2f}",
            ),
            OutcomeResult(
                outcome="lay_wins",
                profit=round(lay_wins_profit, 2),
                description=f"Lose {stake:.2f} at bookmaker, keep {lay_stake * (1 - commission):.2f} from exchange",
            ),
        ],
        guaranteed_profit=round(guaranteed, 2),
        expected_value=round(expected, 2),
        rating=rating,
        spread_percent=round(spread, 2),
    )


def calculate_free_bet_snr(
    back_odds: float,
    lay_odds: float,
    stake: float,
    commission: float,
) -> CalcResponse:
    """
    Calculate a free bet with Stake Not Returned (most common free bet type).
    
    With SNR, if you win, you only get the profit portion (odds - 1) * stake.
    If you lose, you get nothing but you didn't risk real money.
    
    Strategy: Lay for (odds - 1) * stake to guarantee profit.
    
    Formula for lay stake:
        lay_stake = (free_bet * (back_odds - 1)) / (lay_odds - commission)
    """
    # Calculate lay stake based on potential winnings only (not stake)
    potential_winnings = stake * (back_odds - 1)
    lay_stake = potential_winnings / (lay_odds - commission)
    liability = lay_stake * (lay_odds - 1)
    
    # If back bet wins (free bet pays profit only):
    # Profit = stake * (back_odds - 1) - liability
    back_wins_profit = potential_winnings - liability
    
    # If lay bet wins (you keep lay stake minus commission):
    # Profit = lay_stake * (1 - commission)
    # Note: You don't lose the stake because it was a free bet!
    lay_wins_profit = lay_stake * (1 - commission)
    
    # The guaranteed profit is the minimum of both outcomes
    guaranteed = min(back_wins_profit, lay_wins_profit)
    
    # Expected value
    expected = (back_wins_profit + lay_wins_profit) / 2
    
    spread = calculate_spread(back_odds, lay_odds)
    rating = get_rating(spread, BetType.FREE_BET_SNR)
    
    return CalcResponse(
        back_odds=back_odds,
        lay_odds=lay_odds,
        stake=stake,
        bet_type=BetType.FREE_BET_SNR,
        commission=commission,
        lay_stake=round(lay_stake, 2),
        liability=round(liability, 2),
        outcomes=[
            OutcomeResult(
                outcome="back_wins",
                profit=round(back_wins_profit, 2),
                description=f"Free bet wins {potential_winnings:.2f}, exchange takes {liability:.2f}",
            ),
            OutcomeResult(
                outcome="lay_wins",
                profit=round(lay_wins_profit, 2),
                description=f"Free bet loses (no loss), keep {lay_stake * (1 - commission):.2f} from exchange",
            ),
        ],
        guaranteed_profit=round(guaranteed, 2),
        expected_value=round(expected, 2),
        rating=rating,
        spread_percent=round(spread, 2),
    )


def calculate_free_bet_sr(
    back_odds: float,
    lay_odds: float,
    stake: float,
    commission: float,
) -> CalcResponse:
    """
    Calculate a free bet with Stake Returned (rare, but very valuable).
    
    With SR, if you win, you get the full payout including stake.
    This is treated like a normal bet but you're not risking real money.
    
    Formula for lay stake:
        lay_stake = (free_bet * back_odds) / (lay_odds - commission)
    """
    # Calculate lay stake based on full potential payout
    potential_payout = stake * back_odds
    lay_stake = potential_payout / (lay_odds - commission)
    liability = lay_stake * (lay_odds - 1)
    
    # If back bet wins (free bet pays full amount):
    # Profit = stake * back_odds - liability
    back_wins_profit = potential_payout - liability
    
    # If lay bet wins (you keep lay stake minus commission):
    # Profit = lay_stake * (1 - commission)
    lay_wins_profit = lay_stake * (1 - commission)
    
    # The guaranteed profit is the minimum of both outcomes
    guaranteed = min(back_wins_profit, lay_wins_profit)
    
    # Expected value
    expected = (back_wins_profit + lay_wins_profit) / 2
    
    spread = calculate_spread(back_odds, lay_odds)
    rating = get_rating(spread, BetType.FREE_BET_SR)
    
    return CalcResponse(
        back_odds=back_odds,
        lay_odds=lay_odds,
        stake=stake,
        bet_type=BetType.FREE_BET_SR,
        commission=commission,
        lay_stake=round(lay_stake, 2),
        liability=round(liability, 2),
        outcomes=[
            OutcomeResult(
                outcome="back_wins",
                profit=round(back_wins_profit, 2),
                description=f"Free bet wins {potential_payout:.2f}, exchange takes {liability:.2f}",
            ),
            OutcomeResult(
                outcome="lay_wins",
                profit=round(lay_wins_profit, 2),
                description=f"Free bet loses (no loss), keep {lay_stake * (1 - commission):.2f} from exchange",
            ),
        ],
        guaranteed_profit=round(guaranteed, 2),
        expected_value=round(expected, 2),
        rating=rating,
        spread_percent=round(spread, 2),
    )


def calculate(request: CalcRequest) -> CalcResponse:
    """
    Main calculator function that routes to the appropriate calculation.
    """
    if request.bet_type == BetType.QUALIFYING:
        return calculate_qualifying_bet(
            request.back_odds,
            request.lay_odds,
            request.stake,
            request.commission,
        )
    elif request.bet_type == BetType.FREE_BET_SNR:
        return calculate_free_bet_snr(
            request.back_odds,
            request.lay_odds,
            request.stake,
            request.commission,
        )
    elif request.bet_type == BetType.FREE_BET_SR:
        return calculate_free_bet_sr(
            request.back_odds,
            request.lay_odds,
            request.stake,
            request.commission,
        )
    else:
        raise ValueError(f"Unknown bet type: {request.bet_type}")


def calculate_batch(request: BatchCalcRequest) -> BatchCalcResponse:
    """
    Calculate multiple scenarios at once.
    """
    results = [calculate(calc) for calc in request.calculations]
    
    total_profit = sum(r.guaranteed_profit for r in results)
    
    # Find the best opportunity (highest profit for free bets, lowest loss for qualifying)
    best = None
    if results:
        # For free bets, best is highest profit
        free_bet_results = [r for r in results if r.bet_type != BetType.QUALIFYING]
        if free_bet_results:
            best = max(free_bet_results, key=lambda r: r.guaranteed_profit)
        else:
            # For qualifying bets, best is lowest loss (highest guaranteed_profit since it's negative)
            best = max(results, key=lambda r: r.guaranteed_profit)
    
    return BatchCalcResponse(
        results=results,
        total_guaranteed_profit=round(total_profit, 2),
        best_opportunity=best,
    )


def calculate_retention_rate(
    free_bet_value: float,
    back_odds: float,
    lay_odds: float,
    commission: float = 0.05,
) -> float:
    """
    Calculate what percentage of a free bet's face value you can extract.
    
    This is useful for quickly comparing offers.
    Typical retention: 70-80% for SNR free bets with good odds.
    """
    result = calculate_free_bet_snr(back_odds, lay_odds, free_bet_value, commission)
    return (result.guaranteed_profit / free_bet_value) * 100










