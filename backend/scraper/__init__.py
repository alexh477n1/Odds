"""Scraper package."""
from .oddschecker_scraper import scrape_oddschecker_offers as scrape_offers
from .parser import parse_offer_with_llm

__all__ = ["scrape_offers", "parse_offer_with_llm"]



