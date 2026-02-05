"""
增强版数据获取模块 - 支持缓存、智能刷新和混合数据源
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import yfinance as yf
import pandas as pd
import ccxt
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
import hashlib

from config.settings import DATA_SOURCES, MONITOR_SYMBOLS, MONITOR_CONFIG

logger = logging.getLogger(__name__)


class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/cache", ttl: int = 300):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl  # 缓存过期时间（秒）
        
    def _get_cache_key(self, symbol: str, data_type: str) -> str:
        """生成缓存键"""
        key_str = f"{symbol}_{data_type}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, symbol: str, data_type: str) -> Optional[Dict]:
        """从缓存获取数据"""
        cache_key = self._get_cache_key(symbol, data_type)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # 检查是否过期
            timestamp = data.get('_timestamp', 0)
            if time.time() - timestamp > self.ttl:
                return None
                
            # 移除内部字段
            data.pop('_timestamp', None)
            data.pop('_cache_key', None)
            return data
            
        except Exception as e:
            logger.warning(f"读取缓存失败 {symbol}: {e}")
            return None
    
    def set(self, symbol: str, data_type: str, data: Dict) -> None:
        """设置缓存数据"""
        cache_key = self._get_cache_key(symbol, data_type)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            # 添加元数据
            cache_data = data.copy()
            cache_data['_timestamp'] = time.time()
            cache_data['_cache_key'] = cache_key
            
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, default=str)
                
        except Exception as e:
            logger.warning(f"写入缓存失败 {symbol}: {e}")


class RefreshPriorityManager:
    """刷新优先级管理器"""
    
    def __init__(self):
        self.priorities = {}  # symbol -> priority_level
        self.last_access = {}  # symbol -> last_access_time
        self.price_volatility = {}  # symbol -> volatility_score
        
        # 优先级配置
        self.priority_config = {
            "high": {
                "interval": 10,  # 10秒刷新
                "max_symbols": 5
            },
            "medium": {
                "interval": 30,  # 30秒刷新
                "max_symbols": 10
            },
            "low": {
                "interval": 300,  # 5分钟刷新
                "max_symbols": 50
            }
        }
    
    def update_access(self, symbol: str) -> None:
        """更新标的访问时间"""
        self.last_access[symbol] = time.time()
        
        # 最近访问的标的提高优先级
        if symbol in self.priorities and self.priorities[symbol] != "high":
            self.priorities[symbol] = "medium"
    
    def update_volatility(self, symbol: str, price_change: float) -> None:
        """更新价格波动性评分"""
        if symbol not in self.price_volatility:
            self.price_volatility[symbol] = []
        
        self.price_volatility[symbol].append(abs(price_change))
        
        # 保持最近20个波动记录
        if len(self.price_volatility[symbol]) > 20:
            self.price_volatility[symbol] = self.price_volatility[symbol][-20:]
        
        # 计算平均波动率
        avg_volatility = sum(self.price_volatility[symbol]) / len(self.price_volatility[symbol])
        
        # 根据波动率调整优先级
        if avg_volatility > 0.03:  # 3%以上波动
            self.priorities[symbol] = "high"
        elif avg_volatility > 0.01:  # 1%-3%波动
            if symbol not in self.priorities or self.priorities[symbol] == "low":
                self.priorities[symbol] = "medium"
    
    def get_refresh_interval(self, symbol: str) -> int:
        """获取标的刷新间隔"""
        priority = self.priorities.get(symbol, "low")
        return self.priority_config[priority]["interval"]
    
    def get_priority_symbols(self, priority: str) -> List[str]:
        """获取指定优先级的标的列表"""
        return [s for s, p in self.priorities.items() if p == priority]
    
    def should_refresh(self, symbol: str, last_refresh: float) -> bool:
        """判断是否需要刷新"""
        interval = self.get_refresh_interval(symbol)
        return time.time() - last_refresh >= interval


class EnhancedDataFetcher:
    """增强版数据获取器"""
    
    def __init__(self, use_real_data: bool = True):
        self.use_real_data = use_real_data
        self.cache = DataCache(ttl=MONITOR_CONFIG.get("cache_ttl", 300))
        self.priority_manager = RefreshPriorityManager()
        
        # 初始化数据源
        self.yfinance_enabled = DATA_SOURCES["yfinance"]["enabled"] and use_real_data
        self.ccxt_enabled = DATA_SOURCES["ccxt"]["enabled"] and use_real_data
        self.ccxt_exchanges = {}
        
        # 刷新状态跟踪
        self.last_refresh = {}
        self.last_data = {}
        
        logger.info(f"初始化增强版数据获取器 (使用真实数据: {use_real_data})")
    
    async def initialize(self):
        """初始化数据源"""
        if self.ccxt_enabled:
            await self._initialize_ccxt()
        logger.info("✅ 增强版数据获取器初始化完成")
    
    async def _initialize_ccxt(self):
        """初始化CCXT交易所"""
        for exchange_name in DATA_SOURCES["ccxt"]["exchanges"]:
            try:
                exchange_class = getattr(ccxt, exchange_name)
                exchange = exchange_class({
                    'timeout': DATA_SOURCES["ccxt"]["timeout"] * 1000,
                    'enableRateLimit': True
                })
                self.ccxt_exchanges[exchange_name] = exchange
                logger.info(f"✅ 初始化 {exchange_name} 交易所")
            except Exception as e:
                logger.warning(f"⚠️ 无法初始化 {exchange_name}: {e}")
    
    async def fetch_stock_data_with_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票数据（带缓存）"""
        # 检查缓存
        cached_data = self.cache.get(symbol, "stock")
        if cached_data:
            logger.debug(f"使用缓存数据: {symbol}")
            return cached_data
        
        # 检查是否需要刷新
        last_refresh = self.last_refresh.get(symbol, 0)
        if not self.priority_manager.should_refresh(symbol, last_refresh):
            return self.last_data.get(symbol)
        
        try:
            if not self.yfinance_enabled:
                # 回退到模拟数据
                return await self._generate_simulated_data(symbol)
            
            ticker = yf.Ticker(symbol)
            
            # 获取基本信息
            info = ticker.info
            
            # 获取最新价格数据
            history = ticker.history(period="1d", interval="1m")
            if history.empty:
                logger.warning(f"⚠️ 未获取到 {symbol} 的数据")
                return await self._generate_simulated_data(symbol)
            
            latest = history.iloc[-1]
            
            # 计算涨跌幅
            if len(history) > 1:
                prev_close = history.iloc[-2]['close']
                change = latest['close'] - prev_close
                change_percent = (change / prev_close) * 100
            else:
                change = 0
                change_percent = 0
            
            # 构建返回数据
            stock_data = {
                "symbol": symbol,
                "name": info.get('longName', symbol),
                "price": round(latest['close'], 2),
                "change": round(change, 2),
                "changePercent": round(change_percent, 2),
                "high": round(latest['high'], 2),
                "low": round(latest['low'], 2),
                "open": round(latest['open'], 2),
                "volume": int(latest['volume']),
                "marketCap": info.get('marketCap', 0),
                "sector": info.get('sector', ''),
                "timestamp": datetime.now().isoformat(),
                "exchange": "HK" if ".HK" in symbol else "US",
                "currency": "HKD" if ".HK" in symbol else "USD",
                "dataSource": "yfinance",
                "dataDelay": 15  # yfinance有15分钟延迟
            }
            
            # 更新缓存
            self.cache.set(symbol, "stock", stock_data)
            self.last_refresh[symbol] = time.time()
            self.last_data[symbol] = stock_data
            
            # 更新优先级管理器
            self.priority_manager.update_volatility(symbol, change_percent / 100)
            
            logger.debug(f"获取股票数据成功: {symbol}")
            return stock_data
            
        except Exception as e:
            logger.error(f"❌ 获取股票数据失败 {symbol}: {e}")
            # 失败时使用模拟数据
            return await self._generate_simulated_data(symbol)
    
    async def _generate_simulated_data(self, symbol: str) -> Dict[str, Any]:
        """生成模拟数据（回退方案）"""
        import random
        from datetime import datetime
        
        # 基础价格模板
        base_prices = {
            "AAPL": 185.0, "MSFT": 420.0, "GOOGL": 150.0,
            "AMZN": 175.0, "TSLA": 210.0, "NVDA": 650.0,
            "META": 480.0, "BABA": 78.0, "TSM": 145.0,
            "0050.TW": 135.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        volatility = 0.02  # 2%波动
        
        # 生成随机价格变化
        change_percent = random.uniform(-volatility, volatility)
        new_price = base_price * (1 + change_percent)
        
        return {
            "symbol": symbol,
            "name": symbol,
            "price": round(new_price, 2),
            "change": round(new_price - base_price, 2),
            "changePercent": round(change_percent * 100, 2),
            "high": round(new_price * 1.01, 2),
            "low": round(new_price * 0.99, 2),
            "open": round(base_price, 2),
            "volume": random.randint(1000000, 10000000),
            "marketCap": round(new_price * random.uniform(1e9, 1e11), 2),
            "sector": "Technology",
            "timestamp": datetime.now().isoformat(),
            "exchange": "HK" if ".HK" in symbol else "US",
            "currency": "HKD" if ".HK" in symbol else "USD",
            "dataSource": "simulator",
            "dataDelay": 0
        }
    
    async def fetch_crypto_data_with_cache(self, symbol: str, exchange_name: str = "binance") -> Optional[Dict[str, Any]]:
        """获取加密货币数据（带缓存）"""
        # 检查缓存
        cache_key = f"{symbol}_{exchange_name}"
        cached_data = self.cache.get(cache_key, "crypto")
        if cached_data:
            return cached_data
        
        if not self.ccxt_enabled or exchange_name not in self.ccxt_exchanges:
            return None
        
        try:
            exchange = self.ccxt_exchanges[exchange_name]
            
            # 获取ticker数据
            ticker = exchange.fetch_ticker(symbol)
            
            crypto_data = {
                "symbol": symbol,
                "name": symbol.replace("/", ""),
                "price": round(ticker['last'], 2),
                "change": round(ticker['last'] - ticker['open'], 2),
                "changePercent": round(((ticker['last'] - ticker['open']) / ticker['open']) * 100, 2),
                "high": round(ticker['high'], 2),
                "low": round(ticker['low'], 2),
                "open": round(ticker['open'], 2),
                "volume": round(ticker['baseVolume'], 2),
                "timestamp": datetime.now().isoformat(),
                "exchange": exchange_name,
                "currency": "USDT",
                "dataSource": "ccxt",
                "dataDelay": 1  # 加密货币数据接近实时
            }
            
            # 更新缓存
            self.cache.set(cache_key, "crypto", crypto_data)
            
            return crypto_data
            
        except Exception as e:
            logger.error(f"❌ 获取加密货币数据失败 {symbol}@{exchange_name}: {e}")
            return None
    
    async def get_all_monitoring_data(self) -> Dict[str, Dict[str, Any]]:
        """获取所有监控标的的数据"""
        all_data = {}
        
        # 获取股票数据
        for symbol in MONITOR_SYMBOLS["stocks"]:
            data = await self.fetch_stock_data_with_cache(symbol)
            if data:
                all_data[f"stock:{symbol}"] = data
        
        # 获取加密货币数据
        for symbol in MONITOR_SYMBOLS["crypto"]:
            data = await self.fetch_crypto_data_with_cache(symbol, "binance")
            if data:
                all_data[f"crypto:{symbol}"] = data
        
        # 获取指数数据（使用股票接口）
        for symbol in MONITOR_SYMBOLS["indices"]:
            data = await self.fetch_stock_data_with_cache(symbol)
            if data:
                all_data[f"index:{symbol}"] = data
        
        logger.info(f"📊 获取到 {len(all_data)} 个标的的数据")
        return all_data
    
    def update_user_activity(self, symbol: str) -> None:
        """更新用户活动（提高标的优先级）"""
        self.priority_manager.update_access(symbol)
    
    def get_refresh_stats(self) -> Dict[str, Any]:
        """获取刷新统计信息"""
        stats = {
            "total_symbols": len(self.last_refresh),
            "high_priority": len(self.priority_manager.get_priority_symbols("high")),
            "medium_priority": len(self.priority_manager.get_priority_symbols("medium")),
            "low_priority": len(self.priority_manager.get_priority_symbols("low")),
            "cache_hits": 0,  # 需要实际统计
            "cache_misses": 0,  # 需要实际统计
            "last_refresh": {
                symbol: datetime.fromtimestamp(timestamp).isoformat()
                for symbol, timestamp in list(self.last_refresh.items())[:5]
            }
        }
        return stats
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理增强版数据获取器资源...")
        self.ccxt_exchanges.clear()


# 全局实例
enhanced_fetcher = EnhancedDataFetcher(use_real_data=True)