"""Match filtering and ranking utilities for matched betting."""
from typing import List, Optional, Tuple
from config import Config
from models.match import Match, MatchPairing, MatchRecommendation, BookmakerOdds


def calculate_spread(back_odds: float, lay_odds: float) -> float:
    """
    Calculate the spread percentage between back and lay odds.
    
    Args:
        back_odds: Odds at the bookmaker (back bet)
        lay_odds: Odds at the exchange (lay bet)
        
    Returns:
        Spread as a percentage (e.g., 2.5 means 2.5% difference)
    """
    if back_odds <= 0:
        return float('inf')
    return abs(lay_odds - back_odds) / back_odds * 100


def calculate_lay_stake(back_stake: float, back_odds: float, lay_odds: float, 
                         commission: float = Config.BETFAIR_COMMISSION) -> float:
    """
    Calculate the lay stake to minimize qualifying loss.
    
    For a qualifying bet, we want to lose as little as possible regardless of outcome.
    
    Args:
        back_stake: Amount staked at bookmaker
        back_odds: Back odds at bookmaker
        lay_odds: Lay odds at exchange
        commission: Exchange commission rate (default 5% for Betfair)
        
    Returns:
        Optimal lay stake
    """
    # Formula: lay_stake = (back_stake * back_odds) / (lay_odds - commission)
    return (back_stake * back_odds) / (lay_odds - commission)


def calculate_qualifying_loss(back_stake: float, back_odds: float, lay_odds: float,
                               commission: float = Config.BETFAIR_COMMISSION) -> float:
    """
    Calculate the qualifying loss (cost to unlock a free bet).
    
    Args:
        back_stake: Amount staked at bookmaker
        back_odds: Back odds at bookmaker  
        lay_odds: Lay odds at exchange
        commission: Exchange commission rate
        
    Returns:
        Expected qualifying loss (positive = loss, negative = profit)
    """
    lay_stake = calculate_lay_stake(back_stake, back_odds, lay_odds, commission)
    liability = lay_stake * (lay_odds - 1)
    
    # If back bet wins: profit = back_stake * (back_odds - 1) - liability
    # If lay bet wins: profit = lay_stake * (1 - commission) - back_stake
    
    # For qualifying bet with matched stakes, both outcomes should be similar
    # The loss is approximately:
    back_win_profit = back_stake * (back_odds - 1) - liability
    lay_win_profit = lay_stake * (1 - commission) - back_stake
    
    # Average loss (they should be very close if properly matched)
    return -min(back_win_profit, lay_win_profit)


def calculate_free_bet_profit(free_bet_value: float, back_odds: float, lay_odds: float,
                               commission: float = Config.BETFAIR_COMMISSION,
                               is_snr: bool = True) -> float:
    """
    Calculate profit from a free bet (Stake Not Returned).
    
    For SNR free bets, you only get the profit portion if you win.
    
    Args:
        free_bet_value: Value of the free bet
        back_odds: Back odds at bookmaker
        lay_odds: Lay odds at exchange
        commission: Exchange commission rate
        is_snr: Whether stake is not returned (True for most free bets)
        
    Returns:
        Expected profit from the free bet
    """
    if is_snr:
        # SNR: Only get (odds - 1) * stake if back wins
        # Lay to cover: lay_stake = free_bet_value * (back_odds - 1) / (lay_odds - commission)
        lay_stake = (free_bet_value * (back_odds - 1)) / (lay_odds - commission)
        liability = lay_stake * (lay_odds - 1)
        
        # If back wins: profit = free_bet_value * (back_odds - 1) - liability
        # If lay wins: profit = lay_stake * (1 - commission)
        
        back_win_profit = free_bet_value * (back_odds - 1) - liability
        lay_win_profit = lay_stake * (1 - commission)
        
        # Both should be similar; return the minimum (guaranteed profit)
        return min(back_win_profit, lay_win_profit)
    else:
        # Stake returned: treat like a normal bet
        lay_stake = (free_bet_value * back_odds) / (lay_odds - commission)
        liability = lay_stake * (lay_odds - 1)
        
        back_win_profit = free_bet_value * (back_odds - 1) - liability
        lay_win_profit = lay_stake * (1 - commission) - free_bet_value
        
        return min(back_win_profit, lay_win_profit)


def filter_matches_by_odds_range(
    matches: List[Match],
    min_odds: float = Config.DEFAULT_MIN_ODDS,
    max_odds: float = Config.DEFAULT_MAX_ODDS,
) -> List[Match]:
    """
    Filter matches where at least one outcome has odds in the specified range.
    
    Args:
        matches: List of matches to filter
        min_odds: Minimum acceptable odds
        max_odds: Maximum acceptable odds
        
    Returns:
        Filtered list of matches
    """
    filtered = []
    for match in matches:
        for bm_odds in match.bookmaker_odds:
            # Check if any outcome is in range
            if min_odds <= bm_odds.home_odds <= max_odds:
                filtered.append(match)
                break
            if min_odds <= bm_odds.away_odds <= max_odds:
                filtered.append(match)
                break
            if bm_odds.draw_odds and min_odds <= bm_odds.draw_odds <= max_odds:
                filtered.append(match)
                break
    return filtered


def filter_matches_by_league(
    matches: List[Match],
    allowed_leagues: Optional[List[str]] = None,
) -> List[Match]:
    """
    Filter matches to only include specified leagues.
    
    Args:
        matches: List of matches to filter
        allowed_leagues: List of allowed league keys (defaults to top 5 European)
        
    Returns:
        Filtered list of matches
    """
    if allowed_leagues is None:
        allowed_leagues = Config.SUPPORTED_LEAGUES
    
    return [m for m in matches if m.sport_key in allowed_leagues]


def get_best_back_odds(match: Match, outcome: str, 
                        exclude_exchanges: bool = True) -> Optional[Tuple[str, float]]:
    """
    Find the best back odds for an outcome across all bookmakers.
    
    Args:
        match: Match object with bookmaker odds
        outcome: 'home', 'draw', or 'away'
        exclude_exchanges: Whether to exclude exchange odds (we want bookmaker backs)
        
    Returns:
        Tuple of (bookmaker_name, odds) or None if not found
    """
    best_odds = 0.0
    best_bookmaker = None
    
    exchange_keys = [Config.BETFAIR_EXCHANGE_KEY, "smarkets"]
    
    for bm_odds in match.bookmaker_odds:
        # Skip exchanges for back bets
        if exclude_exchanges and bm_odds.bookmaker_key in exchange_keys:
            continue
        
        if outcome == "home":
            odds = bm_odds.home_odds
        elif outcome == "away":
            odds = bm_odds.away_odds
        elif outcome == "draw":
            odds = bm_odds.draw_odds or 0
        else:
            continue
        
        if odds > best_odds:
            best_odds = odds
            best_bookmaker = bm_odds.bookmaker_title
    
    return (best_bookmaker, best_odds) if best_bookmaker else None


def get_betfair_lay_odds(match: Match, outcome: str) -> Optional[float]:
    """
    Get Betfair Exchange lay odds for an outcome.
    
    Args:
        match: Match object with bookmaker odds
        outcome: 'home', 'draw', or 'away'
        
    Returns:
        Lay odds or None if not available
    """
    for bm_odds in match.bookmaker_odds:
        if bm_odds.bookmaker_key == Config.BETFAIR_EXCHANGE_KEY:
            if outcome == "home":
                return bm_odds.home_odds
            elif outcome == "away":
                return bm_odds.away_odds
            elif outcome == "draw":
                return bm_odds.draw_odds
    return None


def find_best_pairings(
    matches: List[Match],
    min_odds: float = Config.DEFAULT_MIN_ODDS,
    max_odds: float = Config.DEFAULT_MAX_ODDS,
    max_spread: float = Config.DEFAULT_MAX_SPREAD_PERCENT,
) -> List[MatchPairing]:
    """
    Find the best Back/Lay pairings across all matches.
    
    Args:
        matches: List of matches to analyze
        min_odds: Minimum acceptable back odds
        max_odds: Maximum acceptable back odds
        max_spread: Maximum acceptable spread percentage
        
    Returns:
        List of MatchPairing objects sorted by spread (tightest first)
    """
    pairings: List[MatchPairing] = []
    
    for match in matches:
        # Check each outcome (home, draw, away)
        for outcome in ["home", "away", "draw"]:
            # Get best back odds from bookmakers
            back_result = get_best_back_odds(match, outcome)
            if not back_result:
                continue
            
            back_bookmaker, back_odds = back_result
            
            # Check if back odds are in range
            if not (min_odds <= back_odds <= max_odds):
                continue
            
            # Get Betfair lay odds
            lay_odds = get_betfair_lay_odds(match, outcome)
            if not lay_odds:
                continue
            
            # Calculate spread
            spread = calculate_spread(back_odds, lay_odds)
            
            # Skip if spread is too high
            if spread > max_spread:
                continue
            
            # Determine outcome name
            if outcome == "home":
                outcome_name = match.home_team
            elif outcome == "away":
                outcome_name = match.away_team
            else:
                outcome_name = "Draw"
            
            pairings.append(MatchPairing(
                match_id=match.match_id,
                home_team=match.home_team,
                away_team=match.away_team,
                league=match.sport_title,
                commence_time=match.commence_time,
                outcome=outcome,
                outcome_name=outcome_name,
                back_bookmaker=back_bookmaker,
                back_odds=back_odds,
                lay_exchange="Betfair",
                lay_odds=lay_odds,
                spread_percent=round(spread, 2),
            ))
    
    # Sort by spread (tightest first)
    pairings.sort(key=lambda p: p.spread_percent)
    
    return pairings


def calculate_match_rating(
    pairing: MatchPairing,
    target_odds: Optional[float] = None,
) -> float:
    """
    Calculate a rating (0-10) for a match pairing.
    
    Factors:
    - Spread score (40%): Tighter spread = higher score
    - Odds score (30%): Closer to optimal range (2.0-3.5) = higher score
    - League score (30%): Top leagues = higher score
    
    Args:
        pairing: The match pairing to rate
        target_odds: Target odds from offer (if available)
        
    Returns:
        Rating from 0-10
    """
    # Spread score (0-10): 0% spread = 10, 5% spread = 0
    spread_score = max(0, 10 - (pairing.spread_percent * 2))
    
    # Odds score (0-10): Optimal around 2.5, falls off above/below
    odds = pairing.back_odds
    if target_odds:
        # Score based on distance from target
        odds_diff = abs(odds - target_odds)
        odds_score = max(0, 10 - odds_diff * 2)
    else:
        # Score based on optimal range (2.0-3.5)
        if 2.0 <= odds <= 3.5:
            odds_score = 10
        elif 1.5 <= odds < 2.0 or 3.5 < odds <= 5.0:
            odds_score = 7
        else:
            odds_score = 4
    
    # League score (0-10): EPL = 10, other top 5 = 8, etc.
    top_leagues = {
        "English Premier League": 10,
        "EPL": 10,
        "Premier League": 10,
        "La Liga": 9,
        "Bundesliga": 9,
        "Serie A": 9,
        "Ligue 1": 8,
        "Champions League": 10,
        "UEFA Champions League": 10,
    }
    league_score = top_leagues.get(pairing.league, 6)
    
    # Weighted average
    rating = (spread_score * 0.4) + (odds_score * 0.3) + (league_score * 0.3)
    
    return round(rating, 1)


def create_recommendations(
    pairings: List[MatchPairing],
    stake: float = 10.0,
    free_bet_value: Optional[float] = None,
    target_odds: Optional[float] = None,
    limit: int = 10,
) -> List[MatchRecommendation]:
    """
    Create ranked match recommendations with profit calculations.
    
    Args:
        pairings: List of match pairings to evaluate
        stake: Back stake amount for calculations
        free_bet_value: Value of free bet (if applicable)
        target_odds: Target odds from offer (if applicable)
        limit: Maximum number of recommendations to return
        
    Returns:
        List of MatchRecommendation objects, ranked by rating
    """
    recommendations: List[MatchRecommendation] = []
    
    for pairing in pairings[:limit * 2]:  # Process more than needed for filtering
        # Calculate lay stake and liability
        lay_stake = calculate_lay_stake(stake, pairing.back_odds, pairing.lay_odds)
        liability = lay_stake * (pairing.lay_odds - 1)
        
        # Calculate qualifying loss
        qual_loss = calculate_qualifying_loss(stake, pairing.back_odds, pairing.lay_odds)
        
        # Calculate free bet profit
        fb_value = free_bet_value or stake  # Use stake if no free bet specified
        fb_profit = calculate_free_bet_profit(fb_value, pairing.back_odds, pairing.lay_odds)
        
        # Calculate rating
        rating = calculate_match_rating(pairing, target_odds)
        
        recommendations.append(MatchRecommendation(
            match_id=pairing.match_id,
            home_team=pairing.home_team,
            away_team=pairing.away_team,
            league=pairing.league,
            commence_time=pairing.commence_time,
            outcome=pairing.outcome,
            outcome_name=pairing.outcome_name,
            back_bookmaker=pairing.back_bookmaker,
            back_odds=pairing.back_odds,
            lay_exchange=pairing.lay_exchange,
            lay_odds=pairing.lay_odds,
            spread_percent=pairing.spread_percent,
            match_rating=rating,
            stake=stake,
            lay_stake=round(lay_stake, 2),
            liability=round(liability, 2),
            qualifying_loss=round(qual_loss, 2),
            free_bet_profit=round(fb_profit, 2),
        ))
    
    # Sort by rating (highest first)
    recommendations.sort(key=lambda r: r.match_rating, reverse=True)
    
    return recommendations[:limit]










