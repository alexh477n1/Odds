"""Database package."""
from .supabase_client import init_supabase, save_offers, get_latest_offers, get_supabase_client

__all__ = ["init_supabase", "save_offers", "get_latest_offers", "get_supabase_client"]



