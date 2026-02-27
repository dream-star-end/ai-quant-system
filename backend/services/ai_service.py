"""
AI 分析服务
- 技术指标规则引擎（实时，无需 API key）
- DeepSeek 大模型深度分析（需要 API key）
- 两者融合：先跑技术指标，再让 DeepSeek 解读
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from core.logger import logger
from services.deepseek_service import is_deepseek_configured


def predict_trend(df: pd.DataFrame, horizon: int = 5) -> Dict[str, Any]:
    """
    综合趋势预测，融合多种信号:
    1. 均线趋势
    2. RSI 状态
    3. MACD 状态
    4. 成交量趋势
    5. 动量分析
    """
    if df.empty or len(df) < 30:
        return {"error": "数据不足，至少需要30根K线"}

    close = df["close"] if "close" in df.columns else df["Close"]
    volume = df["volume"] if "volume" in df.columns else df["Volume"]

    signals: List[Dict] = []
    bull_score = 0
    bear_score = 0

    # 1. 均线趋势
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean() if len(close) >= 60 else ma20

    if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
        bull_score += 25
        signals.append({"name": "均线多头排列", "type": "bullish", "weight": 25})
    elif ma5.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1]:
        bear_score += 25
        signals.append({"name": "均线空头排列", "type": "bearish", "weight": 25})
    else:
        signals.append({"name": "均线交织", "type": "neutral", "weight": 0})

    # 2. RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi_val = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50

    if rsi_val < 30:
        bull_score += 20
        signals.append({"name": f"RSI超卖({rsi_val:.0f})", "type": "bullish", "weight": 20})
    elif rsi_val > 70:
        bear_score += 20
        signals.append({"name": f"RSI超买({rsi_val:.0f})", "type": "bearish", "weight": 20})
    elif rsi_val < 50:
        bear_score += 5
        signals.append({"name": f"RSI偏弱({rsi_val:.0f})", "type": "bearish", "weight": 5})
    else:
        bull_score += 5
        signals.append({"name": f"RSI偏强({rsi_val:.0f})", "type": "bullish", "weight": 5})

    # 3. MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line

    if hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
        bull_score += 20
        signals.append({"name": "MACD金叉", "type": "bullish", "weight": 20})
    elif hist.iloc[-1] < 0 and hist.iloc[-2] >= 0:
        bear_score += 20
        signals.append({"name": "MACD死叉", "type": "bearish", "weight": 20})
    elif hist.iloc[-1] > hist.iloc[-2]:
        bull_score += 10
        signals.append({"name": "MACD柱放大", "type": "bullish", "weight": 10})
    else:
        bear_score += 10
        signals.append({"name": "MACD柱缩小", "type": "bearish", "weight": 10})

    # 4. 成交量趋势
    vol_ma5 = volume.rolling(5).mean()
    vol_ma20 = volume.rolling(20).mean()
    if vol_ma5.iloc[-1] > vol_ma20.iloc[-1] * 1.5:
        if close.iloc[-1] > close.iloc[-2]:
            bull_score += 15
            signals.append({"name": "放量上涨", "type": "bullish", "weight": 15})
        else:
            bear_score += 15
            signals.append({"name": "放量下跌", "type": "bearish", "weight": 15})
    else:
        signals.append({"name": "成交量正常", "type": "neutral", "weight": 0})

    # 5. 动量 (5日涨跌幅)
    mom = (close.iloc[-1] / close.iloc[-5] - 1) * 100
    if mom > 3:
        bull_score += 15
        signals.append({"name": f"5日动量强({mom:.1f}%)", "type": "bullish", "weight": 15})
    elif mom < -3:
        bear_score += 15
        signals.append({"name": f"5日动量弱({mom:.1f}%)", "type": "bearish", "weight": 15})
    else:
        signals.append({"name": f"5日动量中性({mom:.1f}%)", "type": "neutral", "weight": 0})

    # 综合判断
    total = bull_score + bear_score or 1
    bull_pct = bull_score / total * 100
    confidence = abs(bull_score - bear_score) / total * 100

    if bull_score > bear_score + 15:
        trend = "bullish"
        signal = "买入"
    elif bear_score > bull_score + 15:
        trend = "bearish"
        signal = "卖出"
    else:
        trend = "neutral"
        signal = "观望"

    # 简单线性回归预测
    recent = close.values[-20:]
    x = np.arange(len(recent))
    slope, intercept = np.polyfit(x, recent, 1)
    predicted_prices = [round(float(slope * (len(recent) + i) + intercept), 2) for i in range(horizon)]

    return {
        "trend": trend,
        "signal": signal,
        "confidence": round(confidence, 1),
        "bull_score": bull_score,
        "bear_score": bear_score,
        "signals": signals,
        "current_price": round(float(close.iloc[-1]), 2),
        "predicted_prices": predicted_prices,
        "prediction_horizon": horizon,
        "analysis_summary": _generate_summary(trend, confidence, signals),
    }


def _generate_summary(trend: str, confidence: float, signals: List[Dict]) -> str:
    """生成自然语言分析摘要"""
    trend_map = {"bullish": "看涨", "bearish": "看跌", "neutral": "震荡"}
    trend_cn = trend_map.get(trend, "不确定")

    bull_reasons = [s["name"] for s in signals if s["type"] == "bullish"]
    bear_reasons = [s["name"] for s in signals if s["type"] == "bearish"]

    parts = [f"综合分析判断: {trend_cn} (置信度 {confidence:.0f}%)。"]
    if bull_reasons:
        parts.append(f"利多因素: {', '.join(bull_reasons)}。")
    if bear_reasons:
        parts.append(f"利空因素: {', '.join(bear_reasons)}。")

    if confidence < 30:
        parts.append("信号较弱，建议观望。")
    elif trend == "bullish":
        parts.append("建议逢低布局，注意设置止损。")
    elif trend == "bearish":
        parts.append("建议谨慎操作，控制仓位。")

    return " ".join(parts)


def generate_smart_recommendation(
    symbol: str,
    trend_result: Dict,
    risk_metrics: Optional[Dict] = None,
) -> Dict[str, Any]:
    """智能推荐 - 综合趋势和风险给出建议"""
    trend = trend_result.get("trend", "neutral")
    confidence = trend_result.get("confidence", 0)
    price = trend_result.get("current_price", 0)

    action = "观望"
    position_size = "0%"
    entry_range = ""
    stop_loss = ""
    take_profit = ""
    reasoning = []

    if trend == "bullish" and confidence > 40:
        action = "建议买入"
        pct = min(30, 10 + confidence * 0.3)
        position_size = f"{pct:.0f}%"
        entry_range = f"{price * 0.98:.2f} - {price:.2f}"
        stop_loss = f"{price * 0.95:.2f}"
        take_profit = f"{price * 1.15:.2f}"
        reasoning.append("多项技术指标看涨")
        if confidence > 60:
            reasoning.append("信号强度较高")
    elif trend == "bearish" and confidence > 40:
        action = "建议卖出/回避"
        position_size = "0%"
        reasoning.append("多项技术指标看跌")
    else:
        action = "建议观望"
        position_size = "5-10%"
        reasoning.append("信号不明确，建议小仓位试探")

    if risk_metrics:
        mdd = risk_metrics.get("max_drawdown", 0)
        if mdd > 20:
            reasoning.append(f"注意: 历史最大回撤{mdd:.1f}%较高")

    return {
        "symbol": symbol,
        "action": action,
        "position_size": position_size,
        "entry_range": entry_range,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": round(confidence, 1),
        "reasoning": reasoning,
        "trend_detail": trend_result,
    }
