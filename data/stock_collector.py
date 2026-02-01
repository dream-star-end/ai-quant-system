"""
A股数据采集器
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class StockCollector:
    def __init__(self):
        self.symbols = {
            "沪深300": "000300.SS",
            "上证指数": "000001.SS",
            "深证成指": "399001.SZ",
            "创业板指": "399006.SZ",
            "茅台": "600519.SS",
            "宁德时代": "300750.SZ",
            "腾讯": "0700.HK",
            "阿里巴巴": "9988.HK"
        }
    
    def get_index(self, name: str):
        """获取指数数据"""
        if name not in self.symbols:
            return {"error": "Unknown index"}
        
        symbol = self.symbols[name]
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")
        
        return {
            "name": name,
            "symbol": symbol,
            "data": hist.to_dict(orient="records")
        }
    
    def get_stocks(self, symbols: list = None):
        """批量获取股票数据"""
        if symbols is None:
            symbols = list(self.symbols.values())
        
        data = {}
        for name, symbol in self.symbols.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if not hist.empty:
                    latest = hist.iloc[-1]
                    data[name] = {
                        "price": latest["Close"],
                        "change": latest["Close"] - hist.iloc[-2]["Close"] if len(hist) > 1 else 0
                    }
            except Exception as e:
                print(f"Error fetching {name}: {e}")
        
        return data

if __name__ == "__main__":
    collector = StockCollector()
    print(collector.get_stocks())
