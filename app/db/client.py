"""
Single shared Supabase client for the whole app.

Every module that needs Supabase (DB tables, Storage) should import
get_supabase_client() from here rather than creating its own client.

Requires env:
    SUPABASE_URL  - Project Settings → API → Project URL
    SUPABASE_KEY  - service_role key for this server (or anon if RLS allows)
"""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Create (once per process) and return the Supabase client."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)
