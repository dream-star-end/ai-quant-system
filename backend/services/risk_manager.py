"""
风险管理服务
- 仓位控制
- 止损/止盈检查
- 回撤监控
- 风险评分
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from config import get_settings
from core.logger import logger

settings = get_settings()


def check_position_size(
    portfolio_value: float,
    order_amount: float,
    max_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """检查单笔订单是否超过仓位限制"""
    limit = max_pct or settings.MAX_POSITION_SIZE_PCT
    max_allowed = portfolio_value * limit
    ok = order_amount <= max_allowed
    return {
        "allowed": ok,
        "order_amount": round(order_amount, 2),
        "max_allowed": round(max_allowed, 2),
        "portfolio_value": round(portfolio_value, 2),
        "position_pct": round(order_amount / portfolio_value * 100, 2) if portfolio_value else 0,
        "message": "" if ok else f"订单金额 {order_amount:.0f} 超过仓位限制 {max_allowed:.0f} ({limit*100:.0f}%)",
    }


def calculate_stop_loss(
    entry_price: float,
    direction: str = "buy",
    method: str = "fixed",
    pct: Optional[float] = None,
    atr: Optional[float] = None,
    atr_multiplier: float = 2.0,
) -> float:
    """计算止损价"""
    if method == "atr" and atr is not None:
        distance = atr * atr_multiplier
    else:
        distance = entry_price * (pct or settings.DEFAULT_STOP_LOSS_PCT)

    if direction == "buy":
        return round(entry_price - distance, 4)
    return round(entry_price + distance, 4)


def calculate_take_profit(
    entry_price: float,
    direction: str = "buy",
    pct: Optional[float] = None,
) -> float:
    """计算止盈价"""
    tp_pct = pct or settings.DEFAULT_TAKE_PROFIT_PCT
    if direction == "buy":
        return round(entry_price * (1 + tp_pct), 4)
    return round(entry_price * (1 - tp_pct), 4)


def calculate_risk_metrics(equity_curve: List[float]) -> Dict[str, Any]:
    """基于权益曲线计算风险指标"""
    if len(equity_curve) < 2:
        return {}
    series = pd.Series(equity_curve)
    returns = series.pct_change().dropna()

    peak = series.cummax()
    drawdown = (peak - series) / peak
    max_dd = float(drawdown.max())

    vol = float(returns.std() * np.sqrt(252))
    sharpe = float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

    neg_returns = returns[returns < 0]
    sortino = float(returns.mean() / neg_returns.std() * np.sqrt(252)) if len(neg_returns) > 0 and neg_returns.std() > 0 else 0

    # VaR (95%)
    var_95 = float(np.percentile(returns, 5))

    # CVaR (95%)
    cvar_95 = float(returns[returns <= var_95].mean()) if len(returns[returns <= var_95]) > 0 else var_95

    return {
        "volatility": round(vol * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "current_drawdown": round(float(drawdown.iloc[-1]) * 100, 2),
        "var_95": round(var_95 * 100, 2),
        "cvar_95": round(cvar_95 * 100, 2),
        "total_return": round(float((series.iloc[-1] / series.iloc[0] - 1) * 100), 2),
        "win_days": int((returns > 0).sum()),
        "lose_days": int((returns < 0).sum()),
        "daily_win_rate": round(float((returns > 0).sum() / len(returns) * 100), 2),
    }


def score_risk(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """给出综合风险评分 (0-100, 100为最安全)"""
    score = 50.0
    reasons = []

    # Sharpe
    sr = metrics.get("sharpe_ratio", 0)
    if sr > 2:
        score += 15
        reasons.append(f"夏普比率优秀({sr})")
    elif sr > 1:
        score += 8
        reasons.append(f"夏普比率良好({sr})")
    elif sr < 0:
        score -= 15
        reasons.append(f"夏普比率为负({sr})")

    # Max Drawdown
    mdd = metrics.get("max_drawdown", 0)
    if mdd < 5:
        score += 15
        reasons.append(f"最大回撤极低({mdd}%)")
    elif mdd < 10:
        score += 8
        reasons.append(f"最大回撤较低({mdd}%)")
    elif mdd > 30:
        score -= 20
        reasons.append(f"最大回撤过高({mdd}%)")
    elif mdd > 20:
        score -= 10
        reasons.append(f"最大回撤偏高({mdd}%)")

    # Win rate
    wr = metrics.get("daily_win_rate", 50)
    if wr > 55:
        score += 10
        reasons.append(f"日胜率较高({wr}%)")
    elif wr < 45:
        score -= 10
        reasons.append(f"日胜率偏低({wr}%)")

    # Volatility
    vol = metrics.get("volatility", 20)
    if vol < 15:
        score += 5
    elif vol > 40:
        score -= 10
        reasons.append(f"波动率过高({vol}%)")

    score = max(0, min(100, score))
    if score >= 80:
        level = "低风险"
    elif score >= 60:
        level = "中低风险"
    elif score >= 40:
        level = "中等风险"
    elif score >= 20:
        level = "中高风险"
    else:
        level = "高风险"

    return {
        "score": round(score),
        "level": level,
        "reasons": reasons,
    }
