"""
加密货币交易所实盘适配器 — 基于 ccxt
支持: Binance, OKX, Huobi, Bybit, Gate 等
"""
import ccxt.async_support as ccxt_async
from typing import Optional, List, Dict, Any

from services.brokers.base import BaseBroker, OrderResult, BalanceInfo
from core.logger import logger

EXCHANGE_MAP = {
    "binance": ccxt_async.binance,
    "okx": ccxt_async.okx,
    "huobi": ccxt_async.huobi,
    "bybit": ccxt_async.bybit,
    "gate": ccxt_async.gateio,
}


class CryptoBroker(BaseBroker):
    broker_type = "crypto"
    display_name = "加密货币交易所"

    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        api_secret: str,
        passphrase: str = "",
        testnet: bool = False,
        extra_config: Dict[str, Any] = None,
    ):
        cls = EXCHANGE_MAP.get(exchange_id)
        if not cls:
            raise ValueError(f"不支持的交易所: {exchange_id}，支持: {list(EXCHANGE_MAP.keys())}")

        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
        if passphrase:
            config["password"] = passphrase
        if extra_config:
            config.update(extra_config)

        self._exchange: ccxt_async.Exchange = cls(config)
        self._exchange_id = exchange_id

        if testnet:
            self._exchange.set_sandbox_mode(True)

        self.display_name = f"{exchange_id.upper()} ({'测试网' if testnet else '主网'})"

    async def connect(self) -> bool:
        try:
            bal = await self._exchange.fetch_balance()
            logger.info(f"[{self.display_name}] 连接成功")
            return True
        except Exception as e:
            logger.error(f"[{self.display_name}] 连接失败: {e}")
            return False

    async def get_balance(self) -> BalanceInfo:
        try:
            bal = await self._exchange.fetch_balance()
            total = float(bal.get("total", {}).get("USDT", 0))
            free = float(bal.get("free", {}).get("USDT", 0))

            positions = []
            for coin, amount in bal.get("total", {}).items():
                amt = float(amount)
                if amt > 0 and coin != "USDT":
                    positions.append({
                        "symbol": f"{coin}/USDT",
                        "quantity": amt,
                        "asset": coin,
                    })

            return BalanceInfo(
                total_equity=total,
                available_balance=free,
                positions=positions,
                raw={"total": dict(bal.get("total", {})), "free": dict(bal.get("free", {}))},
            )
        except Exception as e:
            logger.error(f"[{self.display_name}] 查询余额失败: {e}")
            return BalanceInfo(raw={"error": str(e)})

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> OrderResult:
        try:
            params = {}
            if order_type == "market":
                order = await self._exchange.create_order(symbol, "market", side, quantity, None, params)
            elif order_type == "limit":
                if price is None:
                    return OrderResult(success=False, error="限价单必须指定价格")
                order = await self._exchange.create_order(symbol, "limit", side, quantity, price, params)
            else:
                return OrderResult(success=False, error=f"不支持的订单类型: {order_type}")

            filled_qty = float(order.get("filled", 0))
            avg_price = float(order.get("average", 0) or order.get("price", 0) or 0)
            fee = order.get("fee", {})
            commission = float(fee.get("cost", 0)) if fee else 0

            result = OrderResult(
                success=True,
                order_id=str(order.get("id", "")),
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=avg_price,
                filled_quantity=filled_qty,
                filled_price=avg_price,
                commission=commission,
                status=order.get("status", "open"),
                raw=order,
            )
            logger.info(f"[{self.display_name}] 下单成功: {side} {symbol} x{quantity} @{avg_price} (id={result.order_id})")
            return result

        except Exception as e:
            logger.error(f"[{self.display_name}] 下单失败: {e}")
            return OrderResult(success=False, symbol=symbol, side=side, error=str(e))

    async def cancel_order(self, order_id: str, symbol: str = "") -> bool:
        try:
            await self._exchange.cancel_order(order_id, symbol or None)
            logger.info(f"[{self.display_name}] 撤单成功: {order_id}")
            return True
        except Exception as e:
            logger.error(f"[{self.display_name}] 撤单失败: {e}")
            return False

    async def get_order(self, order_id: str, symbol: str = "") -> OrderResult:
        try:
            order = await self._exchange.fetch_order(order_id, symbol or None)
            return OrderResult(
                success=True,
                order_id=str(order.get("id", "")),
                symbol=order.get("symbol", ""),
                side=order.get("side", ""),
                quantity=float(order.get("amount", 0)),
                filled_quantity=float(order.get("filled", 0)),
                filled_price=float(order.get("average", 0) or 0),
                status=order.get("status", ""),
                raw=order,
            )
        except Exception as e:
            return OrderResult(success=False, error=str(e))

    async def get_open_orders(self, symbol: str = "") -> List[OrderResult]:
        try:
            orders = await self._exchange.fetch_open_orders(symbol or None)
            return [
                OrderResult(
                    success=True,
                    order_id=str(o.get("id", "")),
                    symbol=o.get("symbol", ""),
                    side=o.get("side", ""),
                    quantity=float(o.get("amount", 0)),
                    filled_quantity=float(o.get("filled", 0)),
                    price=float(o.get("price", 0) or 0),
                    status=o.get("status", ""),
                )
                for o in orders
            ]
        except Exception as e:
            logger.error(f"[{self.display_name}] 查询未成交订单失败: {e}")
            return []

    async def close(self):
        try:
            await self._exchange.close()
        except Exception:
            pass
