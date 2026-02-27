"""
同花顺交易网关 (THS Gateway)

在 Windows 机器上运行此脚本，为远程部署的 AI Quant System 后端提供 HTTP 交易接口。

使用方法:
  1. 安装依赖:  pip install easytrader flask
  2. 打开同花顺独立下单程序并登录
  3. 运行本脚本: python ths_gateway.py
  4. 在 AI Quant System 中配置网关地址: http://<你的IP>:19880

安全提醒:
  - 默认仅监听 127.0.0.1 (本机)
  - 如需远程访问，改为 0.0.0.0 并务必配置防火墙和 API 密钥
  - 建议在内网 / VPN 环境下使用
"""

import os
import sys
import json
import logging
from datetime import datetime
from functools import wraps

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("请安装 Flask: pip install flask")
    sys.exit(1)

try:
    import easytrader
except ImportError:
    print("请安装 easytrader: pip install easytrader")
    sys.exit(1)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger("ths_gateway")

# ---- 配置 ----
HOST = os.environ.get("THS_HOST", "127.0.0.1")
PORT = int(os.environ.get("THS_PORT", "19880"))
API_KEY = os.environ.get("THS_API_KEY", "")
EXE_PATH = os.environ.get("THS_EXE_PATH", "")

trader = None


def init_trader():
    global trader
    log.info("正在连接同花顺客户端...")
    trader = easytrader.use("ths")
    if EXE_PATH:
        trader.connect(EXE_PATH)
    else:
        trader.connect()
    bal = trader.balance
    log.info(f"连接成功! 总资产: {bal[0].get('总资产', 'N/A') if bal else 'N/A'}")


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if API_KEY:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {API_KEY}":
                return jsonify({"success": False, "message": "认证失败"}), 401
        return f(*args, **kwargs)
    return wrapper


def ok(data=None, message=""):
    return jsonify({"success": True, "data": data, "message": message})


def fail(message):
    return jsonify({"success": False, "message": message})


# ---- 路由 ----

@app.route("/ping")
def ping():
    return ok({"status": "running", "time": datetime.now().isoformat()})


@app.route("/balance")
@require_auth
def balance():
    try:
        bal_list = trader.balance
        pos_list = trader.position

        bal = bal_list[0] if bal_list else {}
        total = float(bal.get("总资产", bal.get("资金余额", 0)))
        available = float(bal.get("可用金额", bal.get("可用资金", 0)))
        frozen = float(bal.get("冻结资金", 0))

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

        return ok({
            "total_equity": total,
            "available_balance": available,
            "frozen": frozen,
            "positions": positions,
            "raw_balance": bal,
        })
    except Exception as e:
        log.error(f"查询余额失败: {e}")
        return fail(str(e))


@app.route("/order", methods=["POST"])
@require_auth
def order():
    data = request.json
    symbol = data.get("symbol", "")
    side = data.get("side", "")
    quantity = int(data.get("quantity", 0))
    price = data.get("price")

    if not symbol or not side or quantity <= 0:
        return fail("参数不完整: symbol, side, quantity 必填")

    if not price:
        return fail("A股必须指定价格 (限价单)")

    if quantity % 100 != 0:
        return fail(f"数量须为100的整数倍，当前: {quantity}")

    try:
        if side == "buy":
            result = trader.buy(symbol, price=float(price), amount=quantity)
        elif side == "sell":
            result = trader.sell(symbol, price=float(price), amount=quantity)
        else:
            return fail(f"不支持的方向: {side}")

        entrust_no = ""
        if isinstance(result, dict):
            entrust_no = str(result.get("entrust_no", result.get("委托编号", "")))
        elif isinstance(result, list) and result:
            entrust_no = str(result[0].get("entrust_no", result[0].get("委托编号", "")))

        log.info(f"下单成功: {side} {symbol} x{quantity} @{price} -> 委托号 {entrust_no}")
        return ok({"entrust_no": entrust_no, "raw": result if isinstance(result, dict) else str(result)})
    except Exception as e:
        log.error(f"下单失败: {e}")
        return fail(str(e))


@app.route("/cancel", methods=["POST"])
@require_auth
def cancel():
    data = request.json
    entrust_no = data.get("entrust_no", "")
    if not entrust_no:
        return fail("entrust_no 必填")

    try:
        trader.cancel_entrust(entrust_no)
        log.info(f"撤单成功: {entrust_no}")
        return ok(message="撤单成功")
    except Exception as e:
        log.error(f"撤单失败: {e}")
        return fail(str(e))


@app.route("/entrusts")
@require_auth
def entrusts():
    try:
        data = trader.today_entrusts
        result = []
        for e in data:
            result.append({
                "entrust_no": str(e.get("委托编号", e.get("合同编号", ""))),
                "symbol": str(e.get("证券代码", "")),
                "name": e.get("证券名称", ""),
                "direction": e.get("操作", e.get("买卖标志", "")),
                "price": float(e.get("委托价格", 0)),
                "quantity": float(e.get("委托数量", 0)),
                "filled_quantity": float(e.get("成交数量", 0)),
                "filled_price": float(e.get("成交均价", e.get("成交价格", 0))),
                "status": e.get("备注", e.get("状态说明", "")),
                "time": e.get("委托时间", ""),
            })
        return ok(result)
    except Exception as e:
        log.error(f"查询委托失败: {e}")
        return fail(str(e))


@app.route("/trades")
@require_auth
def trades():
    try:
        data = trader.today_trades
        result = []
        for t in data:
            result.append({
                "symbol": str(t.get("证券代码", "")),
                "name": t.get("证券名称", ""),
                "direction": t.get("操作", t.get("买卖标志", "")),
                "price": float(t.get("成交价格", t.get("成交均价", 0))),
                "quantity": float(t.get("成交数量", 0)),
                "amount": float(t.get("成交金额", 0)),
                "time": t.get("成交时间", ""),
            })
        return ok(result)
    except Exception as e:
        return fail(str(e))


if __name__ == "__main__":
    print("=" * 60)
    print("  同花顺交易网关 (THS Gateway)")
    print("=" * 60)
    print(f"  监听地址: {HOST}:{PORT}")
    print(f"  API密钥:  {'已设置' if API_KEY else '未设置 (不鉴权)'}")
    print(f"  客户端路径: {EXE_PATH or '自动检测'}")
    print()
    print("  端点:")
    print("    GET  /ping     - 健康检查")
    print("    GET  /balance  - 查询余额持仓")
    print("    POST /order    - 下单 {symbol, side, quantity, price}")
    print("    POST /cancel   - 撤单 {entrust_no}")
    print("    GET  /entrusts - 今日委托")
    print("    GET  /trades   - 今日成交")
    print("=" * 60)

    init_trader()
    app.run(host=HOST, port=PORT, debug=False)
