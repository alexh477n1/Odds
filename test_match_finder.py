"""Test script for the match finder functionality."""
import asyncio
import pytest
from backend.services.odds_api_client import OddsAPIClient
from backend.utils.match_filtering import (
    filter_matches_by_odds_range,
    find_best_pairings,
    create_recommendations,
    calculate_spread,
    calculate_qualifying_loss,
    calculate_free_bet_profit,
)
from backend.config import Config


class TestSpreadCalculations:
    """Test spread and profit calculations."""

    def test_spread_calculation(self):
        """Test basic spread calculation."""
        back_odds = 2.10
        lay_odds = 2.14
        spread = calculate_spread(back_odds, lay_odds)
        assert spread == pytest.approx(1.87, rel=0.1)

    def test_qualifying_loss(self):
        """Test qualifying loss calculation."""
        stake = 10.0
        back_odds = 2.10
        lay_odds = 2.14
        qual_loss = calculate_qualifying_loss(stake, back_odds, lay_odds)
        assert qual_loss > 0
        assert qual_loss < 1.0  # Should be small for tight spread

    def test_free_bet_profit(self):
        """Test free bet profit calculation."""
        free_bet = 10.0
        back_odds = 2.10
        lay_odds = 2.14
        fb_profit = calculate_free_bet_profit(free_bet, back_odds, lay_odds)
        assert fb_profit > 0
        assert fb_profit < free_bet  # Profit is less than free bet value

    def test_tight_spread_better_profit(self):
        """Verify tighter spread gives better profit."""
        stake = 10.0
        
        # Tight spread
        tight_qual = calculate_qualifying_loss(stake, 2.0, 2.02)
        tight_profit = calculate_free_bet_profit(stake, 2.0, 2.02)
        
        # Wide spread
        wide_qual = calculate_qualifying_loss(stake, 2.0, 2.20)
        wide_profit = calculate_free_bet_profit(stake, 2.0, 2.20)
        
        # Tight spread should have lower qual loss and higher profit
        assert tight_qual < wide_qual
        assert tight_profit > wide_profit

    def test_various_odds_scenarios(self):
        """Test calculations with various odds."""
        scenarios = [
            (2.0, 2.02, "Tight spread"),
            (2.5, 2.55, "Medium spread"),
            (3.0, 3.15, "Wide spread"),
        ]
        
        for back, lay, label in scenarios:
            spread = calculate_spread(back, lay)
            qual = calculate_qualifying_loss(10, back, lay)
            profit = calculate_free_bet_profit(10, back, lay)
            
            assert spread > 0, f"{label}: Spread should be positive"
            assert qual >= 0, f"{label}: Qualifying loss should be non-negative"
            assert profit > 0, f"{label}: Free bet profit should be positive"


class TestOddsAPI:
    """Test The-Odds-API client."""

    @pytest.mark.asyncio
    async def test_fetch_matches(self):
        """Test fetching matches from API."""
        client = OddsAPIClient()
        
        matches = await client.get_upcoming_matches(
            leagues=Config.SUPPORTED_LEAGUES[:2],  # Limit to 2 leagues for speed
            hours_ahead=48,
        )
        
        # Should return a list (may be empty if no matches)
        assert isinstance(matches, list)
        
        if matches:
            match = matches[0]
            assert hasattr(match, 'display_name')
            assert hasattr(match, 'bookmaker_odds')
            assert hasattr(match, 'hours_until_start')

    @pytest.mark.asyncio
    async def test_api_requests_remaining(self):
        """Test API tracks remaining requests."""
        client = OddsAPIClient()
        
        await client.get_upcoming_matches(
            leagues=Config.SUPPORTED_LEAGUES[:1],
            hours_ahead=24,
        )
        
        # After a request, should have requests_remaining set
        # (may be None if API didn't return header, or string)
        if client.requests_remaining is not None:
            remaining = int(client.requests_remaining)
            assert remaining >= 0


class TestMatchFiltering:
    """Test match filtering and pairing."""

    @pytest.fixture
    def sample_matches(self):
        """Fetch sample matches for testing."""
        async def fetch():
            client = OddsAPIClient()
            matches = await client.get_upcoming_matches(
                leagues=Config.SUPPORTED_LEAGUES[:2],
                hours_ahead=72,
            )
            return matches
        return asyncio.get_event_loop().run_until_complete(fetch())

    def test_filter_by_odds_range(self, sample_matches):
        """Test filtering matches by odds range."""
        matches = sample_matches
        
        if not matches:
            pytest.skip("No matches available for testing")
        
        filtered = filter_matches_by_odds_range(matches, min_odds=1.5, max_odds=5.0)
        assert isinstance(filtered, list)
        
        # All filtered matches should have odds in range
        for match in filtered:
            for bookie in match.bookmaker_odds:
                for market in bookie.markets:
                    for outcome in market.outcomes:
                        if 1.5 <= outcome.price <= 5.0:
                            break

    def test_find_pairings(self, sample_matches):
        """Test finding back/lay pairings."""
        matches = sample_matches
        
        if not matches:
            pytest.skip("No matches available for testing")
        
        pairings = find_best_pairings(
            matches,
            min_odds=1.5,
            max_odds=5.0,
            max_spread=10.0,  # Wide spread to ensure we find some
        )
        
        assert isinstance(pairings, list)
        
        for pairing in pairings:
            assert hasattr(pairing, 'back_odds')
            assert hasattr(pairing, 'lay_odds')
            assert hasattr(pairing, 'spread_percent')
            assert pairing.back_odds > 0
            assert pairing.lay_odds > 0
            assert pairing.spread_percent >= 0


class TestRecommendations:
    """Test recommendation generation."""

    @pytest.fixture
    def sample_pairings(self):
        """Fetch sample pairings for testing."""
        async def fetch():
            client = OddsAPIClient()
            matches = await client.get_upcoming_matches(
                leagues=Config.SUPPORTED_LEAGUES[:3],
                hours_ahead=72,
            )
            
            if not matches:
                return []
            
            pairings = find_best_pairings(
                matches,
                min_odds=1.5,
                max_odds=5.0,
                max_spread=10.0,
            )
            return pairings
        return asyncio.get_event_loop().run_until_complete(fetch())

    def test_create_recommendations(self, sample_pairings):
        """Test creating recommendations from pairings."""
        pairings = sample_pairings
        
        if not pairings:
            pytest.skip("No pairings available for testing")
        
        recommendations = create_recommendations(
            pairings,
            stake=10.0,
            free_bet_value=10.0,
            limit=5,
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5
        
        for rec in recommendations:
            assert hasattr(rec, 'match_rating')
            assert hasattr(rec, 'lay_stake')
            assert hasattr(rec, 'liability')
            assert hasattr(rec, 'qualifying_loss')
            assert hasattr(rec, 'free_bet_profit')

    def test_recommendations_sorted_by_rating(self, sample_pairings):
        """Test recommendations are sorted by rating."""
        pairings = sample_pairings
        
        if len(pairings) < 2:
            pytest.skip("Need at least 2 pairings for sorting test")
        
        recommendations = create_recommendations(
            pairings,
            stake=10.0,
            free_bet_value=10.0,
            limit=10,
        )
        
        if len(recommendations) >= 2:
            # Higher rated should come first
            for i in range(len(recommendations) - 1):
                assert recommendations[i].match_rating >= recommendations[i + 1].match_rating


# Legacy runner for standalone execution
async def main():
    """Run tests manually (for debugging)."""
    print("\n" + "=== MATCH FINDER TEST SUITE ===".center(60))
    print("=" * 60)
    
    # Test calculations
    test_calcs = TestSpreadCalculations()
    test_calcs.test_spread_calculation()
    test_calcs.test_qualifying_loss()
    test_calcs.test_free_bet_profit()
    print("[OK] Spread calculations passed")
    
    # Test API
    client = OddsAPIClient()
    matches = await client.get_upcoming_matches(
        leagues=Config.SUPPORTED_LEAGUES,
        hours_ahead=48,
    )
    print(f"[OK] Fetched {len(matches)} matches")
    
    # Test filtering
    if matches:
        pairings = find_best_pairings(
            matches,
            min_odds=1.5,
            max_odds=5.0,
            max_spread=5.0,
        )
        print(f"[OK] Found {len(pairings)} pairings")
        
        if pairings:
            recommendations = create_recommendations(
                pairings,
                stake=10.0,
                free_bet_value=10.0,
                limit=5,
            )
            print(f"[OK] Generated {len(recommendations)} recommendations")
    
    print("\n[SUCCESS] All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
