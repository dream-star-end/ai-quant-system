"""市场数据相关模型"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class StockQuote(BaseModel):
    symbol: str
    name: Optional[str] = None
    price: float
    change: float
    change_pct: float
    volume: float
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    timestamp: Optional[str] = None


class CryptoQuote(BaseModel):
    symbol: str
    price: float
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    change_pct: Optional[float] = None


class OHLCV(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataResponse(BaseModel):
    symbol: str
    data: List[OHLCV] = []


class IndicatorRequest(BaseModel):
    symbol: str
    period: str = "6mo"
    indicators: List[str] = ["ma", "rsi", "macd", "bollinger"]


class IndicatorResult(BaseModel):
    symbol: str
    ma5: List[Optional[float]] = []
    ma10: List[Optional[float]] = []
    ma20: List[Optional[float]] = []
    ma60: List[Optional[float]] = []
    rsi14: List[Optional[float]] = []
    macd: List[Optional[float]] = []
    macd_signal: List[Optional[float]] = []
    macd_hist: List[Optional[float]] = []
    boll_upper: List[Optional[float]] = []
    boll_middle: List[Optional[float]] = []
    boll_lower: List[Optional[float]] = []
    dates: List[str] = []
    closes: List[float] = []
    volumes: List[float] = []
