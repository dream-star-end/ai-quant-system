"""
AI Quant System - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routers import stocks, crypto, analysis

app = FastAPI(
    title="AI Quant System",
    description="AI 量化投资辅助决策系统 API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(stocks.router, prefix="/api/stocks", tags=["A股数据"])
app.include_router(crypto.router, prefix="/api/crypto", tags=["加密货币"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["AI分析"])

@app.get("/")
async def root():
    return {"message": "AI Quant System API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
