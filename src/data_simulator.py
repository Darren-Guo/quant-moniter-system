"""
数据模拟器 - 为演示提供模拟股票数据
"""

import asyncio
import random
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataSimulator:
    """股票数据模拟器"""
    
    def __init__(self):
        self.stock_templates = {
            # 港股
            "9988.HK": {
                "name": "阿里巴巴",
                "base_price": 85.0,
                "volatility": 0.02,
                "volume_base": 5000000,
                "sector": "科技"
            },
            "1810.HK": {
                "name": "小米集团",
                "base_price": 15.5,
                "volatility": 0.03,
                "volume_base": 3000000,
                "sector": "消费电子"
            },
            "0700.HK": {
                "name": "腾讯控股",
                "base_price": 320.0,
                "volatility": 0.015,
                "volume_base": 8000000,
                "sector": "科技"
            },
            
            # 美股
            "AAPL": {
                "name": "苹果公司",
                "base_price": 185.0,
                "volatility": 0.01,
                "volume_base": 10000000,
                "sector": "科技"
            },
            "NVDA": {
                "name": "英伟达",
                "base_price": 650.0,
                "volatility": 0.025,
                "volume_base": 5000000,
                "sector": "半导体"
            },
            "TSLA": {
                "name": "特斯拉",
                "base_price": 210.0,
                "volatility": 0.03,
                "volume_base": 4000000,
                "sector": "汽车"
            },
            
            # 中概股
            "XPEV": {
                "name": "小鹏汽车",
                "base_price": 12.5,
                "volatility": 0.04,
                "volume_base": 2000000,
                "sector": "汽车"
            },
            "BABA": {
                "name": "阿里巴巴",
                "base_price": 78.0,
                "volatility": 0.02,
                "volume_base": 6000000,
                "sector": "电商"
            },
            "MI": {
                "name": "小米",
                "base_price": 14.2,
                "volatility": 0.025,
                "volume_base": 2500000,
                "sector": "消费电子"
            }
        }
        
        self.current_prices = {}
        self.initialize_prices()
    
    def initialize_prices(self):
        """初始化股票价格"""
        for symbol, template in self.stock_templates.items():
            # 在基础价格附近随机初始化
            variation = random.uniform(-0.05, 0.05)
            self.current_prices[symbol] = template["base_price"] * (1 + variation)
    
    async def fetch_stock_data(self, symbol: str) -> Dict[str, Any]:
        """获取模拟股票数据"""
        if symbol not in self.stock_templates:
            logger.warning(f"未知股票代码: {symbol}")
            return None
        
        template = self.stock_templates[symbol]
        
        # 生成随机价格变动
        volatility = template["volatility"]
        price_change = random.uniform(-volatility, volatility)
        
        # 更新当前价格
        old_price = self.current_prices.get(symbol, template["base_price"])
        new_price = old_price * (1 + price_change)
        self.current_prices[symbol] = new_price
        
        # 生成成交量（在基础成交量附近随机）
        volume_variation = random.uniform(0.5, 1.5)
        volume = int(template["volume_base"] * volume_variation)
        
        # 生成其他数据
        change = new_price - old_price
        change_percent = (change / old_price) * 100 if old_price > 0 else 0
        
        # 生成高低价
        high = new_price * random.uniform(1.0, 1.02)
        low = new_price * random.uniform(0.98, 1.0)
        
        # 生成市值（基于价格和随机因子）
        market_cap = new_price * random.uniform(1e9, 1e11)
        
        # 生成技术指标
        rsi = random.uniform(30, 70)
        macd = random.uniform(-2, 2)
        
        return {
            "symbol": symbol,
            "name": template["name"],
            "price": round(new_price, 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "open": round(old_price, 2),
            "volume": volume,
            "marketCap": round(market_cap, 2),
            "sector": template["sector"],
            "rsi": round(rsi, 2),
            "macd": round(macd, 2),
            "timestamp": datetime.now().isoformat(),
            "exchange": "HK" if ".HK" in symbol else "US",
            "currency": "HKD" if ".HK" in symbol else "USD"
        }
    
    async def fetch_multiple_stocks(self, symbols: list) -> Dict[str, Dict[str, Any]]:
        """获取多个股票数据"""
        results = {}
        
        for symbol in symbols:
            data = await self.fetch_stock_data(symbol)
            if data:
                results[symbol] = data
        
        return results
    
    async def generate_alert(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成模拟告警"""
        alert_types = [
            {
                "type": "price_drop",
                "message": f"{data['name']} 价格下跌超过3%",
                "threshold": -3.0
            },
            {
                "type": "price_surge", 
                "message": f"{data['name']} 价格上涨超过3%",
                "threshold": 3.0
            },
            {
                "type": "volume_spike",
                "message": f"{data['name']} 成交量异常放大",
                "threshold": 1.5
            },
            {
                "type": "rsi_overbought",
                "message": f"{data['name']} RSI超过70，可能超买",
                "threshold": 70
            },
            {
                "type": "rsi_oversold",
                "message": f"{data['name']} RSI低于30，可能超卖", 
                "threshold": 30
            }
        ]
        
        # 随机决定是否生成告警（20%概率）
        if random.random() < 0.2:
            alert_type = random.choice(alert_types)
            
            # 检查是否满足告警条件
            should_alert = False
            
            if alert_type["type"] == "price_drop" and data["changePercent"] < alert_type["threshold"]:
                should_alert = True
            elif alert_type["type"] == "price_surge" and data["changePercent"] > alert_type["threshold"]:
                should_alert = True
            elif alert_type["type"] == "rsi_overbought" and data.get("rsi", 50) > alert_type["threshold"]:
                should_alert = True
            elif alert_type["type"] == "rsi_oversold" and data.get("rsi", 50) < alert_type["threshold"]:
                should_alert = True
            elif alert_type["type"] == "volume_spike":
                # 对于成交量告警，我们随机生成
                should_alert = random.random() < 0.3
            
            if should_alert:
                return {
                    "symbol": symbol,
                    "type": alert_type["type"],
                    "message": alert_type["message"],
                    "severity": "high" if "price" in alert_type["type"] else "medium",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "price": data["price"],
                        "changePercent": data["changePercent"],
                        "volume": data["volume"]
                    }
                }
        
        return None


# 单例实例
simulator = DataSimulator()