"""
策略管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from schemas.common import APIResponse
from schemas.strategy import StrategyCreate, StrategyUpdate
from database import get_supabase
from routers.auth import get_current_user
from core.logger import logger

router = APIRouter()


@router.get("/")
async def list_strategies(user: dict = Depends(get_current_user)):
    """获取用户策略列表"""
    sb = get_supabase()
    result = sb.table("strategies").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
    return APIResponse(data=result.data)


@router.post("/")
async def create_strategy(body: StrategyCreate, user: dict = Depends(get_current_user)):
    """创建策略"""
    sb = get_supabase()
    result = sb.table("strategies").insert({
        "user_id": user["id"],
        "name": body.name,
        "description": body.description,
        "strategy_type": body.strategy_type,
        "params": body.params,
        "symbols": body.symbols,
        "timeframe": body.timeframe,
    }).execute()
    logger.info(f"用户 {user['username']} 创建策略: {body.name}")
    return APIResponse(data=result.data[0], message="策略创建成功")


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int, user: dict = Depends(get_current_user)):
    """获取策略详情"""
    sb = get_supabase()
    result = sb.table("strategies").select("*").eq("id", strategy_id).eq("user_id", user["id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="策略不存在")
    return APIResponse(data=result.data[0])


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: int, body: StrategyUpdate, user: dict = Depends(get_current_user)):
    """更新策略"""
    sb = get_supabase()
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_data:
        return APIResponse(success=False, message="无更新内容")

    result = sb.table("strategies").update(update_data).eq("id", strategy_id).eq("user_id", user["id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="策略不存在")
    return APIResponse(data=result.data[0], message="策略已更新")


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, user: dict = Depends(get_current_user)):
    """删除策略"""
    sb = get_supabase()
    sb.table("strategies").delete().eq("id", strategy_id).eq("user_id", user["id"]).execute()
    return APIResponse(message="策略已删除")


@router.get("/types/list")
async def list_strategy_types():
    """获取支持的策略类型"""
    return APIResponse(data=[
        {"type": "ma_cross", "name": "均线交叉", "description": "快慢均线金叉死叉策略", "params": {"fast_period": 5, "slow_period": 20}},
        {"type": "rsi", "name": "RSI超买超卖", "description": "RSI指标在超买超卖区域交易", "params": {"period": 14, "overbought": 70, "oversold": 30}},
        {"type": "macd", "name": "MACD信号", "description": "MACD与信号线交叉策略", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}},
        {"type": "bollinger", "name": "布林带", "description": "价格触及布林带上下轨交易", "params": {"period": 20, "num_std": 2}},
        {"type": "dual_thrust", "name": "Dual Thrust", "description": "经典日内突破策略", "params": {"lookback": 5, "k1": 0.5, "k2": 0.5}},
        {"type": "turtle", "name": "海龟交易", "description": "经典趋势跟踪策略", "params": {"entry_period": 20, "exit_period": 10}},
    ])
