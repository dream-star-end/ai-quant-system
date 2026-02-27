"""
AI Quant System - FastAPI 后端服务
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uvicorn

from config import get_settings
from core.logger import logger
from routers import stocks, crypto, analysis, backtest, strategies, portfolio, alerts, auth, watchlist, agent

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"Supabase: {settings.SUPABASE_URL}")
    yield
    logger.info("👋 服务关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI 驱动的量化投资决策系统 - 支持 A股/加密货币的智能分析、策略回测、模拟交易",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    if request.url.path not in ("/health", "/favicon.ico"):
        logger.debug(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.0f}ms)")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未捕获异常: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"success": False, "error": "服务器内部错误", "detail": str(exc) if settings.DEBUG else ""})


prefix = settings.API_PREFIX

app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["认证"])
app.include_router(stocks.router, prefix=f"{prefix}/stocks", tags=["A股数据"])
app.include_router(crypto.router, prefix=f"{prefix}/crypto", tags=["加密货币"])
app.include_router(analysis.router, prefix=f"{prefix}/analysis", tags=["AI分析"])
app.include_router(backtest.router, prefix=f"{prefix}/backtest", tags=["策略回测"])
app.include_router(strategies.router, prefix=f"{prefix}/strategies", tags=["策略管理"])
app.include_router(portfolio.router, prefix=f"{prefix}/portfolio", tags=["投资组合"])
app.include_router(alerts.router, prefix=f"{prefix}/alerts", tags=["智能告警"])
app.include_router(watchlist.router, prefix=f"{prefix}/watchlist", tags=["自选管理"])
app.include_router(agent.router, prefix=f"{prefix}/agent", tags=["AI Agent"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "features": [
            "A股/加密货币行情数据",
            "多策略回测引擎 (均线交叉/RSI/MACD/布林带/海龟/Dual Thrust)",
            "AI趋势预测与智能推荐",
            "风险评估与管理",
            "模拟交易系统",
            "投资组合管理",
            "智能告警",
            "自选管理",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
