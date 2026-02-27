"""
回测引擎 - 支持多种内置策略的回测
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime
from core.logger import logger


def _ma_cross_signals(df: pd.DataFrame, params: Dict) -> List[Tuple[str, str]]:
    """均线交叉策略"""
    fast = params.get("fast_period", 5)
    slow = params.get("slow_period", 20)
    close = df["close"] if "close" in df.columns else df["Close"]
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()

    signals = []
    position = 0
    for i in range(1, len(df)):
        if np.isnan(ma_fast.iloc[i]) or np.isnan(ma_slow.iloc[i]):
            signals.append(("hold", "数据不足"))
            continue
        if ma_fast.iloc[i] > ma_slow.iloc[i] and ma_fast.iloc[i - 1] <= ma_slow.iloc[i - 1]:
            signals.append(("buy", f"MA{fast}上穿MA{slow}"))
            position = 1
        elif ma_fast.iloc[i] < ma_slow.iloc[i] and ma_fast.iloc[i - 1] >= ma_slow.iloc[i - 1]:
            signals.append(("sell", f"MA{fast}下穿MA{slow}"))
            position = 0
        else:
            signals.append(("hold", ""))
    return signals


def _rsi_signals(df: pd.DataFrame, params: Dict) -> List[Tuple[str, str]]:
    """RSI 策略"""
    period = params.get("period", 14)
    overbought = params.get("overbought", 70)
    oversold = params.get("oversold", 30)
    close = df["close"] if "close" in df.columns else df["Close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)

    signals = []
    position = 0
    for i in range(1, len(df)):
        val = rsi.iloc[i]
        if np.isnan(val):
            signals.append(("hold", ""))
            continue
        if val < oversold and position == 0:
            signals.append(("buy", f"RSI={val:.1f}<{oversold}超卖"))
            position = 1
        elif val > overbought and position == 1:
            signals.append(("sell", f"RSI={val:.1f}>{overbought}超买"))
            position = 0
        else:
            signals.append(("hold", ""))
    return signals


def _macd_signals(df: pd.DataFrame, params: Dict) -> List[Tuple[str, str]]:
    """MACD 策略"""
    fast = params.get("fast_period", 12)
    slow = params.get("slow_period", 26)
    signal_period = params.get("signal_period", 9)
    close = df["close"] if "close" in df.columns else df["Close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    signals = []
    position = 0
    for i in range(1, len(df)):
        if np.isnan(macd_line.iloc[i]):
            signals.append(("hold", ""))
            continue
        if macd_line.iloc[i] > signal_line.iloc[i] and macd_line.iloc[i - 1] <= signal_line.iloc[i - 1]:
            signals.append(("buy", "MACD金叉"))
            position = 1
        elif macd_line.iloc[i] < signal_line.iloc[i] and macd_line.iloc[i - 1] >= signal_line.iloc[i - 1]:
            signals.append(("sell", "MACD死叉"))
            position = 0
        else:
            signals.append(("hold", ""))
    return signals


def _bollinger_signals(df: pd.DataFrame, params: Dict) -> List[Tuple[str, str]]:
    """布林带策略"""
    period = params.get("period", 20)
    num_std = params.get("num_std", 2)
    close = df["close"] if "close" in df.columns else df["Close"]
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std

    signals = []
    position = 0
    for i in range(1, len(df)):
        if np.isnan(upper.iloc[i]):
            signals.append(("hold", ""))
            continue
        p = close.iloc[i]
        if p < lower.iloc[i] and position == 0:
            signals.append(("buy", f"价格({p:.2f})触及下轨({lower.iloc[i]:.2f})"))
            position = 1
        elif p > upper.iloc[i] and position == 1:
            signals.append(("sell", f"价格({p:.2f})触及上轨({upper.iloc[i]:.2f})"))
            position = 0
        else:
            signals.append(("hold", ""))
    return signals


def _dual_thrust_signals(df: pd.DataFrame, params: Dict) -> List[Tuple[str, str]]:
    """Dual Thrust 策略"""
    n = params.get("lookback", 5)
    k1 = params.get("k1", 0.5)
    k2 = params.get("k2", 0.5)
    close = df["close"] if "close" in df.columns else df["Close"]
    high = df["high"] if "high" in df.columns else df["High"]
    low = df["low"] if "low" in df.columns else df["Low"]
    open_ = df["open"] if "open" in df.columns else df["Open"]

    signals = []
    position = 0
    for i in range(n, len(df)):
        hh = high.iloc[i - n:i].max()
        ll = low.iloc[i - n:i].min()
        hc = close.iloc[i - n:i].max()
        lc = close.iloc[i - n:i].min()
        rng = max(hh - lc, hc - ll)
        upper = open_.iloc[i] + k1 * rng
        lower = open_.iloc[i] - k2 * rng

        if close.iloc[i] > upper and position == 0:
            signals.append(("buy", f"突破上轨{upper:.2f}"))
            position = 1
        elif close.iloc[i] < lower and position == 1:
            signals.append(("sell", f"跌破下轨{lower:.2f}"))
            position = 0
        else:
            signals.append(("hold", ""))

    padding = [("hold", "")] * n
    return padding[1:] + signals  # skip first since we compare from index 1


def _turtle_signals(df: pd.DataFrame, params: Dict) -> List[Tuple[str, str]]:
    """海龟交易策略"""
    entry_period = params.get("entry_period", 20)
    exit_period = params.get("exit_period", 10)
    close = df["close"] if "close" in df.columns else df["Close"]
    high = df["high"] if "high" in df.columns else df["High"]
    low = df["low"] if "low" in df.columns else df["Low"]

    signals = []
    position = 0
    for i in range(1, len(df)):
        if i < entry_period:
            signals.append(("hold", ""))
            continue
        entry_high = high.iloc[i - entry_period:i].max()
        entry_low = low.iloc[i - entry_period:i].min()
        exit_low = low.iloc[max(0, i - exit_period):i].min()
        exit_high = high.iloc[max(0, i - exit_period):i].max()

        if close.iloc[i] > entry_high and position == 0:
            signals.append(("buy", f"突破{entry_period}日高点{entry_high:.2f}"))
            position = 1
        elif close.iloc[i] < exit_low and position == 1:
            signals.append(("sell", f"跌破{exit_period}日低点{exit_low:.2f}"))
            position = 0
        else:
            signals.append(("hold", ""))
    return signals


STRATEGY_GENERATORS = {
    "ma_cross": _ma_cross_signals,
    "rsi": _rsi_signals,
    "macd": _macd_signals,
    "bollinger": _bollinger_signals,
    "dual_thrust": _dual_thrust_signals,
    "turtle": _turtle_signals,
}


def run_backtest(
    df: pd.DataFrame,
    strategy_type: str,
    params: Dict[str, Any],
    initial_capital: float = 1_000_000,
    commission_rate: float = 0.001,
    slippage: float = 0.001,
) -> Dict[str, Any]:
    """执行回测，返回详细结果"""
    if strategy_type not in STRATEGY_GENERATORS:
        return {"error": f"不支持的策略类型: {strategy_type}"}

    if len(df) < 30:
        return {"error": "数据不足，至少需要30条K线"}

    close = df["close"] if "close" in df.columns else df["Close"]
    dates = [str(d)[:10] for d in df.index]

    signals = STRATEGY_GENERATORS[strategy_type](df, params)
    if len(signals) < len(df) - 1:
        signals = signals + [("hold", "")] * (len(df) - 1 - len(signals))

    cash = initial_capital
    position_qty = 0.0
    equity_curve = [{"date": dates[0], "value": initial_capital}]
    trades = []
    peak = initial_capital
    max_dd = 0.0
    max_dd_duration = 0
    dd_start = 0

    for i, (sig, reason) in enumerate(signals):
        idx = i + 1
        price = float(close.iloc[idx])
        slip_price = price * (1 + slippage) if sig == "buy" else price * (1 - slippage)

        if sig == "buy" and position_qty == 0:
            qty = int(cash * 0.95 / (slip_price * (1 + commission_rate)))
            if qty > 0:
                cost = qty * slip_price
                comm = cost * commission_rate
                cash -= cost + comm
                position_qty = qty
                trades.append({
                    "date": dates[idx],
                    "direction": "buy",
                    "price": round(slip_price, 2),
                    "quantity": qty,
                    "amount": round(cost, 2),
                    "commission": round(comm, 2),
                    "pnl": None,
                    "reason": reason,
                })

        elif sig == "sell" and position_qty > 0:
            revenue = position_qty * slip_price
            comm = revenue * commission_rate
            pnl = revenue - comm - trades[-1]["amount"] - trades[-1]["commission"] if trades else 0
            cash += revenue - comm
            trades.append({
                "date": dates[idx],
                "direction": "sell",
                "price": round(slip_price, 2),
                "quantity": position_qty,
                "amount": round(revenue, 2),
                "commission": round(comm, 2),
                "pnl": round(pnl, 2),
                "reason": reason,
            })
            position_qty = 0

        total_value = cash + position_qty * price
        equity_curve.append({"date": dates[idx], "value": round(total_value, 2)})

        if total_value > peak:
            peak = total_value
            dd_start = idx
        dd = (peak - total_value) / peak
        if dd > max_dd:
            max_dd = dd
            max_dd_duration = idx - dd_start

    # 如果回测结束时还有持仓，按最后价格平仓
    if position_qty > 0:
        last_price = float(close.iloc[-1])
        revenue = position_qty * last_price
        comm = revenue * commission_rate
        pnl = revenue - comm - trades[-1]["amount"] - trades[-1].get("commission", 0) if trades else 0
        cash += revenue - comm
        trades.append({
            "date": dates[-1],
            "direction": "sell",
            "price": round(last_price, 2),
            "quantity": position_qty,
            "amount": round(revenue, 2),
            "commission": round(comm, 2),
            "pnl": round(pnl, 2),
            "reason": "回测结束平仓",
        })
        position_qty = 0
        equity_curve[-1]["value"] = round(cash, 2)

    final_value = cash
    total_return = (final_value - initial_capital) / initial_capital
    days = max((df.index[-1] - df.index[0]).days, 1)
    annual_return = (1 + total_return) ** (365 / days) - 1

    sell_trades = [t for t in trades if t["direction"] == "sell" and t["pnl"] is not None]
    winning = [t for t in sell_trades if t["pnl"] > 0]
    losing = [t for t in sell_trades if t["pnl"] <= 0]
    total_wins = sum(t["pnl"] for t in winning)
    total_losses = abs(sum(t["pnl"] for t in losing)) or 1

    # Sharpe ratio (简化：使用日收益率)
    values = [e["value"] for e in equity_curve]
    returns = pd.Series(values).pct_change().dropna()
    sharpe = float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

    # Monthly returns
    eq_df = pd.DataFrame(equity_curve)
    eq_df["date"] = pd.to_datetime(eq_df["date"])
    eq_df.set_index("date", inplace=True)
    monthly = eq_df["value"].resample("ME").last().pct_change().dropna()
    monthly_returns = [{"month": str(d)[:7], "return": round(float(v) * 100, 2)} for d, v in monthly.items()]

    # Drawdown curve
    eq_series = pd.Series(values)
    running_max = eq_series.cummax()
    drawdown = (running_max - eq_series) / running_max
    drawdown_curve = [
        {"date": equity_curve[i]["date"], "drawdown": round(float(drawdown.iloc[i]) * 100, 2)}
        for i in range(len(drawdown))
    ]

    return {
        "total_return": round(total_return * 100, 2),
        "annual_return": round(annual_return * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "max_drawdown_duration": max_dd_duration,
        "win_rate": round(len(winning) / max(len(sell_trades), 1) * 100, 2),
        "profit_factor": round(total_wins / total_losses, 2),
        "total_trades": len(sell_trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "avg_win": round(total_wins / max(len(winning), 1), 2),
        "avg_loss": round(total_losses / max(len(losing), 1), 2),
        "best_trade": round(max((t["pnl"] for t in sell_trades), default=0), 2),
        "worst_trade": round(min((t["pnl"] for t in sell_trades), default=0), 2),
        "equity_curve": equity_curve,
        "trades": trades,
        "monthly_returns": monthly_returns,
        "drawdown_curve": drawdown_curve,
        "final_value": round(final_value, 2),
    }
