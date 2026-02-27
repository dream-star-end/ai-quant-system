"""
AI 分析路由 - 趋势预测/智能推荐/综合分析
"""
from fastapi import APIRouter, Query
from schemas.common import APIResponse
from services.market_data import get_stock_history, get_crypto_history, calculate_indicators
from services.ai_service import predict_trend, generate_smart_recommendation
from services.risk_manager import calculate_risk_metrics, score_risk
from core.logger import logger

router = APIRouter()


@router.get("/predict/{symbol}")
async def predict(
    symbol: str,
    period: str = Query("6mo", description="分析数据范围"),
    asset_type: str = Query("stock", description="stock 或 crypto"),
):
    """AI 综合趋势预测"""
    if asset_type == "crypto":
        df = get_crypto_history(symbol, "1d", 200)
    else:
        df = get_stock_history(symbol, period)

    if df.empty or len(df) < 30:
        return APIResponse(success=False, message="数据不足，无法分析")

    result = predict_trend(df)
    if "error" in result:
        return APIResponse(success=False, message=result["error"])

    return APIResponse(data=result)


@router.get("/recommend/{symbol}")
async def recommend(
    symbol: str,
    period: str = Query("6mo"),
    asset_type: str = Query("stock"),
):
    """智能投资推荐"""
    if asset_type == "crypto":
        df = get_crypto_history(symbol, "1d", 200)
    else:
        df = get_stock_history(symbol, period)

    if df.empty or len(df) < 30:
        return APIResponse(success=False, message="数据不足")

    close_col = "close" if "close" in df.columns else "Close"
    trend = predict_trend(df)
    risk = calculate_risk_metrics(df[close_col].tolist())

    rec = generate_smart_recommendation(symbol, trend, risk)
    return APIResponse(data=rec)


@router.get("/risk/{symbol}")
async def risk_analysis(
    symbol: str,
    period: str = Query("1y"),
    asset_type: str = Query("stock"),
):
    """风险分析"""
    if asset_type == "crypto":
        df = get_crypto_history(symbol, "1d", 365)
    else:
        df = get_stock_history(symbol, period)

    if df.empty or len(df) < 30:
        return APIResponse(success=False, message="数据不足")

    close_col = "close" if "close" in df.columns else "Close"
    metrics = calculate_risk_metrics(df[close_col].tolist())
    risk_score = score_risk(metrics)

    return APIResponse(data={
        "symbol": symbol,
        "metrics": metrics,
        "risk_score": risk_score,
    })


@router.get("/indicators/{symbol}")
async def indicators(
    symbol: str,
    period: str = Query("6mo"),
    asset_type: str = Query("stock"),
):
    """获取全量技术指标"""
    if asset_type == "crypto":
        df = get_crypto_history(symbol, "1d", 200)
    else:
        df = get_stock_history(symbol, period)

    if df.empty:
        return APIResponse(success=False, message="无数据")

    result = calculate_indicators(df)
    return APIResponse(data={"symbol": symbol, **result})
