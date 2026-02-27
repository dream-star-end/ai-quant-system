"""
市场数据服务 - 统一的市场数据获取接口
支持 A股(yfinance) 和 加密货币(ccxt)
"""
import yfinance as yf
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from core.logger import logger

STOCK_SYMBOLS = {
    "沪深300": "000300.SS",
    "上证指数": "000001.SS",
    "深证成指": "399001.SZ",
    "创业板指": "399006.SZ",
    "贵州茅台": "600519.SS",
    "宁德时代": "300750.SZ",
    "招商银行": "600036.SS",
    "中国平安": "601318.SS",
    "比亚迪": "002594.SZ",
    "腾讯控股": "0700.HK",
    "阿里巴巴": "9988.HK",
    "美团": "3690.HK",
}

TOP_CRYPTO = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT",
    "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT",
    "MATIC/USDT", "LTC/USDT",
]

_exchanges: Dict[str, Any] = {}


def _get_exchange(name: str = "binance"):
    if name not in _exchanges:
        cls = getattr(ccxt, name, None)
        if cls is None:
            raise ValueError(f"不支持的交易所: {name}")
        _exchanges[name] = cls({"enableRateLimit": True})
    return _exchanges[name]


# ------------------------------------------------------------------
# 股票
# ------------------------------------------------------------------

def get_stock_quote(symbol: str) -> Dict:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if hist.empty:
            return {"error": "无数据"}
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        change = float(latest["Close"] - prev["Close"])
        change_pct = change / float(prev["Close"]) * 100
        return {
            "symbol": symbol,
            "price": round(float(latest["Close"]), 2),
            "open": round(float(latest["Open"]), 2),
            "high": round(float(latest["High"]), 2),
            "low": round(float(latest["Low"]), 2),
            "volume": int(latest["Volume"]),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "timestamp": latest.name.isoformat(),
        }
    except Exception as e:
        logger.error(f"获取股票报价失败 {symbol}: {e}")
        return {"error": str(e)}


def get_stock_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        df.index = df.index.tz_localize(None) if df.index.tz else df.index
        return df
    except Exception as e:
        logger.error(f"获取股票历史失败 {symbol}: {e}")
        return pd.DataFrame()


def get_multiple_quotes(symbols: Optional[List[str]] = None) -> List[Dict]:
    if symbols is None:
        symbols = list(STOCK_SYMBOLS.values())
    results = []
    for sym in symbols:
        q = get_stock_quote(sym)
        if "error" not in q:
            name = next((k for k, v in STOCK_SYMBOLS.items() if v == sym), sym)
            q["name"] = name
            results.append(q)
    return results


# ------------------------------------------------------------------
# 加密货币
# ------------------------------------------------------------------

def get_crypto_price(symbol: str = "BTC/USDT", exchange: str = "binance") -> Dict:
    try:
        ex = _get_exchange(exchange)
        ticker = ex.fetch_ticker(symbol)
        return {
            "symbol": symbol,
            "price": ticker.get("last", 0),
            "high": ticker.get("high", 0),
            "low": ticker.get("low", 0),
            "volume": ticker.get("baseVolume", 0),
            "change_pct": ticker.get("percentage", 0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"获取加密货币价格失败 {symbol}: {e}")
        return {"error": str(e)}


def get_crypto_history(
    symbol: str = "BTC/USDT",
    timeframe: str = "1d",
    limit: int = 200,
    exchange: str = "binance",
) -> pd.DataFrame:
    try:
        ex = _get_exchange(exchange)
        ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        logger.error(f"获取加密货币历史失败 {symbol}: {e}")
        return pd.DataFrame()


def get_multiple_crypto_quotes(symbols: Optional[List[str]] = None) -> List[Dict]:
    if symbols is None:
        symbols = TOP_CRYPTO
    results = []
    for sym in symbols:
        q = get_crypto_price(sym)
        if "error" not in q:
            results.append(q)
    return results


# ------------------------------------------------------------------
# 技术指标计算 (统一接口)
# ------------------------------------------------------------------

def calculate_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """对一个 OHLCV DataFrame 计算全量技术指标"""
    if df.empty or len(df) < 20:
        return {}

    close = df["close"] if "close" in df.columns else df["Close"]
    high = df["high"] if "high" in df.columns else df["High"]
    low = df["low"] if "low" in df.columns else df["Low"]
    volume = df["volume"] if "volume" in df.columns else df["Volume"]

    result: Dict[str, Any] = {}

    # MA
    for w in [5, 10, 20, 60]:
        result[f"ma{w}"] = close.rolling(window=w).mean().tolist()

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    result["rsi14"] = (100 - 100 / (1 + rs)).tolist()

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    result["macd"] = macd_line.tolist()
    result["macd_signal"] = signal_line.tolist()
    result["macd_hist"] = (macd_line - signal_line).tolist()

    # Bollinger Bands
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    result["boll_upper"] = (ma20 + 2 * std20).tolist()
    result["boll_middle"] = ma20.tolist()
    result["boll_lower"] = (ma20 - 2 * std20).tolist()

    # KDJ
    low_n = low.rolling(9).min()
    high_n = high.rolling(9).max()
    rsv = (close - low_n) / (high_n - low_n).replace(0, np.nan) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    result["kdj_k"] = k.tolist()
    result["kdj_d"] = d.tolist()
    result["kdj_j"] = j.tolist()

    # Volume MA
    result["vol_ma5"] = volume.rolling(5).mean().tolist()
    result["vol_ma10"] = volume.rolling(10).mean().tolist()

    result["dates"] = [str(d)[:10] for d in df.index]
    result["closes"] = close.tolist()
    result["volumes"] = volume.tolist()

    return result
