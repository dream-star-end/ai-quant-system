"""
DeepSeek 大模型服务
- 调用 DeepSeek API (OpenAI 兼容接口)
- 生成专业分析报告
- 智能问答
- 策略解读
"""
import json
import httpx
from typing import Dict, Any, List, Optional

from config import get_settings
from core.logger import logger

settings = get_settings()

SYSTEM_PROMPT = """你是一位资深量化投资分析师，拥有 CFA 和 FRM 资质。你擅长：
1. 分析股票和加密货币的技术面、基本面
2. 解读各种技术指标（MA、RSI、MACD、布林带、KDJ等）
3. 给出专业的投资建议，包括仓位管理、止损止盈
4. 风险评估和资产配置建议
5. 量化策略的设计和回测结果解读

回答要求：
- 用中文回答，专业但易懂
- 给出明确的观点和建议，不要模棱两可
- 涉及具体数字时要精确
- 始终提醒风险，投资有风险
- 格式清晰，使用分点或分段"""


async def _call_deepseek(
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """调用 DeepSeek API"""
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("未配置 DEEPSEEK_API_KEY，请在 .env 文件中设置")

    url = f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature or settings.DEEPSEEK_TEMPERATURE,
        "max_tokens": max_tokens or settings.DEEPSEEK_MAX_TOKENS,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        logger.info(f"DeepSeek 调用成功, tokens: {data.get('usage', {})}")
        return content


async def chat(user_message: str, context: Optional[str] = None) -> str:
    """与 DeepSeek 对话（通用问答）"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "system", "content": f"当前市场数据上下文:\n{context}"})
    messages.append({"role": "user", "content": user_message})
    return await _call_deepseek(messages)


async def generate_analysis_report(
    symbol: str,
    market_data: Dict[str, Any],
    indicators: Dict[str, Any],
    trend_result: Dict[str, Any],
    risk_metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """生成深度分析报告"""
    # 构建数据摘要供 DeepSeek 分析
    data_summary = _build_data_summary(symbol, market_data, indicators, trend_result, risk_metrics)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""请对 {symbol} 生成一份专业的投资分析报告。

## 市场数据
{data_summary}

请按以下结构输出报告：

### 一、行情概览
简述当前价格、近期走势。

### 二、技术面分析
分析各技术指标的含义和信号。

### 三、趋势研判
综合判断短期（1-5天）、中期（1-4周）趋势方向。

### 四、风险评估
分析主要风险点，给出风险等级。

### 五、操作建议
明确的操作建议，包括：
- 操作方向（买入/卖出/观望）
- 建议仓位比例
- 入场价位区间
- 止损价位
- 止盈目标

### 六、风险提示
投资风险提醒。"""},
    ]
    return await _call_deepseek(messages, max_tokens=4096)


async def interpret_backtest(
    strategy_type: str,
    params: Dict[str, Any],
    result: Dict[str, Any],
    symbol: str,
) -> str:
    """解读回测结果"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""请解读以下策略回测结果：

**策略**: {strategy_type}
**标的**: {symbol}
**参数**: {json.dumps(params, ensure_ascii=False)}

**回测结果**:
- 总收益率: {result.get('total_return')}%
- 年化收益: {result.get('annual_return')}%
- 夏普比率: {result.get('sharpe_ratio')}
- 最大回撤: {result.get('max_drawdown')}%
- 胜率: {result.get('win_rate')}%
- 盈亏比: {result.get('profit_factor')}
- 总交易次数: {result.get('total_trades')}
- 盈利次数: {result.get('winning_trades')}
- 亏损次数: {result.get('losing_trades')}
- 平均盈利: {result.get('avg_win')}
- 平均亏损: {result.get('avg_loss')}

请分析：
1. 这个策略表现如何？有哪些优缺点？
2. 参数是否合理？有什么优化建议？
3. 这个策略适合什么市场环境？
4. 实盘使用需要注意什么？"""},
    ]
    return await _call_deepseek(messages)


async def generate_strategy_suggestion(
    symbol: str,
    market_data: Dict[str, Any],
    user_preference: Optional[str] = None,
) -> str:
    """基于当前行情推荐策略"""
    pref = f"\n用户偏好: {user_preference}" if user_preference else ""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""基于以下市场数据，推荐适合当前行情的量化策略。

**标的**: {symbol}
**市场数据**:
{json.dumps(market_data, ensure_ascii=False, indent=2)}{pref}

系统支持的策略类型：
1. ma_cross (均线交叉) - 参数: fast_period, slow_period
2. rsi (RSI超买超卖) - 参数: period, overbought, oversold
3. macd (MACD信号) - 参数: fast_period, slow_period, signal_period
4. bollinger (布林带) - 参数: period, num_std
5. dual_thrust (Dual Thrust) - 参数: lookback, k1, k2
6. turtle (海龟交易) - 参数: entry_period, exit_period

请推荐 1-2 个最适合当前行情的策略，并给出推荐的参数值和理由。
用 JSON 格式输出推荐，包含 strategy_type, params, reason 字段。"""},
    ]
    return await _call_deepseek(messages, temperature=0.2)


def _build_data_summary(
    symbol: str,
    market_data: Dict[str, Any],
    indicators: Dict[str, Any],
    trend_result: Dict[str, Any],
    risk_metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """构建给 DeepSeek 的数据摘要"""
    parts = [f"标的: {symbol}"]

    # 价格数据
    if market_data:
        parts.append(f"当前价格: {market_data.get('price', 'N/A')}")
        parts.append(f"涨跌幅: {market_data.get('change_pct', 'N/A')}%")
        parts.append(f"成交量: {market_data.get('volume', 'N/A')}")

    # 技术指标摘要
    if indicators:
        for key in ["ma5", "ma10", "ma20", "ma60"]:
            vals = indicators.get(key, [])
            if vals:
                recent = [v for v in vals[-3:] if v is not None]
                if recent:
                    parts.append(f"{key.upper()}: {recent[-1]:.2f}")

        rsi = indicators.get("rsi14", [])
        if rsi:
            recent_rsi = [v for v in rsi[-3:] if v is not None]
            if recent_rsi:
                parts.append(f"RSI(14): {recent_rsi[-1]:.1f}")

        macd = indicators.get("macd", [])
        macd_sig = indicators.get("macd_signal", [])
        if macd and macd_sig:
            recent_m = [v for v in macd[-3:] if v is not None]
            recent_s = [v for v in macd_sig[-3:] if v is not None]
            if recent_m and recent_s:
                parts.append(f"MACD: {recent_m[-1]:.4f}, Signal: {recent_s[-1]:.4f}")

        for key in ["boll_upper", "boll_middle", "boll_lower"]:
            vals = indicators.get(key, [])
            if vals:
                recent = [v for v in vals[-3:] if v is not None]
                if recent:
                    label = {"boll_upper": "布林上轨", "boll_middle": "布林中轨", "boll_lower": "布林下轨"}[key]
                    parts.append(f"{label}: {recent[-1]:.2f}")

    # 趋势预测
    if trend_result:
        parts.append(f"\n技术面综合判断: {trend_result.get('signal', 'N/A')}")
        parts.append(f"趋势方向: {trend_result.get('trend', 'N/A')}")
        parts.append(f"置信度: {trend_result.get('confidence', 'N/A')}%")
        parts.append(f"多头评分: {trend_result.get('bull_score', 0)}, 空头评分: {trend_result.get('bear_score', 0)}")
        sigs = trend_result.get("signals", [])
        if sigs:
            parts.append("信号明细:")
            for s in sigs:
                parts.append(f"  - {s['name']} ({s['type']})")

    # 风险指标
    if risk_metrics:
        parts.append(f"\n夏普比率: {risk_metrics.get('sharpe_ratio', 'N/A')}")
        parts.append(f"最大回撤: {risk_metrics.get('max_drawdown', 'N/A')}%")
        parts.append(f"年化波动率: {risk_metrics.get('volatility', 'N/A')}%")
        parts.append(f"VaR(95%): {risk_metrics.get('var_95', 'N/A')}%")

    return "\n".join(parts)


def is_deepseek_configured() -> bool:
    """检查 DeepSeek 是否已配置"""
    return bool(settings.DEEPSEEK_API_KEY)
