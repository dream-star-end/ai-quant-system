"""
A股数据路由
"""
from fastapi import APIRouter
import yfinance as yf
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/history/{symbol}")
async def get_stock_history(symbol: str, period: str = "1y"):
    """获取股票历史数据"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        data = hist.to_dict(orient="records")
        
        # 转换日期格式
        for item in data:
            item["Date"] = item["Date"].isoformat()
        
        return {"symbol": symbol, "data": data}
    except Exception as e:
        return {"error": str(e)}

@router.get("/info/{symbol}")
async def get_stock_info(symbol: str):
    """获取股票基本信息"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {"symbol": symbol, "info": info}
    except Exception as e:
        return {"error": str(e)}

@router.get("/quote/{symbol}")
async def get_stock_quote(symbol: str):
    """获取股票实时报价"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if hist.empty:
            return {"error": "No data found"}
        
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        
        change = latest["Close"] - prev["Close"]
        change_pct = (change / prev["Close"]) * 100
        
        return {
            "symbol": symbol,
            "price": latest["Close"],
            "change": change,
            "change_pct": change_pct,
            "volume": latest["Volume"],
            "timestamp": latest.name.isoformat()
        }
    except Exception as e:
        return {"error": str(e)}
