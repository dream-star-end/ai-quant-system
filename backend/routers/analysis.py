"""
AI 分析路由
- 技术面趋势预测（规则引擎，无需 key）
- DeepSeek 深度分析报告
- DeepSeek 智能问答
- DeepSeek 回测解读
- DeepSeek 策略推荐
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from schemas.common import APIResponse
from services.market_data import (
    get_stock_quote, get_stock_history,
    get_crypto_price, get_crypto_history,
    calculate_indicators,
)
from services.ai_service import predict_trend, generate_smart_recommendation
from services.risk_manager import calculate_risk_metrics, score_risk
from services import deepseek_service
from core.logger import logger

router = APIRouter()


# ---------- 技术面分析（无需 DeepSeek key） ----------

@router.get("/predict/{symbol}")
async def predict(
    symbol: str,
    period: str = Query("6mo", description="数据范围"),
    asset_type: str = Query("stock", description="stock 或 crypto"),
):
    """AI 综合趋势预测（规则引擎）"""
    df = _get_df(symbol, asset_type, period)
    if df is None:
        return APIResponse(success=False, message="数据不足，无法分析")

    result = predict_trend(df)
    if "error" in result:
        return APIResponse(success=False, message=result["error"])
    return APIResponse(data=result)


@router.get("/recommend/{symbol}")
async def recommend(
    symbol: str,
    period: str = Query("6mo"),
    asset_type: str = Query("stock"),
):
    """智能投资推荐（规则引擎）"""
    df = _get_df(symbol, asset_type, period)
    if df is None:
        return APIResponse(success=False, message="数据不足")

    close_col = "close" if "close" in df.columns else "Close"
    trend = predict_trend(df)
    risk = calculate_risk_metrics(df[close_col].tolist())
    rec = generate_smart_recommendation(symbol, trend, risk)
    return APIResponse(data=rec)


@router.get("/risk/{symbol}")
async def risk_analysis(
    symbol: str,
    period: str = Query("1y"),
    asset_type: str = Query("stock"),
):
    """风险分析"""
    df = _get_df(symbol, asset_type, period, min_rows=30, long_period=True)
    if df is None:
        return APIResponse(success=False, message="数据不足")

    close_col = "close" if "close" in df.columns else "Close"
    metrics = calculate_risk_metrics(df[close_col].tolist())
    risk_score = score_risk(metrics)
    return APIResponse(data={"symbol": symbol, "metrics": metrics, "risk_score": risk_score})


@router.get("/indicators/{symbol}")
async def indicators(
    symbol: str,
    period: str = Query("6mo"),
    asset_type: str = Query("stock"),
):
    """全量技术指标"""
    df = _get_df(symbol, asset_type, period, min_rows=5)
    if df is None:
        return APIResponse(success=False, message="无数据")
    result = calculate_indicators(df)
    return APIResponse(data={"symbol": symbol, **result})


# ---------- DeepSeek 大模型分析 ----------

@router.get("/deepseek/status")
async def deepseek_status():
    """检查 DeepSeek 是否可用"""
    from config import get_settings
    s = get_settings()
    return APIResponse(data={
        "configured": deepseek_service.is_deepseek_configured(),
        "model": s.DEEPSEEK_MODEL,
        "base_url": s.DEEPSEEK_BASE_URL,
    })


class ChatRequest(BaseModel):
    message: str
    symbol: Optional[str] = None
    asset_type: str = "stock"


@router.post("/deepseek/chat")
async def deepseek_chat(body: ChatRequest):
    """与 DeepSeek 对话 - 询问任何投资问题"""
    if not deepseek_service.is_deepseek_configured():
        return APIResponse(success=False, message="未配置 DEEPSEEK_API_KEY，请在 .env 中设置")

    context = None
    if body.symbol:
        try:
            df = _get_df(body.symbol, body.asset_type, "3mo")
            if df is not None:
                trend = predict_trend(df)
                indicators = calculate_indicators(df)
                context = deepseek_service._build_data_summary(
                    body.symbol, {}, indicators, trend, None
                )
        except Exception:
            pass

    try:
        reply = await deepseek_service.chat(body.message, context)
        return APIResponse(data={"reply": reply})
    except Exception as e:
        logger.error(f"DeepSeek chat 失败: {e}")
        return APIResponse(success=False, message=f"DeepSeek 调用失败: {str(e)}")


@router.get("/deepseek/report/{symbol}")
async def deepseek_report(
    symbol: str,
    period: str = Query("6mo"),
    asset_type: str = Query("stock"),
):
    """DeepSeek 生成专业分析报告"""
    if not deepseek_service.is_deepseek_configured():
        return APIResponse(success=False, message="未配置 DEEPSEEK_API_KEY，请在 .env 中设置")

    df = _get_df(symbol, asset_type, period)
    if df is None:
        return APIResponse(success=False, message="数据不足")

    # 收集全量数据
    close_col = "close" if "close" in df.columns else "Close"
    market_data = {}
    if asset_type == "crypto":
        market_data = get_crypto_price(symbol)
    else:
        market_data = get_stock_quote(symbol)

    indicators = calculate_indicators(df)
    trend = predict_trend(df)
    risk = calculate_risk_metrics(df[close_col].tolist())

    try:
        report = await deepseek_service.generate_analysis_report(
            symbol, market_data, indicators, trend, risk
        )
        return APIResponse(data={
            "symbol": symbol,
            "report": report,
            "trend_data": trend,
            "risk_data": {"metrics": risk, "risk_score": score_risk(risk)},
        })
    except Exception as e:
        logger.error(f"DeepSeek report 失败: {e}")
        return APIResponse(success=False, message=f"DeepSeek 调用失败: {str(e)}")


class BacktestInterpretRequest(BaseModel):
    strategy_type: str
    params: dict = {}
    symbol: str
    result: dict


@router.post("/deepseek/interpret-backtest")
async def deepseek_interpret_backtest(body: BacktestInterpretRequest):
    """DeepSeek 解读回测结果"""
    if not deepseek_service.is_deepseek_configured():
        return APIResponse(success=False, message="未配置 DEEPSEEK_API_KEY")

    try:
        interpretation = await deepseek_service.interpret_backtest(
            body.strategy_type, body.params, body.result, body.symbol
        )
        return APIResponse(data={"interpretation": interpretation})
    except Exception as e:
        logger.error(f"DeepSeek interpret 失败: {e}")
        return APIResponse(success=False, message=f"DeepSeek 调用失败: {str(e)}")


@router.get("/deepseek/strategy-suggest/{symbol}")
async def deepseek_strategy_suggest(
    symbol: str,
    asset_type: str = Query("stock"),
    preference: Optional[str] = Query(None, description="用户偏好，如: 稳健、激进、短线"),
):
    """DeepSeek 智能推荐策略"""
    if not deepseek_service.is_deepseek_configured():
        return APIResponse(success=False, message="未配置 DEEPSEEK_API_KEY")

    df = _get_df(symbol, asset_type, "6mo")
    if df is None:
        return APIResponse(success=False, message="数据不足")

    trend = predict_trend(df)
    indicators = calculate_indicators(df)
    market_data = {
        "trend": trend,
        "indicators_summary": {
            k: ([v for v in vals[-5:] if v is not None][-1:] or [None])[0]
            for k, vals in indicators.items()
            if isinstance(vals, list) and k not in ("dates", "closes", "volumes")
        },
    }

    try:
        suggestion = await deepseek_service.generate_strategy_suggestion(
            symbol, market_data, preference
        )
        return APIResponse(data={"suggestion": suggestion})
    except Exception as e:
        logger.error(f"DeepSeek strategy suggest 失败: {e}")
        return APIResponse(success=False, message=f"DeepSeek 调用失败: {str(e)}")


# ---------- 辅助函数 ----------

def _get_df(symbol, asset_type, period="6mo", min_rows=30, long_period=False):
    if asset_type == "crypto":
        limit = 365 if long_period else 200
        df = get_crypto_history(symbol, "1d", limit)
    else:
        p = "1y" if long_period else period
        df = get_stock_history(symbol, p)
    if df.empty or len(df) < min_rows:
        return None
    return df
