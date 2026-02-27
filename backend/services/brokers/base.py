"""
Broker 抽象基类 — 所有交易所/券商适配器的统一接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class OrderResult:
    success: bool
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = "market"
    quantity: float = 0
    price: float = 0
    filled_quantity: float = 0
    filled_price: float = 0
    commission: float = 0
    status: str = "pending"
    raw: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class BalanceInfo:
    total_equity: float = 0
    available_balance: float = 0
    positions: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


class BaseBroker(ABC):
    """所有券商/交易所适配器的抽象基类"""

    broker_type: str = "base"
    display_name: str = "Base Broker"

    @abstractmethod
    async def connect(self) -> bool:
        """测试连接"""
        ...

    @abstractmethod
    async def get_balance(self) -> BalanceInfo:
        """查询账户余额和持仓"""
        ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> OrderResult:
        """下单"""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str = "") -> bool:
        """撤单"""
        ...

    @abstractmethod
    async def get_order(self, order_id: str, symbol: str = "") -> OrderResult:
        """查询订单状态"""
        ...

    @abstractmethod
    async def get_open_orders(self, symbol: str = "") -> List[OrderResult]:
        """查询未成交订单"""
        ...

    async def close(self):
        """关闭连接"""
        pass
