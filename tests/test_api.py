"""
测试模块
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Quant System" in response.json()["message"]

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_stock_quote():
    response = client.get("/api/stocks/quote/000300.SS")
    # 可能返回 error 或数据
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data or "error" in data

def test_crypto_price():
    response = client.get("/api/crypto/price/BTC/USDT")
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data or "error" in data
