"""
自选列表路由
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from schemas.common import APIResponse
from database import get_supabase
from routers.auth import get_current_user

router = APIRouter()


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    symbols: Optional[List[str]] = None


@router.get("/")
async def list_watchlists(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("watchlists").select("*").eq("user_id", user["id"]).execute()
    return APIResponse(data=result.data)


@router.post("/")
async def create_watchlist(body: WatchlistUpdate, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("watchlists").insert({
        "user_id": user["id"],
        "name": body.name or "新自选",
        "symbols": body.symbols or [],
    }).execute()
    return APIResponse(data=result.data[0])


@router.put("/{watchlist_id}")
async def update_watchlist(watchlist_id: int, body: WatchlistUpdate, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = sb.table("watchlists").update(data).eq("id", watchlist_id).eq("user_id", user["id"]).execute()
    return APIResponse(data=result.data[0] if result.data else None)


@router.put("/{watchlist_id}/add/{symbol}")
async def add_symbol(watchlist_id: int, symbol: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    wl = sb.table("watchlists").select("symbols").eq("id", watchlist_id).eq("user_id", user["id"]).single().execute()
    if not wl.data:
        return APIResponse(success=False, message="自选列表不存在")
    symbols = wl.data["symbols"] or []
    if symbol not in symbols:
        symbols.append(symbol)
        sb.table("watchlists").update({"symbols": symbols}).eq("id", watchlist_id).execute()
    return APIResponse(data=symbols, message=f"已添加 {symbol}")


@router.put("/{watchlist_id}/remove/{symbol:path}")
async def remove_symbol(watchlist_id: int, symbol: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    wl = sb.table("watchlists").select("symbols").eq("id", watchlist_id).eq("user_id", user["id"]).single().execute()
    if not wl.data:
        return APIResponse(success=False, message="自选列表不存在")
    symbols = [s for s in (wl.data["symbols"] or []) if s != symbol]
    sb.table("watchlists").update({"symbols": symbols}).eq("id", watchlist_id).execute()
    return APIResponse(data=symbols, message=f"已移除 {symbol}")
