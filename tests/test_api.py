"""
API 测试模块
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "AI Quant System" in data["name"]
    assert "features" in data


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_stock_symbols():
    response = client.get("/api/v1/stocks/symbols")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) > 0


def test_crypto_symbols():
    response = client.get("/api/v1/crypto/symbols")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_strategy_types():
    response = client.get("/api/v1/strategies/types/list")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    types = [t["type"] for t in data["data"]]
    assert "ma_cross" in types
    assert "rsi" in types
    assert "macd" in types
    assert "bollinger" in types
    assert "turtle" in types


def test_backtest_guest():
    response = client.post("/api/v1/backtest/run/guest", json={
        "strategy_type": "ma_cross",
        "symbol": "000300.SS",
        "start_date": "2024-01-01",
        "end_date": "2025-06-01",
        "initial_capital": 1000000,
        "commission_rate": 0.001,
        "slippage": 0.001,
        "params": {"fast_period": 5, "slow_period": 20},
    })
    assert response.status_code == 200
    data = response.json()
    assert "success" in data


def test_deepseek_status():
    response = client.get("/api/v1/analysis/deepseek/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "configured" in data["data"]
    assert "model" in data["data"]


def test_deepseek_chat_without_key():
    """未配置 key 时应返回错误提示而非崩溃"""
    response = client.post("/api/v1/analysis/deepseek/chat", json={
        "message": "茅台现在能买吗？",
    })
    assert response.status_code == 200
    data = response.json()
    if not data.get("success"):
        assert "DEEPSEEK_API_KEY" in data.get("message", "")


def test_supported_brokers():
    """获取支持的交易所列表"""
    response = client.get("/api/v1/broker/supported")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    types = [b["type"] for b in data["data"]]
    assert "binance" in types
    assert "okx" in types


def test_live_trade_requires_confirmation():
    """实盘交易需要二次确认"""
    response = client.post("/api/v1/broker/trade", json={
        "broker_account_id": 1,
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": 0.001,
        "confirm_real_trade": False,
    })
    assert response.status_code in (200, 401)
    data = response.json()
    if response.status_code == 200:
        assert data["success"] is False
        assert "确认" in data.get("message", "")
