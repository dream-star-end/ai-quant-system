"""策略模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum
import enum
from database import Base


class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class StrategyType(str, enum.Enum):
    MA_CROSS = "ma_cross"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"
    DUAL_THRUST = "dual_thrust"
    GRID = "grid"
    TURTLE = "turtle"
    AI_PREDICTION = "ai_prediction"
    CUSTOM = "custom"


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000), default="")
    strategy_type = Column(Enum(StrategyType), nullable=False)
    status = Column(Enum(StrategyStatus), default=StrategyStatus.DRAFT)
    params = Column(JSON, default=dict)
    symbols = Column(JSON, default=list)
    timeframe = Column(String(10), default="1d")

    # 回测结果摘要
    backtest_return = Column(Float, nullable=True)
    backtest_sharpe = Column(Float, nullable=True)
    backtest_max_drawdown = Column(Float, nullable=True)
    backtest_win_rate = Column(Float, nullable=True)
    backtest_trade_count = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class StrategySignal(Base):
    __tablename__ = "strategy_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, index=True)
    symbol = Column(String(30), nullable=False)
    signal_type = Column(String(10), nullable=False)  # buy / sell / hold
    price = Column(Float, nullable=False)
    confidence = Column(Float, default=0.5)
    reason = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
