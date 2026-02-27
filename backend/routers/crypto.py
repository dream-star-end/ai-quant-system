"""
加密货币数据路由
"""
from fastapi import APIRouter, Query
from schemas.common import APIResponse
from services.market_data import (
    get_crypto_price,
    get_crypto_history,
    get_multiple_crypto_quotes,
    calculate_indicators,
    TOP_CRYPTO,
)
from core.logger import logger

router = APIRouter()


@router.get("/price/{symbol:path}")
async def price(symbol: str, exchange: str = Query("binance")):
    """获取加密货币实时价格"""
    data = get_crypto_price(symbol, exchange)
    if "error" in data:
        return APIResponse(success=False, message=data["error"])
    return APIResponse(data=data)


@router.get("/history/{symbol:path}")
async def history(
    symbol: str,
    timeframe: str = Query("1d", description="K线周期: 1m,5m,15m,1h,4h,1d"),
    limit: int = Query(200, ge=10, le=1000),
    exchange: str = Query("binance"),
):
    """获取加密货币历史 K 线和技术指标"""
    df = get_crypto_history(symbol, timeframe, limit, exchange)
    if df.empty:
        return APIResponse(success=False, message="无数据")

    candles = []
    for idx, row in df.iterrows():
        candles.append({
            "date": str(idx)[:19],
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": round(float(row["volume"]), 2),
        })

    indicators = calculate_indicators(df)
    return APIResponse(data={
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "indicators": indicators,
    })


@router.get("/batch")
async def batch_prices():
    """批量获取主流加密货币价格"""
    data = get_multiple_crypto_quotes()
    return APIResponse(data=data)


@router.get("/symbols")
async def list_symbols():
    """获取支持的加密货币列表"""
    return APIResponse(data=TOP_CRYPTO)
