"""
回测路由 - 策略回测
"""
from fastapi import APIRouter, Depends
from schemas.common import APIResponse
from schemas.strategy import BacktestRequest
from services.market_data import get_stock_history, get_crypto_history
from services.backtest_engine import run_backtest
from database import get_supabase
from routers.auth import get_current_user
from core.logger import logger

router = APIRouter()


@router.post("/run")
async def run(req: BacktestRequest, user: dict = Depends(get_current_user)):
    """执行策略回测"""
    if "/" in req.symbol:
        df = get_crypto_history(req.symbol, "1d", 1000)
    else:
        df = get_stock_history(req.symbol, "5y")

    if df.empty or len(df) < 30:
        return APIResponse(success=False, message="数据不足")

    # 按日期范围过滤
    df.index = df.index.tz_localize(None) if hasattr(df.index, "tz_localize") and df.index.tz else df.index
    try:
        start = req.start_date
        end = req.end_date
        mask = (df.index >= start) & (df.index <= end)
        df = df.loc[mask]
    except Exception:
        pass

    if len(df) < 30:
        return APIResponse(success=False, message=f"选定时间范围内数据不足(仅{len(df)}条)")

    result = run_backtest(
        df,
        strategy_type=req.strategy_type,
        params=req.params,
        initial_capital=req.initial_capital,
        commission_rate=req.commission_rate,
        slippage=req.slippage,
    )

    if "error" in result:
        return APIResponse(success=False, message=result["error"])

    logger.info(f"回测完成: {req.strategy_type} on {req.symbol}, return={result['total_return']}%")
    return APIResponse(data=result)


@router.post("/run/guest")
async def run_guest(req: BacktestRequest):
    """游客模式回测（无需登录）"""
    if "/" in req.symbol:
        df = get_crypto_history(req.symbol, "1d", 1000)
    else:
        df = get_stock_history(req.symbol, "5y")

    if df.empty or len(df) < 30:
        return APIResponse(success=False, message="数据不足")

    df.index = df.index.tz_localize(None) if hasattr(df.index, "tz_localize") and df.index.tz else df.index
    try:
        mask = (df.index >= req.start_date) & (df.index <= req.end_date)
        df = df.loc[mask]
    except Exception:
        pass

    if len(df) < 30:
        return APIResponse(success=False, message=f"数据不足(仅{len(df)}条)")

    result = run_backtest(
        df,
        strategy_type=req.strategy_type,
        params=req.params,
        initial_capital=req.initial_capital,
        commission_rate=req.commission_rate,
        slippage=req.slippage,
    )
    if "error" in result:
        return APIResponse(success=False, message=result["error"])
    return APIResponse(data=result)
