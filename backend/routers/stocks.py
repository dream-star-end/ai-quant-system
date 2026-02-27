"""
A股数据路由 - 行情/历史/搜索
"""
from fastapi import APIRouter, Query
from schemas.common import APIResponse
from services.market_data import (
    get_stock_quote,
    get_stock_history,
    get_multiple_quotes,
    calculate_indicators,
    STOCK_SYMBOLS,
)
from core.logger import logger

router = APIRouter()


@router.get("/quote/{symbol}")
async def quote(symbol: str):
    """获取股票实时报价"""
    data = get_stock_quote(symbol)
    if "error" in data:
        return APIResponse(success=False, message=data["error"])
    return APIResponse(data=data)


@router.get("/history/{symbol}")
async def history(symbol: str, period: str = Query("6mo", description="数据周期: 1mo,3mo,6mo,1y,2y,5y")):
    """获取股票历史 K 线数据和技术指标"""
    df = get_stock_history(symbol, period)
    if df.empty:
        return APIResponse(success=False, message="无数据")

    candles = []
    for idx, row in df.iterrows():
        candles.append({
            "date": str(idx)[:10],
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })

    indicators = calculate_indicators(df)
    return APIResponse(data={
        "symbol": symbol,
        "candles": candles,
        "indicators": indicators,
    })


@router.get("/batch")
async def batch_quotes(symbols: str = Query(None, description="逗号分隔的股票代码")):
    """批量获取多只股票报价"""
    sym_list = symbols.split(",") if symbols else None
    data = get_multiple_quotes(sym_list)
    return APIResponse(data=data)


@router.get("/symbols")
async def list_symbols():
    """获取支持的股票列表"""
    return APIResponse(data=[
        {"name": name, "symbol": sym} for name, sym in STOCK_SYMBOLS.items()
    ])
