"""
Supabase client utilities.
"""
from functools import lru_cache
from supabase import create_client, Client
from app.core.config import settings


@lru_cache()
def get_supabase() -> Client:
    """Get Supabase client instance."""
    return create_client(settings.supabase_url, settings.supabase_service_key)
