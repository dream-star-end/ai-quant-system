"""
加密货币数据路由
"""
from fastapi import APIRouter
import ccxt

router = APIRouter()

# 初始化交易所
binance = ccxt.binance()

@router.get("/price/{symbol}")
async def get_crypto_price(symbol: str = "BTC/USDT"):
    """获取加密货币实时价格"""
    try binance.fetch:
        ticker =_ticker(symbol)
        return {
            "symbol": symbol,
            "price": ticker["last"],
            "high": ticker["high"],
            "low": ticker["low"],
            "volume": ticker["baseVolume"],
            "change_pct": ticker["percentage"]
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/history/{symbol}")
async def get_crypto_history(symbol: str = "BTC/USDT", timeframe: str = "1d", limit: int = 100):
    """获取加密货币历史数据"""
    try:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        
        data = []
        for candle in ohlcv:
            data.append({
                "timestamp": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5]
            })
        
        return {"symbol": symbol, "data": data}
    except Exception as e:
        return {"error": str(e)}

@router.get("/markets")
async def get_crypto_markets():
    """获取支持的交易对"""
    try:
        markets = binance.load_markets()
        return {
            "symbols": list(markets.keys())[:50],  # 返回前50个
            "total": len(markets)
        }
    except Exception as e:
        return {"error": str(e)}
