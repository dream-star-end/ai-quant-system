"""
告警管理路由
"""
from fastapi import APIRouter, Depends
from schemas.common import APIResponse
from schemas.portfolio import AlertCreate
from database import get_supabase
from routers.auth import get_current_user

router = APIRouter()


@router.get("/")
async def list_alerts(user: dict = Depends(get_current_user)):
    """获取告警列表"""
    sb = get_supabase()
    result = sb.table("alerts").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
    return APIResponse(data=result.data)


@router.post("/")
async def create_alert(body: AlertCreate, user: dict = Depends(get_current_user)):
    """创建告警"""
    sb = get_supabase()
    result = sb.table("alerts").insert({
        "user_id": user["id"],
        "alert_type": body.alert_type,
        "symbol": body.symbol,
        "condition_value": body.condition_value,
        "message": body.message,
    }).execute()
    return APIResponse(data=result.data[0], message="告警创建成功")


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, user: dict = Depends(get_current_user)):
    """删除告警"""
    sb = get_supabase()
    sb.table("alerts").delete().eq("id", alert_id).eq("user_id", user["id"]).execute()
    return APIResponse(message="告警已删除")


@router.put("/{alert_id}/toggle")
async def toggle_alert(alert_id: int, user: dict = Depends(get_current_user)):
    """启用/停用告警"""
    sb = get_supabase()
    current = sb.table("alerts").select("is_active").eq("id", alert_id).eq("user_id", user["id"]).single().execute()
    if not current.data:
        return APIResponse(success=False, message="告警不存在")

    new_status = not current.data["is_active"]
    sb.table("alerts").update({"is_active": new_status}).eq("id", alert_id).execute()
    return APIResponse(message=f"告警已{'启用' if new_status else '停用'}")
