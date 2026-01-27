"""Client for The-Odds-API to fetch match odds."""
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from config import Config
from models.match import Match, BookmakerOdds


class OddsAPIClient:
    """Client for interacting with The-Odds-API."""

    def __init__(self):
        self.api_key = Config.THE_ODDS_API_KEY
        self.base_url = Config.THE_ODDS_API_URL
        self.requests_remaining: Optional[int] = None
        self.requests_used: Optional[int] = None

    def _parse_bookmaker_odds(self, bookmaker_data: Dict[str, Any]) -> Optional[BookmakerOdds]:
        """Parse bookmaker odds from API response."""
        try:
            markets = bookmaker_data.get("markets", [])
            h2h_market = next((m for m in markets if m["key"] == "h2h"), None)

            if not h2h_market:
                return None

            outcomes = h2h_market.get("outcomes", [])
            if len(outcomes) < 2:
                return None

            odds_by_name = {o["name"]: o["price"] for o in outcomes}

            return BookmakerOdds(
                bookmaker_key=bookmaker_data["key"],
                bookmaker_title=bookmaker_data["title"],
                home_odds=0,
                draw_odds=None,
                away_odds=0,
                last_update=datetime.fromisoformat(
                    bookmaker_data["last_update"].replace("Z", "+00:00")
                ),
            ), odds_by_name
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error parsing bookmaker odds: {e}")
            return None

    def _parse_match(self, match_data: Dict[str, Any]) -> Optional[Match]:
        """Parse match data from API response."""
        try:
            home_team = match_data["home_team"]
            away_team = match_data["away_team"]

            bookmaker_odds_list = []

            for bookmaker in match_data.get("bookmakers", []):
                result = self._parse_bookmaker_odds(bookmaker)
                if result is None:
                    continue

                odds_obj, odds_by_name = result

                home_odds = odds_by_name.get(home_team)
                away_odds = odds_by_name.get(away_team)
                draw_odds = odds_by_name.get("Draw")

                if home_odds is None or away_odds is None:
                    continue

                bookmaker_odds_list.append(BookmakerOdds(
                    bookmaker_key=odds_obj.bookmaker_key,
                    bookmaker_title=odds_obj.bookmaker_title,
                    home_odds=home_odds,
                    draw_odds=draw_odds,
                    away_odds=away_odds,
                    last_update=odds_obj.last_update,
                ))

            return Match(
                match_id=match_data["id"],
                sport_key=match_data["sport_key"],
                sport_title=match_data["sport_title"],
                home_team=home_team,
                away_team=away_team,
                commence_time=datetime.fromisoformat(
                    match_data["commence_time"].replace("Z", "+00:00")
                ),
                bookmaker_odds=bookmaker_odds_list,
            )
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error parsing match: {e}")
            return None

    async def get_upcoming_matches(
        self,
        leagues: Optional[List[str]] = None,
        hours_ahead: int = 48,
    ) -> List[Match]:
        if leagues is None:
            leagues = Config.SUPPORTED_LEAGUES

        all_matches: List[Match] = []
        cutoff_time = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for league in leagues:
                try:
                    url = f"{self.base_url}/sports/{league}/odds"
                    params = {
                        "apiKey": self.api_key,
                        "regions": "uk",
                        "markets": "h2h",
                        "oddsFormat": "decimal",
                    }

                    response = await client.get(url, params=params)
                    self.requests_remaining = response.headers.get("x-requests-remaining")
                    self.requests_used = response.headers.get("x-requests-used")

                    if response.status_code == 404:
                        print(f"No matches found for {league}")
                        continue

                    response.raise_for_status()
                    matches_data = response.json()

                    for match_data in matches_data:
                        match = self._parse_match(match_data)
                        if match and match.commence_time <= cutoff_time:
                            all_matches.append(match)

                except httpx.HTTPStatusError as e:
                    print(f"HTTP error fetching {league}: {e}")
                except Exception as e:
                    print(f"Error fetching {league}: {e}")

        all_matches.sort(key=lambda m: m.commence_time)
        return all_matches

    async def get_all_upcoming_odds(self, hours_ahead: int = 48) -> List[Match]:
        cutoff_time = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
        matches: List[Match] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/sports/upcoming/odds"
                params = {
                    "apiKey": self.api_key,
                    "regions": "uk",
                    "markets": "h2h",
                    "oddsFormat": "decimal",
                }

                response = await client.get(url, params=params)
                self.requests_remaining = response.headers.get("x-requests-remaining")
                self.requests_used = response.headers.get("x-requests-used")
                response.raise_for_status()
                matches_data = response.json()

                for match_data in matches_data:
                    if not match_data.get("sport_key", "").startswith("soccer"):
                        continue

                    match = self._parse_match(match_data)
                    if match and match.commence_time <= cutoff_time:
                        matches.append(match)

            except httpx.HTTPStatusError as e:
                print(f"HTTP error fetching upcoming odds: {e}")
            except Exception as e:
                print(f"Error fetching upcoming odds: {e}")

        matches.sort(key=lambda m: m.commence_time)
        return matches

