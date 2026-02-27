"""
A股券商适配器

同花顺适配器 (THSBroker):
  模式 1 — local: 使用 easytrader 直连本机同花顺客户端 (需 Windows + 客户端已登录)
  模式 2 — gateway: 通过 HTTP 网关中转 (适用于远程部署，用户在本机运行网关程序)

华鑫证券 / 中泰 XTP 等: 预留接口 (StockBrokerStub)
"""
import asyncio
import json
from typing import Optional, List, Dict, Any
from functools import partial

import httpx

from services.brokers.base import BaseBroker, OrderResult, BalanceInfo
from core.logger import logger


# ================================================================
# 同花顺适配器
# ================================================================

class THSBroker(BaseBroker):
    """
    同花顺交易适配器

    支持两种模式:
    - local:   通过 easytrader 直连本机运行的同花顺客户端
    - gateway: 通过 HTTP API 网关中转 (用户在 Windows 机器上运行 gateway 程序)

    local 模式需要:
      1. Windows 操作系统
      2. 安装 easytrader: pip install easytrader
      3. 同花顺独立下单程序已登录

    gateway 模式需要:
      1. 用户在 Windows 机器上运行 ths_gateway.py (见 tools/ths_gateway.py)
      2. 配置 gateway_url 指向该机器
    """

    broker_type = "stock_ths"
    display_name = "同花顺"

    def __init__(
        self,
        mode: str = "gateway",
        exe_path: str = "",
        gateway_url: str = "http://127.0.0.1:19880",
        **kwargs,
    ):
        self._mode = mode
        self._exe_path = exe_path
        self._gateway_url = gateway_url.rstrip("/")
        self._trader = None
        self._loop = asyncio.get_event_loop()

    # ---- 连接 ----

    async def connect(self) -> bool:
        if self._mode == "local":
            return await self._connect_local()
        return await self._connect_gateway()

    async def _connect_local(self) -> bool:
        try:
            import easytrader
        except ImportError:
            logger.error("[同花顺-local] 未安装 easytrader，请执行: pip install easytrader")
            return False

        def _do_connect():
            trader = easytrader.use("ths")
            if self._exe_path:
                trader.connect(self._exe_path)
            else:
                trader.connect()
            _ = trader.balance
            return trader

        try:
            self._trader = await asyncio.get_event_loop().run_in_executor(None, _do_connect)
            logger.info("[同花顺-local] 连接成功")
            return True
        except Exception as e:
            logger.error(f"[同花顺-local] 连接失败: {e}")
            return False

    async def _connect_gateway(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._gateway_url}/ping")
                if resp.status_code == 200:
                    logger.info(f"[同花顺-gateway] 连接成功: {self._gateway_url}")
                    return True
                logger.error(f"[同花顺-gateway] 连接失败: HTTP {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"[同花顺-gateway] 连接失败: {e}")
            return False

    # ---- 查询余额 ----

    async def get_balance(self) -> BalanceInfo:
        if self._mode == "local":
            return await self._balance_local()
        return await self._balance_gateway()

    async def _balance_local(self) -> BalanceInfo:
        if not self._trader:
            return BalanceInfo(raw={"error": "未连接"})

        def _query():
            bal = self._trader.balance
            pos = self._trader.position
            return bal, pos

        try:
            bal_list, pos_list = await asyncio.get_event_loop().run_in_executor(None, _query)
            bal = bal_list[0] if bal_list else {}

            total = float(bal.get("总资产", bal.get("资金余额", 0)))
            available = float(bal.get("可用金额", bal.get("可用资金", 0)))

            positions = []
            for p in pos_list:
                positions.append({
                    "symbol": str(p.get("证券代码", "")),
                    "name": p.get("证券名称", ""),
                    "quantity": float(p.get("股票余额", p.get("当前持仓", p.get("持仓量", 0)))),
                    "available_qty": float(p.get("可用余额", p.get("可卖数量", 0))),
                    "avg_cost": float(p.get("成本价", p.get("买入均价", 0))),
                    "current_price": float(p.get("当前价", p.get("最新价", 0))),
                    "market_value": float(p.get("市值", p.get("最新市值", 0))),
                    "pnl": float(p.get("盈亏", p.get("浮动盈亏", 0))),
                    "pnl_pct": float(p.get("盈亏比例(%)", p.get("盈亏比例", 0))),
                })

            return BalanceInfo(total_equity=total, available_balance=available, positions=positions, raw=bal)
        except Exception as e:
            logger.error(f"[同花顺-local] 查询余额失败: {e}")
            return BalanceInfo(raw={"error": str(e)})

    async def _balance_gateway(self) -> BalanceInfo:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{self._gateway_url}/balance")
                data = resp.json()

                if not data.get("success"):
                    return BalanceInfo(raw=data)

                d = data.get("data", {})
                return BalanceInfo(
                    total_equity=d.get("total_equity", 0),
                    available_balance=d.get("available_balance", 0),
                    positions=d.get("positions", []),
                    raw=d,
                )
        except Exception as e:
            logger.error(f"[同花顺-gateway] 查询余额失败: {e}")
            return BalanceInfo(raw={"error": str(e)})

    # ---- 下单 ----

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "limit",
        price: Optional[float] = None,
    ) -> OrderResult:
        if self._mode == "local":
            return await self._order_local(symbol, side, quantity, price)
        return await self._order_gateway(symbol, side, quantity, order_type, price)

    async def _order_local(self, symbol, side, quantity, price) -> OrderResult:
        if not self._trader:
            return OrderResult(success=False, error="未连接同花顺客户端")

        if not price:
            return OrderResult(success=False, symbol=symbol, side=side, error="A股必须指定价格(限价单)")

        qty = int(quantity)
        if qty <= 0 or qty % 100 != 0:
            return OrderResult(success=False, symbol=symbol, side=side, error=f"数量须为100的整数倍，当前: {qty}")

        def _do_order():
            if side == "buy":
                return self._trader.buy(symbol, price=price, amount=qty)
            else:
                return self._trader.sell(symbol, price=price, amount=qty)

        try:
            result = await asyncio.get_event_loop().run_in_executor(None, _do_order)

            entrust_no = ""
            if isinstance(result, dict):
                entrust_no = str(result.get("entrust_no", result.get("委托编号", "")))
            elif isinstance(result, list) and result:
                entrust_no = str(result[0].get("entrust_no", result[0].get("委托编号", "")))

            logger.info(f"[同花顺-local] 下单成功: {side} {symbol} x{qty} @{price} -> 委托号{entrust_no}")
            return OrderResult(
                success=True,
                order_id=entrust_no,
                symbol=symbol,
                side=side,
                order_type="limit",
                quantity=qty,
                price=price,
                status="submitted",
                raw=result if isinstance(result, dict) else {"result": result},
            )
        except Exception as e:
            logger.error(f"[同花顺-local] 下单失败: {e}")
            return OrderResult(success=False, symbol=symbol, side=side, error=str(e))

    async def _order_gateway(self, symbol, side, quantity, order_type, price) -> OrderResult:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(f"{self._gateway_url}/order", json={
                    "symbol": symbol,
                    "side": side,
                    "quantity": int(quantity),
                    "order_type": order_type,
                    "price": price,
                })
                data = resp.json()

                if data.get("success"):
                    d = data.get("data", {})
                    return OrderResult(
                        success=True,
                        order_id=str(d.get("entrust_no", "")),
                        symbol=symbol,
                        side=side,
                        quantity=int(quantity),
                        price=price or 0,
                        status="submitted",
                        raw=d,
                    )
                return OrderResult(success=False, symbol=symbol, side=side, error=data.get("message", "网关下单失败"))
        except Exception as e:
            return OrderResult(success=False, symbol=symbol, side=side, error=f"网关请求失败: {e}")

    # ---- 撤单 ----

    async def cancel_order(self, order_id: str, symbol: str = "") -> bool:
        if self._mode == "local":
            return await self._cancel_local(order_id)
        return await self._cancel_gateway(order_id)

    async def _cancel_local(self, order_id: str) -> bool:
        if not self._trader:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, partial(self._trader.cancel_entrust, order_id)
            )
            logger.info(f"[同花顺-local] 撤单成功: {order_id}")
            return True
        except Exception as e:
            logger.error(f"[同花顺-local] 撤单失败: {e}")
            return False

    async def _cancel_gateway(self, order_id: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{self._gateway_url}/cancel", json={"entrust_no": order_id})
                return resp.json().get("success", False)
        except Exception:
            return False

    # ---- 查询订单 ----

    async def get_order(self, order_id: str, symbol: str = "") -> OrderResult:
        entrusts = await self._get_today_entrusts()
        for e in entrusts:
            if str(e.get("entrust_no", "")) == order_id:
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    symbol=e.get("symbol", symbol),
                    side="buy" if "买" in e.get("操作", e.get("direction", "")) else "sell",
                    quantity=float(e.get("委托数量", e.get("quantity", 0))),
                    filled_quantity=float(e.get("成交数量", e.get("filled_quantity", 0))),
                    filled_price=float(e.get("成交均价", e.get("filled_price", 0))),
                    status=e.get("status", e.get("备注", "unknown")),
                    raw=e,
                )
        return OrderResult(success=False, error=f"未找到委托号 {order_id}")

    async def get_open_orders(self, symbol: str = "") -> List[OrderResult]:
        entrusts = await self._get_today_entrusts()
        open_orders = []
        for e in entrusts:
            status = str(e.get("备注", e.get("status", "")))
            if "已成" in status or "已撤" in status or "废单" in status:
                continue
            sym = str(e.get("证券代码", e.get("symbol", "")))
            if symbol and sym != symbol:
                continue
            open_orders.append(OrderResult(
                success=True,
                order_id=str(e.get("委托编号", e.get("entrust_no", ""))),
                symbol=sym,
                side="buy" if "买" in str(e.get("操作", e.get("direction", ""))) else "sell",
                quantity=float(e.get("委托数量", e.get("quantity", 0))),
                price=float(e.get("委托价格", e.get("price", 0))),
                filled_quantity=float(e.get("成交数量", e.get("filled_quantity", 0))),
                status=status,
                raw=e,
            ))
        return open_orders

    async def _get_today_entrusts(self) -> list:
        if self._mode == "local" and self._trader:
            try:
                return await asyncio.get_event_loop().run_in_executor(None, self._trader.today_entrusts)
            except Exception:
                return []
        elif self._mode == "gateway":
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(f"{self._gateway_url}/entrusts")
                    data = resp.json()
                    return data.get("data", [])
            except Exception:
                return []
        return []


# ================================================================
# A股券商存根 (其它券商预留)
# ================================================================

class StockBrokerStub(BaseBroker):
    broker_type = "stock"
    display_name = "A股券商 (待对接)"

    def __init__(self, broker_id: str = "stock_sim", **kwargs):
        self._broker_id = broker_id

    async def connect(self) -> bool:
        logger.warning(f"[A股券商] {self._broker_id} 尚未实现")
        return False

    async def get_balance(self) -> BalanceInfo:
        return BalanceInfo(raw={"error": "券商接口待实现"})

    async def place_order(self, symbol, side, quantity, order_type="limit", price=None) -> OrderResult:
        return OrderResult(success=False, error=f"{self._broker_id} 接口待实现")

    async def cancel_order(self, order_id, symbol="") -> bool:
        return False

    async def get_order(self, order_id, symbol="") -> OrderResult:
        return OrderResult(success=False, error="接口待实现")

    async def get_open_orders(self, symbol="") -> List[OrderResult]:
        return []
