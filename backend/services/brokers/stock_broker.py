"""
A股券商适配器 — 预留接口

支持方案 (需用户自行安装对应 SDK):
1. easytrader — 基于同花顺/通达信客户端，模拟键鼠操作
2. 华鑫证券奇点 — 官方量化 API
3. 中泰证券 XTP — 官方量化 API
4. 自定义 HTTP API — 对接用户自建的委托网关

当前实现: Stub (存根)，仅提供接口定义。
用户可继承 BaseBroker 实现自己的券商对接。
"""
from typing import Optional, List, Dict, Any
from services.brokers.base import BaseBroker, OrderResult, BalanceInfo
from core.logger import logger


class StockBrokerStub(BaseBroker):
    """
    A股券商存根适配器
    展示接口规范，实际使用时需要替换为具体实现
    """
    broker_type = "stock"
    display_name = "A股券商 (待对接)"

    def __init__(self, broker_id: str = "stock_sim", **kwargs):
        self._broker_id = broker_id
        self._config = kwargs

    async def connect(self) -> bool:
        logger.warning(f"[A股券商] {self._broker_id} 尚未实现实盘对接，当前为模拟模式")
        return True

    async def get_balance(self) -> BalanceInfo:
        return BalanceInfo(
            total_equity=0,
            available_balance=0,
            positions=[],
            raw={"message": "A股券商接口待对接，请参考文档实现 StockBroker"},
        )

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> OrderResult:
        return OrderResult(
            success=False,
            symbol=symbol,
            side=side,
            error="A股券商接口待对接。请参考 services/brokers/stock_broker.py 实现具体券商适配器。"
                  "\n支持方案: easytrader(同花顺/通达信), 华鑫证券奇点, 中泰XTP, 自定义HTTP网关",
        )

    async def cancel_order(self, order_id: str, symbol: str = "") -> bool:
        return False

    async def get_order(self, order_id: str, symbol: str = "") -> OrderResult:
        return OrderResult(success=False, error="A股券商接口待对接")

    async def get_open_orders(self, symbol: str = "") -> List[OrderResult]:
        return []


# ================================================================
# 下面是一个 easytrader 适配器的示例框架（需安装 easytrader）
# pip install easytrader
# ================================================================
#
# class EasyTraderBroker(BaseBroker):
#     broker_type = "stock"
#     display_name = "A股券商 (easytrader)"
#
#     def __init__(self, broker: str = "ths", **kwargs):
#         """
#         broker: "ths" (同花顺) / "ht" (海通) / "gj" (国金) / "yh" (银河)
#         """
#         import easytrader
#         self._trader = easytrader.use(broker)
#         self._config = kwargs
#
#     async def connect(self) -> bool:
#         try:
#             self._trader.connect(self._config.get("exe_path", ""))
#             return True
#         except Exception as e:
#             return False
#
#     async def get_balance(self) -> BalanceInfo:
#         bal = self._trader.balance
#         positions = self._trader.position
#         return BalanceInfo(
#             total_equity=bal[0].get("总资产", 0),
#             available_balance=bal[0].get("可用金额", 0),
#             positions=[{
#                 "symbol": p.get("证券代码"),
#                 "name": p.get("证券名称"),
#                 "quantity": p.get("持仓量"),
#                 "avg_cost": p.get("成本价"),
#                 "market_value": p.get("市值"),
#                 "pnl": p.get("盈亏"),
#             } for p in positions],
#         )
#
#     async def place_order(self, symbol, side, quantity, order_type="market", price=None):
#         try:
#             if side == "buy":
#                 result = self._trader.buy(symbol, price=price or 0, amount=quantity)
#             else:
#                 result = self._trader.sell(symbol, price=price or 0, amount=quantity)
#             return OrderResult(success=True, order_id=str(result.get("entrust_no", "")),
#                                symbol=symbol, side=side, quantity=quantity, price=price or 0)
#         except Exception as e:
#             return OrderResult(success=False, error=str(e))
#
#     async def cancel_order(self, order_id, symbol=""):
#         try:
#             self._trader.cancel_entrust(order_id)
#             return True
#         except:
#             return False
#
#     async def get_order(self, order_id, symbol=""):
#         return OrderResult(success=False, error="easytrader 不支持单笔订单查询")
#
#     async def get_open_orders(self, symbol=""):
#         return []
