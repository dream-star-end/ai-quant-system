"""投资组合相关模型"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PortfolioCreate(BaseModel):
    name: str
    description: str = ""
    initial_capital: float = 1000000.0
    is_paper: bool = True


class PortfolioResponse(BaseModel):
    id: int
    name: str
    description: str
    initial_capital: float
    current_value: float
    cash_balance: float
    total_pnl: float
    total_pnl_pct: float
    max_drawdown: float
    is_paper: int
    positions: List[dict] = []
    created_at: Optional[str] = None


class TradeRequest(BaseModel):
    portfolio_id: int
    symbol: str
    direction: str  # buy / sell
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    note: str = ""


class TradeResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    direction: str
    quantity: float
    price: float
    total_amount: float
    commission: float
    status: str
    pnl: Optional[float] = None
    executed_at: Optional[str] = None


class PositionResponse(BaseModel):
    id: int
    symbol: str
    asset_type: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class AlertCreate(BaseModel):
    alert_type: str
    symbol: Optional[str] = None
    condition_value: Optional[float] = None
    message: str


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    symbol: Optional[str] = None
    condition_value: Optional[float] = None
    message: str
    is_triggered: bool
    is_active: bool
    triggered_at: Optional[str] = None
    created_at: Optional[str] = None
