"""
AI Agent 自主交易服务

核心流程:
1. 获取市场数据 + 技术指标
2. 调用 DeepSeek 进行分析并生成交易决策
3. 风控检查
4. 根据模式执行:
   - autonomous: 自动执行
   - approval: 等待用户审批
   - observe: 仅记录不执行
5. 记录决策日志
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from config import get_settings
from core.logger import logger
from database import get_supabase
from services.market_data import (
    get_stock_quote, get_crypto_price,
    get_stock_history, get_crypto_history,
    calculate_indicators,
)
from services.ai_service import predict_trend
from services.risk_manager import check_position_size, calculate_stop_loss, calculate_take_profit
from services import deepseek_service

settings = get_settings()

AGENT_DECISION_PROMPT = """你是一个 AI 量化交易 Agent。你正在管理用户的投资组合，需要基于当前市场数据做出交易决策。

## 当前持仓
{positions}

## 组合概况
- 总资产: {portfolio_value}
- 现金余额: {cash_balance}
- 总收益: {total_pnl} ({total_pnl_pct}%)

## 标的: {symbol}
## 当前行情
{market_data}

## 技术指标分析
{tech_analysis}

## 风控参数
- 单笔最大仓位: {max_position_pct}%
- 止损线: {stop_loss_pct}%
- 止盈线: {take_profit_pct}%
- 风险偏好: {risk_tolerance}
- 策略倾向: {strategy_preference}

## 今日已交易次数: {trades_today}/{max_trades_per_day}

请根据以上信息做出决策。你 **必须** 以如下 JSON 格式回复（不要输出其他内容）:

```json
{{
  "action": "buy" | "sell" | "hold",
  "symbol": "{symbol}",
  "confidence": 0.0-1.0,
  "quantity": 数量(hold时为0),
  "reason": "中文决策理由，2-3句话",
  "risk_note": "风险提示，1句话"
}}
```

决策原则:
1. 没有明确信号时，选择 hold
2. 置信度低于 0.6 时，优先 hold
3. 买入数量不超过现金余额的 {max_position_pct}%
4. 已有持仓亏损超过止损线时必须卖出
5. 已有持仓盈利超过止盈线时考虑止盈
6. 单日交易次数不超过限额
7. 风险偏好 conservative: 少交易多观望; aggressive: 积极交易; balanced: 均衡"""


async def run_agent_check(session_id: int) -> List[Dict[str, Any]]:
    """
    执行一次 Agent 检查循环，返回所有决策
    """
    sb = get_supabase()

    session = sb.table("agent_sessions").select("*").eq("id", session_id).single().execute()
    if not session.data:
        return [{"error": "会话不存在"}]

    s = session.data
    if s["status"] != "running":
        return [{"error": f"会话状态为 {s['status']}，非运行中"}]

    if not deepseek_service.is_deepseek_configured():
        return [{"error": "未配置 DEEPSEEK_API_KEY"}]

    # 获取组合信息
    portfolio = sb.table("portfolios").select("*").eq("id", s["portfolio_id"]).single().execute()
    if not portfolio.data:
        return [{"error": "组合不存在"}]
    pf = portfolio.data

    positions = sb.table("positions").select("*").eq("portfolio_id", pf["id"]).execute()
    pos_list = positions.data or []

    # 今日交易数
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_trades = sb.table("agent_decisions").select("id", count="exact").eq("session_id", session_id).gte("created_at", today).neq("action", "hold").execute()
    trades_today = len(today_trades.data) if today_trades.data else 0

    symbols = s.get("symbols") or []
    if not symbols:
        return [{"error": "未配置监控标的"}]

    decisions = []

    for symbol in symbols:
        try:
            decision = await _analyze_and_decide(
                symbol=symbol,
                session=s,
                portfolio=pf,
                positions=pos_list,
                trades_today=trades_today,
            )
            if decision:
                decisions.append(decision)
                if decision.get("action") != "hold":
                    trades_today += 1
        except Exception as e:
            logger.error(f"Agent 分析 {symbol} 失败: {e}")
            decisions.append({
                "symbol": symbol,
                "action": "hold",
                "reason": f"分析异常: {str(e)}",
                "confidence": 0,
                "error": True,
            })

    # 更新会话
    sb.table("agent_sessions").update({
        "last_check_at": datetime.now(timezone.utc).isoformat(),
        "total_decisions": (s.get("total_decisions") or 0) + len(decisions),
    }).eq("id", session_id).execute()

    return decisions


async def _analyze_and_decide(
    symbol: str,
    session: dict,
    portfolio: dict,
    positions: list,
    trades_today: int,
) -> Dict[str, Any]:
    """对单个标的进行分析并决策"""
    sb = get_supabase()
    is_crypto = "/" in symbol

    # 1. 获取行情
    if is_crypto:
        quote = get_crypto_price(symbol)
        df = get_crypto_history(symbol, "1d", 100)
    else:
        quote = get_stock_quote(symbol)
        df = get_stock_history(symbol, "6mo")

    if "error" in quote or df.empty:
        return {"symbol": symbol, "action": "hold", "reason": "无法获取行情", "confidence": 0}

    price = quote.get("price", 0)
    if price <= 0:
        return {"symbol": symbol, "action": "hold", "reason": "价格异常", "confidence": 0}

    # 2. 技术指标
    indicators = calculate_indicators(df)
    trend = predict_trend(df)

    # 3. 检查止损/止盈
    current_pos = next((p for p in positions if p["symbol"] == symbol), None)
    forced_action = _check_stop_loss_take_profit(current_pos, price, session)
    if forced_action:
        forced_action["market_snapshot"] = _compact_snapshot(quote, trend)
        return await _save_decision(sb, session, forced_action)

    # 4. 调用 DeepSeek 决策
    pos_desc = "无持仓"
    if positions:
        pos_desc = "\n".join([
            f"- {p['symbol']}: {p['quantity']}股, 成本{p['avg_cost']:.2f}, 现价{p.get('current_price', 0):.2f}, 浮盈{p.get('unrealized_pnl', 0):.2f}"
            for p in positions
        ])

    market_desc = (
        f"价格: {price}, 涨跌幅: {quote.get('change_pct', 0):.2f}%, "
        f"成交量: {quote.get('volume', 'N/A')}"
    )

    tech_desc = f"趋势: {trend.get('trend', 'N/A')}, 信号: {trend.get('signal', 'N/A')}, 置信度: {trend.get('confidence', 0):.0f}%"
    for sig in trend.get("signals", []):
        tech_desc += f"\n  - {sig['name']} ({sig['type']})"

    prompt = AGENT_DECISION_PROMPT.format(
        symbol=symbol,
        positions=pos_desc,
        portfolio_value=f"{portfolio['current_value']:.0f}",
        cash_balance=f"{portfolio['cash_balance']:.0f}",
        total_pnl=f"{portfolio['total_pnl']:.0f}",
        total_pnl_pct=f"{portfolio['total_pnl_pct']:.2f}",
        market_data=market_desc,
        tech_analysis=tech_desc,
        max_position_pct=session.get("max_position_pct", 0.15) * 100,
        stop_loss_pct=session.get("stop_loss_pct", 0.05) * 100,
        take_profit_pct=session.get("take_profit_pct", 0.15) * 100,
        risk_tolerance=session.get("risk_tolerance", "medium"),
        strategy_preference=session.get("strategy_preference", "balanced"),
        trades_today=trades_today,
        max_trades_per_day=session.get("max_trades_per_day", 5),
    )

    try:
        messages = [
            {"role": "system", "content": "你是一个专业的 AI 量化交易 Agent。严格按要求的 JSON 格式输出决策。"},
            {"role": "user", "content": prompt},
        ]
        raw = await deepseek_service._call_deepseek(messages, temperature=0.1, max_tokens=500)

        # 解析 JSON
        decision = _parse_decision(raw, symbol)
    except Exception as e:
        logger.error(f"Agent DeepSeek 决策失败 {symbol}: {e}")
        decision = {
            "action": "hold",
            "symbol": symbol,
            "confidence": 0,
            "quantity": 0,
            "reason": f"AI 决策异常: {str(e)}",
            "risk_note": "系统异常，暂停操作",
        }

    # 5. 风控二次校验
    decision = _risk_check(decision, portfolio, session, current_pos, price)

    # 6. 保存决策
    decision["price"] = price
    decision["market_snapshot"] = _compact_snapshot(quote, trend)
    decision["ai_analysis"] = raw if "raw" in dir() else ""

    saved = await _save_decision(sb, session, decision)

    # 7. autonomous 模式自动执行
    if session["mode"] == "autonomous" and saved.get("action") in ("buy", "sell") and saved.get("status") == "pending":
        saved = await execute_decision(saved["id"])

    return saved


def _check_stop_loss_take_profit(position, price, session):
    """检查是否触发止损/止盈"""
    if not position or position["quantity"] <= 0:
        return None

    avg_cost = position["avg_cost"]
    if avg_cost <= 0:
        return None

    pnl_pct = (price - avg_cost) / avg_cost
    sl = session.get("stop_loss_pct", 0.05)
    tp = session.get("take_profit_pct", 0.15)

    if pnl_pct <= -sl:
        return {
            "action": "stop_loss",
            "symbol": position["symbol"],
            "confidence": 0.95,
            "quantity": position["quantity"],
            "reason": f"触发止损: 亏损 {pnl_pct*100:.1f}% 超过止损线 {sl*100:.0f}%，强制平仓",
            "risk_note": "止损保护触发",
            "price": price,
            "status": "pending",
        }

    if pnl_pct >= tp:
        return {
            "action": "take_profit",
            "symbol": position["symbol"],
            "confidence": 0.85,
            "quantity": position["quantity"],
            "reason": f"触发止盈: 盈利 {pnl_pct*100:.1f}% 达到止盈线 {tp*100:.0f}%，建议获利了结",
            "risk_note": "止盈信号",
            "price": price,
            "status": "pending",
        }

    return None


def _parse_decision(raw: str, symbol: str) -> dict:
    """从 DeepSeek 回复中解析 JSON 决策"""
    text = raw.strip()
    # 提取 JSON 块
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        d = json.loads(text)
        return {
            "action": d.get("action", "hold"),
            "symbol": d.get("symbol", symbol),
            "confidence": float(d.get("confidence", 0.5)),
            "quantity": int(d.get("quantity", 0)),
            "reason": d.get("reason", ""),
            "risk_note": d.get("risk_note", ""),
        }
    except json.JSONDecodeError:
        return {
            "action": "hold",
            "symbol": symbol,
            "confidence": 0.3,
            "quantity": 0,
            "reason": f"AI 回复解析失败，原始内容: {raw[:200]}",
            "risk_note": "JSON 解析失败",
        }


def _risk_check(decision: dict, portfolio: dict, session: dict, position, price: float) -> dict:
    """风控二次校验"""
    action = decision["action"]
    qty = decision.get("quantity", 0)

    if action == "buy":
        max_pct = session.get("max_position_pct", 0.15)
        max_amount = portfolio["current_value"] * max_pct
        amount = price * qty

        if amount > max_amount:
            qty = int(max_amount / price)
            decision["quantity"] = qty
            decision["reason"] += f" (风控调整数量至{qty})"

        if price * qty > portfolio["cash_balance"] * 0.95:
            qty = int(portfolio["cash_balance"] * 0.95 / price)
            decision["quantity"] = qty
            if qty <= 0:
                decision["action"] = "hold"
                decision["reason"] = "现金不足，无法买入"

    elif action == "sell":
        if not position or position["quantity"] <= 0:
            decision["action"] = "hold"
            decision["reason"] = "无持仓可卖出"
        elif qty > position["quantity"]:
            decision["quantity"] = position["quantity"]

    return decision


def _compact_snapshot(quote: dict, trend: dict) -> dict:
    """生成紧凑的市场快照"""
    return {
        "price": quote.get("price"),
        "change_pct": quote.get("change_pct"),
        "volume": quote.get("volume"),
        "trend": trend.get("trend"),
        "signal": trend.get("signal"),
        "confidence": trend.get("confidence"),
        "bull_score": trend.get("bull_score"),
        "bear_score": trend.get("bear_score"),
    }


async def _save_decision(sb, session, decision: dict) -> dict:
    """保存决策到数据库"""
    action = decision["action"]
    if action in ("stop_loss", "take_profit"):
        db_action = "sell"
    else:
        db_action = action

    status = "pending"
    if action == "hold":
        status = "executed"
    elif session["mode"] == "observe":
        status = "executed"

    qty = decision.get("quantity", 0)
    price = decision.get("price", 0)

    record = {
        "session_id": session["id"],
        "symbol": decision.get("symbol", ""),
        "action": db_action if db_action in ("buy", "sell", "hold") else action,
        "reason": decision.get("reason", ""),
        "confidence": decision.get("confidence", 0),
        "price": price,
        "quantity": qty,
        "amount": round(price * qty, 2) if price and qty else None,
        "market_snapshot": decision.get("market_snapshot", {}),
        "ai_analysis": decision.get("ai_analysis", ""),
        "status": status,
    }

    result = sb.table("agent_decisions").insert(record).execute()
    saved = result.data[0] if result.data else record
    saved["action_display"] = action
    logger.info(f"Agent 决策: {action} {decision.get('symbol')} (置信度={decision.get('confidence', 0):.0%})")
    return saved


async def execute_decision(decision_id: int) -> dict:
    """执行一条决策（买入/卖出）"""
    sb = get_supabase()

    dec = sb.table("agent_decisions").select("*, agent_sessions(*)").eq("id", decision_id).single().execute()
    if not dec.data:
        return {"error": "决策不存在"}

    d = dec.data
    session = d.get("agent_sessions", {})
    action = d["action"]

    if d["status"] != "pending":
        return {"error": f"决策状态为 {d['status']}，无法执行"}

    if action == "hold":
        sb.table("agent_decisions").update({"status": "executed"}).eq("id", decision_id).execute()
        return {**d, "status": "executed"}

    if action not in ("buy", "sell"):
        sb.table("agent_decisions").update({"status": "executed"}).eq("id", decision_id).execute()
        return {**d, "status": "executed"}

    portfolio_id = session.get("portfolio_id")
    if not portfolio_id:
        return {"error": "无法找到关联组合"}

    portfolio = sb.table("portfolios").select("*").eq("id", portfolio_id).single().execute()
    if not portfolio.data:
        return {"error": "组合不存在"}
    pf = portfolio.data

    price = d.get("price", 0)
    qty = d.get("quantity", 0)
    symbol = d["symbol"]

    if price <= 0 or qty <= 0:
        sb.table("agent_decisions").update({"status": "rejected", "reviewed_at": datetime.now(timezone.utc).isoformat()}).eq("id", decision_id).execute()
        return {**d, "status": "rejected", "reason": "价格或数量无效"}

    commission = price * qty * settings.COMMISSION_RATE
    total_amount = price * qty

    if action == "buy":
        if pf["cash_balance"] < total_amount + commission:
            sb.table("agent_decisions").update({"status": "rejected"}).eq("id", decision_id).execute()
            return {**d, "status": "rejected", "reason": "资金不足"}

        new_cash = pf["cash_balance"] - total_amount - commission

        existing = sb.table("positions").select("*").eq("portfolio_id", pf["id"]).eq("symbol", symbol).execute()
        if existing.data:
            pos = existing.data[0]
            new_qty = pos["quantity"] + qty
            new_avg = (pos["avg_cost"] * pos["quantity"] + price * qty) / new_qty
            sb.table("positions").update({
                "quantity": new_qty, "avg_cost": round(new_avg, 4),
                "current_price": price, "market_value": round(new_qty * price, 2),
                "unrealized_pnl": round(new_qty * (price - new_avg), 2),
                "stop_loss": calculate_stop_loss(price, pct=session.get("stop_loss_pct")),
                "take_profit": calculate_take_profit(price, pct=session.get("take_profit_pct")),
            }).eq("id", pos["id"]).execute()
        else:
            asset_type = "crypto" if "/" in symbol else "stock"
            sb.table("positions").insert({
                "portfolio_id": pf["id"], "symbol": symbol, "asset_type": asset_type,
                "quantity": qty, "avg_cost": price, "current_price": price,
                "market_value": round(qty * price, 2),
                "stop_loss": calculate_stop_loss(price, pct=session.get("stop_loss_pct")),
                "take_profit": calculate_take_profit(price, pct=session.get("take_profit_pct")),
            }).execute()

        sb.table("portfolios").update({
            "cash_balance": round(new_cash, 2),
            "current_value": round(new_cash + total_amount, 2),
        }).eq("id", pf["id"]).execute()

    elif action == "sell":
        existing = sb.table("positions").select("*").eq("portfolio_id", pf["id"]).eq("symbol", symbol).execute()
        if not existing.data:
            sb.table("agent_decisions").update({"status": "rejected"}).eq("id", decision_id).execute()
            return {**d, "status": "rejected", "reason": "无持仓"}

        pos = existing.data[0]
        sell_qty = min(qty, pos["quantity"])
        pnl = (price - pos["avg_cost"]) * sell_qty - commission
        new_cash = pf["cash_balance"] + price * sell_qty - commission

        remaining = pos["quantity"] - sell_qty
        if remaining <= 0:
            sb.table("positions").delete().eq("id", pos["id"]).execute()
        else:
            sb.table("positions").update({
                "quantity": remaining, "current_price": price,
                "market_value": round(remaining * price, 2),
            }).eq("id", pos["id"]).execute()

        all_pos = sb.table("positions").select("market_value").eq("portfolio_id", pf["id"]).execute()
        pos_value = sum(p["market_value"] or 0 for p in (all_pos.data or []))
        new_value = new_cash + pos_value
        total_pnl = new_value - pf["initial_capital"]

        sb.table("portfolios").update({
            "cash_balance": round(new_cash, 2),
            "current_value": round(new_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / pf["initial_capital"] * 100, 2),
        }).eq("id", pf["id"]).execute()

    # 记录交易
    trade = sb.table("trades").insert({
        "portfolio_id": pf["id"], "symbol": symbol,
        "direction": action, "quantity": qty if action == "buy" else sell_qty,
        "price": price, "total_amount": round(total_amount, 2),
        "commission": round(commission, 2), "status": "filled",
        "pnl": round(pnl, 2) if action == "sell" else None,
        "note": f"[AI Agent] {d.get('reason', '')}",
    }).execute()

    trade_id = trade.data[0]["id"] if trade.data else None

    # 更新决策状态
    sb.table("agent_decisions").update({
        "status": "executed",
        "trade_id": trade_id,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", decision_id).execute()

    # 更新会话统计
    is_win = action == "sell" and pnl > 0
    is_lose = action == "sell" and pnl <= 0
    sb.table("agent_sessions").update({
        "total_trades": (session.get("total_trades") or 0) + 1,
        "total_pnl": (session.get("total_pnl") or 0) + (pnl if action == "sell" else 0),
        "win_trades": (session.get("win_trades") or 0) + (1 if is_win else 0),
        "lose_trades": (session.get("lose_trades") or 0) + (1 if is_lose else 0),
    }).eq("id", session["id"]).execute()

    logger.info(f"Agent 交易执行: {action} {symbol} x{qty} @{price}")
    return {**d, "status": "executed", "trade_id": trade_id}
