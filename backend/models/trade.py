"""交易记录模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
import enum
from database import Base


class TradeDirection(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    symbol = Column(String(30), nullable=False)
    direction = Column(Enum(TradeDirection), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    status = Column(Enum(TradeStatus), default=TradeStatus.FILLED)
    pnl = Column(Float, nullable=True)
    note = Column(String(500), default="")
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
