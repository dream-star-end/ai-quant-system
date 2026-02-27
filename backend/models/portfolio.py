"""投资组合与持仓模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
import enum
from database import Base


class AssetType(str, enum.Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    INDEX = "index"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    initial_capital = Column(Float, nullable=False, default=1000000.0)
    current_value = Column(Float, default=1000000.0)
    cash_balance = Column(Float, default=1000000.0)
    total_pnl = Column(Float, default=0.0)
    total_pnl_pct = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    is_paper = Column(Integer, default=1)  # 1=模拟, 0=实盘
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(30), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    quantity = Column(Float, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0)
    current_price = Column(Float, default=0)
    market_value = Column(Float, default=0)
    unrealized_pnl = Column(Float, default=0)
    unrealized_pnl_pct = Column(Float, default=0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
