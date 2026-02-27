"""
Supabase 数据库客户端
"""
from supabase import create_client, Client
from config import get_settings

settings = get_settings()

_client: Client = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client
