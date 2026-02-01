"""
加密货币数据采集器
"""
import ccxt
import pandas as pd

class CryptoCollector:
    def __init__(self):
        self.exchanges = {
            "binance": ccxt.binance(),
            "huobi": ccxt.huobi(),
            "okx": ccxt.okx()
        }
    
    def get_price(self, symbol: str = "BTC/USDT"):
        """获取单个币种价格"""
        data = {}
        for name, exchange in self.exchanges.items():
            try:
                ticker = exchange.fetch_ticker(symbol)
                data[name] = {
                    "price": ticker["last"],
                    "volume": ticker["baseVolume"],
                    "change_pct": ticker["percentage"]
                }
            except Exception as e:
                print(f"Error fetching from {name}: {e}")
        return data
    
    def get_top_coins(self, limit: int = 10):
        """获取主流币种"""
        symbols = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT",
            "ADA/USDT", "SOL/USDT", "DOGE/USDT", "DOT/USDT",
            "MATIC/USDT", "LTC/USDT"
        ]
        
        data = []
        for symbol in symbols[:limit]:
            try:
                ticker = self.exchanges["binance"].fetch_ticker(symbol)
                data.append({
                    "symbol": symbol,
                    "price": ticker["last"],
                    "change_24h": ticker["percentage"],
                    "volume": ticker["baseVolume"]
                })
            except Exception as e:
                print(f"Error: {e}")
        
        return data

if __name__ == "__main__":
    collector = CryptoCollector()
    print(collector.get_top_coins())
