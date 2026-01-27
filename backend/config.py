"""Configuration management for the application."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # The-Odds-API Configuration
    THE_ODDS_API_KEY: str = os.getenv("THE_ODDS_API_KEY", "5e617593ea4e955e42e1c6a80a997834")
    THE_ODDS_API_URL: str = "https://api.the-odds-api.com/v4"
    
    # Supported Leagues (Top 5 European + Champions League)
    SUPPORTED_LEAGUES: list = [
        "soccer_epl",              # Premier League
        "soccer_spain_la_liga",    # La Liga
        "soccer_germany_bundesliga", # Bundesliga
        "soccer_italy_serie_a",    # Serie A
        "soccer_france_ligue_one", # Ligue 1
        "soccer_uefa_champs_league", # Champions League
    ]
    
    # Betfair Exchange key in The-Odds-API
    BETFAIR_EXCHANGE_KEY: str = "betfair_ex_uk"
    
    # Match Finder Defaults
    DEFAULT_MAX_HOURS_AHEAD: int = 48
    DEFAULT_MIN_ODDS: float = 1.5
    DEFAULT_MAX_ODDS: float = 5.0
    DEFAULT_MAX_SPREAD_PERCENT: float = 5.0
    BETFAIR_COMMISSION: float = 0.05  # 5% commission
    
    # Scraper Configuration
    ODDSCHECKER_URL: str = "https://www.oddschecker.com/free-bets"
    SCRAPER_TIMEOUT: int = 30000  # 30 seconds
    SCRAPER_DELAY_MIN: float = 1.0
    SCRAPER_DELAY_MAX: float = 3.0
    
    # LLM Configuration
    GEMINI_MODEL: str = "gemini-2.0-flash"  # Fast and free tier friendly
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 30
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required environment variables are set."""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL is not set in environment variables")
        if not cls.SUPABASE_KEY:
            raise ValueError("SUPABASE_KEY is not set in environment variables")
        return True


