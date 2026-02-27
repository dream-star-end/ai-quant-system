"""
Broker 工厂 — 根据配置创建对应的交易适配器
"""
from typing import Dict, Any
from services.brokers.base import BaseBroker
from services.brokers.crypto_broker import CryptoBroker
from services.brokers.stock_broker import StockBrokerStub
from database import get_supabase
from core.logger import logger

CRYPTO_EXCHANGES = {"binance", "okx", "huobi", "bybit", "gate"}
STOCK_BROKERS = {"stock_sim", "stock_hx", "stock_ths"}


def create_broker(
    broker_type: str,
    api_key: str,
    api_secret: str,
    passphrase: str = "",
    testnet: bool = False,
    extra_config: Dict[str, Any] = None,
) -> BaseBroker:
    """根据类型创建 Broker 实例"""
    if broker_type in CRYPTO_EXCHANGES:
        return CryptoBroker(
            exchange_id=broker_type,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            testnet=testnet,
            extra_config=extra_config,
        )
    elif broker_type in STOCK_BROKERS:
        return StockBrokerStub(broker_id=broker_type)
    else:
        raise ValueError(f"不支持的 broker 类型: {broker_type}")


async def get_broker(broker_account_id: int) -> BaseBroker:
    """从数据库加载 Broker 配置并创建实例"""
    sb = get_supabase()
    result = sb.table("broker_accounts").select("*").eq("id", broker_account_id).single().execute()
    if not result.data:
        raise ValueError(f"交易账户 {broker_account_id} 不存在")

    acc = result.data
    return create_broker(
        broker_type=acc["broker_type"],
        api_key=acc["api_key"],
        api_secret=acc["api_secret"],
        passphrase=acc.get("passphrase", ""),
        testnet=acc.get("is_testnet", False),
        extra_config=acc.get("extra_config"),
    )


def get_supported_brokers():
    """获取支持的交易所/券商列表"""
    return [
        {"type": "binance", "name": "Binance 币安", "category": "crypto", "features": ["现货", "合约", "测试网"]},
        {"type": "okx", "name": "OKX 欧易", "category": "crypto", "features": ["现货", "合约", "测试网"]},
        {"type": "huobi", "name": "Huobi 火币", "category": "crypto", "features": ["现货"]},
        {"type": "bybit", "name": "Bybit", "category": "crypto", "features": ["现货", "合约", "测试网"]},
        {"type": "gate", "name": "Gate.io", "category": "crypto", "features": ["现货"]},
        {"type": "stock_sim", "name": "A股模拟 (待对接)", "category": "stock", "features": ["模拟交易"]},
        {"type": "stock_hx", "name": "华鑫证券奇点 (待对接)", "category": "stock", "features": ["量化API"]},
        {"type": "stock_ths", "name": "同花顺 easytrader (待对接)", "category": "stock", "features": ["模拟键鼠"]},
    ]
