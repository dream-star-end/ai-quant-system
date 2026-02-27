"""告警模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum
import enum
from database import Base


class AlertType(str, enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    CHANGE_PCT = "change_pct"
    VOLUME_SPIKE = "volume_spike"
    STRATEGY_SIGNAL = "strategy_signal"
    RISK_WARNING = "risk_warning"
    DRAWDOWN = "drawdown"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_type = Column(Enum(AlertType), nullable=False)
    symbol = Column(String(30), nullable=True)
    condition_value = Column(Float, nullable=True)
    message = Column(String(500), nullable=False)
    is_triggered = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
