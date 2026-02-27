"""
AI Agent 路由 - 自主交易代理
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from schemas.common import APIResponse
from database import get_supabase
from routers.auth import get_current_user
from services.agent_service import run_agent_check, execute_decision
from services.deepseek_service import is_deepseek_configured
from core.logger import logger

router = APIRouter()


class AgentCreate(BaseModel):
    portfolio_id: int
    name: str = "AI Agent"
    mode: str = "approval"  # autonomous / approval / observe
    symbols: List[str] = []
    strategy_preference: str = "balanced"  # conservative / balanced / aggressive
    risk_tolerance: str = "medium"  # low / medium / high
    max_trades_per_day: int = 5
    max_position_pct: float = 0.15
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.15
    check_interval_minutes: int = 30


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    mode: Optional[str] = None
    symbols: Optional[List[str]] = None
    strategy_preference: Optional[str] = None
    risk_tolerance: Optional[str] = None
    max_trades_per_day: Optional[int] = None
    max_position_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    check_interval_minutes: Optional[int] = None


# ---------- Agent 会话管理 ----------

@router.get("/")
async def list_agents(user: dict = Depends(get_current_user)):
    """获取用户的所有 Agent 会话"""
    sb = get_supabase()
    result = sb.table("agent_sessions").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
    return APIResponse(data=result.data)


@router.post("/")
async def create_agent(body: AgentCreate, user: dict = Depends(get_current_user)):
    """创建 Agent 会话"""
    if not is_deepseek_configured():
        return APIResponse(success=False, message="需要先配置 DEEPSEEK_API_KEY 才能使用 AI Agent")

    sb = get_supabase()

    pf = sb.table("portfolios").select("id, is_paper").eq("id", body.portfolio_id).eq("user_id", user["id"]).single().execute()
    if not pf.data:
        raise HTTPException(status_code=404, detail="组合不存在")

    if not pf.data.get("is_paper") and body.mode == "autonomous":
        return APIResponse(success=False, message="安全限制: 实盘组合不允许全自动模式，请使用 approval 审批模式")

    result = sb.table("agent_sessions").insert({
        "user_id": user["id"],
        "portfolio_id": body.portfolio_id,
        "name": body.name,
        "mode": body.mode,
        "status": "paused",
        "symbols": body.symbols,
        "strategy_preference": body.strategy_preference,
        "risk_tolerance": body.risk_tolerance,
        "max_trades_per_day": body.max_trades_per_day,
        "max_position_pct": body.max_position_pct,
        "stop_loss_pct": body.stop_loss_pct,
        "take_profit_pct": body.take_profit_pct,
        "check_interval_minutes": body.check_interval_minutes,
    }).execute()

    logger.info(f"Agent 创建: {user['username']} -> {body.name} ({body.mode})")
    return APIResponse(data=result.data[0], message="Agent 创建成功")


@router.put("/{agent_id}")
async def update_agent(agent_id: int, body: AgentUpdate, user: dict = Depends(get_current_user)):
    """更新 Agent 配置"""
    sb = get_supabase()
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        return APIResponse(success=False, message="无更新内容")

    result = sb.table("agent_sessions").update(data).eq("id", agent_id).eq("user_id", user["id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return APIResponse(data=result.data[0], message="配置已更新")


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, user: dict = Depends(get_current_user)):
    """删除 Agent"""
    sb = get_supabase()
    sb.table("agent_sessions").delete().eq("id", agent_id).eq("user_id", user["id"]).execute()
    return APIResponse(message="Agent 已删除")


# ---------- Agent 控制 ----------

@router.post("/{agent_id}/start")
async def start_agent(agent_id: int, user: dict = Depends(get_current_user)):
    """启动 Agent"""
    sb = get_supabase()
    session = sb.table("agent_sessions").select("*").eq("id", agent_id).eq("user_id", user["id"]).single().execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    if not is_deepseek_configured():
        return APIResponse(success=False, message="请先配置 DEEPSEEK_API_KEY")

    sb.table("agent_sessions").update({
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", agent_id).execute()

    logger.info(f"Agent 启动: {session.data['name']} (mode={session.data['mode']})")
    return APIResponse(message=f"Agent 已启动 (模式: {session.data['mode']})")


@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: int, user: dict = Depends(get_current_user)):
    """停止 Agent"""
    sb = get_supabase()
    sb.table("agent_sessions").update({"status": "stopped"}).eq("id", agent_id).eq("user_id", user["id"]).execute()
    return APIResponse(message="Agent 已停止")


@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: int, user: dict = Depends(get_current_user)):
    """暂停 Agent"""
    sb = get_supabase()
    sb.table("agent_sessions").update({"status": "paused"}).eq("id", agent_id).eq("user_id", user["id"]).execute()
    return APIResponse(message="Agent 已暂停")


# ---------- Agent 运行 ----------

@router.post("/{agent_id}/run-check")
async def run_check(agent_id: int, user: dict = Depends(get_current_user)):
    """手动触发一次 Agent 分析检查"""
    sb = get_supabase()
    session = sb.table("agent_sessions").select("*").eq("id", agent_id).eq("user_id", user["id"]).single().execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    if session.data["status"] not in ("running", "paused"):
        return APIResponse(success=False, message="Agent 未处于可运行状态")

    # 临时设为 running 以便执行检查
    was_paused = session.data["status"] == "paused"
    if was_paused:
        sb.table("agent_sessions").update({"status": "running"}).eq("id", agent_id).execute()

    decisions = await run_agent_check(agent_id)

    if was_paused:
        sb.table("agent_sessions").update({"status": "paused"}).eq("id", agent_id).execute()

    return APIResponse(data=decisions, message=f"分析完成，生成 {len(decisions)} 条决策")


# ---------- 决策管理 ----------

@router.get("/{agent_id}/decisions")
async def list_decisions(
    agent_id: int,
    limit: int = 50,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """获取 Agent 决策历史"""
    sb = get_supabase()
    query = sb.table("agent_decisions").select("*").eq("session_id", agent_id).order("created_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return APIResponse(data=result.data)


@router.get("/{agent_id}/decisions/pending")
async def list_pending_decisions(agent_id: int, user: dict = Depends(get_current_user)):
    """获取待审批决策"""
    sb = get_supabase()
    result = sb.table("agent_decisions").select("*").eq("session_id", agent_id).eq("status", "pending").order("created_at", desc=True).execute()
    return APIResponse(data=result.data)


@router.post("/decisions/{decision_id}/approve")
async def approve_decision(decision_id: int, user: dict = Depends(get_current_user)):
    """审批通过并执行决策"""
    result = await execute_decision(decision_id)
    if "error" in result:
        return APIResponse(success=False, message=result["error"])
    return APIResponse(data=result, message="决策已执行")


@router.post("/decisions/{decision_id}/reject")
async def reject_decision(decision_id: int, user: dict = Depends(get_current_user)):
    """驳回决策"""
    sb = get_supabase()
    sb.table("agent_decisions").update({
        "status": "rejected",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", decision_id).execute()
    return APIResponse(message="决策已驳回")
