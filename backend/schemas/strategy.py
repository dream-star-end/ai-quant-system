"""策略相关模型"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class StrategyCreate(BaseModel):
    name: str
    description: str = ""
    strategy_type: str  # ma_cross, rsi, macd, bollinger, dual_thrust, grid, turtle, ai_prediction
    params: Dict[str, Any] = {}
    symbols: List[str] = []
    timeframe: str = "1d"


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = None
    status: Optional[str] = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    description: str
    strategy_type: str
    status: str
    params: dict
    symbols: list
    timeframe: str
    backtest_return: Optional[float] = None
    backtest_sharpe: Optional[float] = None
    backtest_max_drawdown: Optional[float] = None
    backtest_win_rate: Optional[float] = None
    backtest_trade_count: Optional[int] = None
    created_at: Optional[str] = None


class BacktestRequest(BaseModel):
    strategy_type: str
    params: Dict[str, Any] = {}
    symbol: str
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 1000000.0
    commission_rate: float = 0.001
    slippage: float = 0.001


class BacktestTradeRecord(BaseModel):
    date: str
    direction: str
    price: float
    quantity: float
    amount: float
    pnl: Optional[float] = None
    reason: str = ""


class BacktestResult(BaseModel):
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_duration: int = 0
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    equity_curve: List[Dict[str, Any]] = []
    trades: List[BacktestTradeRecord] = []
    monthly_returns: List[Dict[str, Any]] = []
    drawdown_curve: List[Dict[str, Any]] = []
