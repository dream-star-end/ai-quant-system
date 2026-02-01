"""
AI 分析路由
"""
from fastapi import APIRouter
import numpy as np
import pandas as pd

router = APIRouter()

def calculate_ma(data, window: int = 5):
    """计算移动平均线"""
    prices = [d["close"] if "close" in d else d.get("Close", 0) for d in data]
    return np.convolve(prices, np.ones(window)/window, mode='valid').tolist()

def calculate_rsi(data, period: int = 14):
    """计算 RSI 指标"""
    prices = [d["close"] if "close" in d else d.get("Close", 0) for d in data]
    df = pd.DataFrame({"close": prices})
    
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.dropna().tolist()

@router.post("/indicators")
async def calculate_indicators(data: dict):
    """计算技术指标"""
    try:
        market_data = data.get("data", [])
        if not market_data:
            return {"error": "No data provided"}
        
        indicators = {
            "ma5": calculate_ma(market_data, 5),
            "ma10": calculate_ma(market_data, 10),
            "ma20": calculate_ma(market_data, 20),
            "rsi14": calculate_rsi(market_data, 14)
        }
        return indicators
    except Exception as e:
        return {"error": str(e)}

@router.post("/predict/trend")
async def predict_trend(data: dict):
    """简单趋势预测 (基于规则)"""
    try:
        market_data = data.get("data", [])
        if len(market_data) < 5:
            return {"error": "Need at least 5 data points"}
        
        # 简单规则：比较最近3天和前3天的均价
        recent = market_data[-3:]
        past = market_data[-6:-3]
        
        recent_avg = np.mean([d.get("close", d.get("Close", 0)) for d in recent])
        past_avg = np.mean([d.get("close", d.get("Close", 0)) for d in past])
        
        change = (recent_avg - past_avg) / past_avg * 100
        
        if change > 2:
            trend = "bullish"
            signal = "买入"
        elif change < -2:
            trend = "bearish"
            signal = "卖出"
        else:
            trend = "neutral"
            signal = "持有"
        
        return {
            "trend": trend,
            "signal": signal,
            "change_pct": round(change, 2),
            "confidence": min(abs(change) * 10, 95)
        }
    except Exception as e:
        return {"error": str(e)}
