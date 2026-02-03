"""
数据获取模块 - 从不同数据源获取市场数据
支持真实数据和模拟数据
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import yfinance as yf
import pandas as pd
import ccxt
from datetime import datetime, timedelta
import random

from config.settings import DATA_SOURCES, MONITOR_SYMBOLS
from .data_simulator import simulator

logger = logging.getLogger(__name__)


class DataFetcher:
    """数据获取器"""
    
    def __init__(self, use_simulator: bool = True):
        self.yfinance_enabled = DATA_SOURCES["yfinance"]["enabled"]
        self.ccxt_enabled = DATA_SOURCES["ccxt"]["enabled"]
        self.ccxt_exchanges = {}
        self.use_simulator = use_simulator
        
    async def initialize(self):
        """初始化数据源"""
        logger.info("初始化数据获取器...")
        
        if self.ccxt_enabled and not self.use_simulator:
            await self._initialize_ccxt()
            
        logger.info("✅ 数据获取器初始化完成")
    
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
    
    async def fetch_stock_data(self, symbol: str, interval: str = "1m") -> Optional[pd.DataFrame]:
        """获取股票数据"""
        if not self.yfinance_enabled or self.use_simulator:
            return None
            
        try:
            ticker = yf.Ticker(symbol)
            
            # 获取最近的数据
            if interval == "1m":
                period = "1d"
            elif interval == "5m":
                period = "5d"
            elif interval == "1h":
                period = "1mo"
            else:  # 1d
                period = "3mo"
            
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"⚠️ 未获取到 {symbol} 的数据")
                return None
                
            # 添加技术指标
            df = self._add_technical_indicators(df)
            return df
            
        except Exception as e:
            logger.error(f"❌ 获取股票数据失败 {symbol}: {e}")
            return None
    
    async def fetch_crypto_data(self, symbol: str, exchange_name: str = "binance", 
                               timeframe: str = "1m") -> Optional[pd.DataFrame]:
        """获取加密货币数据"""
        if not self.ccxt_enabled or exchange_name not in self.ccxt_exchanges or self.use_simulator:
            return None
            
        try:
            exchange = self.ccxt_exchanges[exchange_name]
            
            # 转换时间帧
            if timeframe == "1m":
                limit = 100  # 最近100条1分钟数据
            elif timeframe == "5m":
                limit = 200
            elif timeframe == "1h":
                limit = 168  # 一周的小时数据
            else:  # 1d
                limit = 90   # 3个月的日数据
            
            # 获取K线数据
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                return None
                
            # 转换为DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 添加技术指标
            df = self._add_technical_indicators(df)
            return df
            
        except Exception as e:
            logger.error(f"❌ 获取加密货币数据失败 {symbol}@{exchange_name}: {e}")
            return None
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加技术指标"""
        try:
            # 计算简单移动平均线
            df['SMA_20'] = df['close'].rolling(window=20).mean()
            df['SMA_50'] = df['close'].rolling(window=50).mean()
            
            # 计算指数移动平均线
            df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
            
            # 计算MACD
            df['MACD'] = df['EMA_12'] - df['EMA_26']
            df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_hist'] = df['MACD'] - df['MACD_signal']
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 计算布林带
            df['BB_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
            df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
            
            # 计算成交量均值
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            
        except Exception as e:
            logger.warning(f"⚠️ 计算技术指标时出错: {e}")
            
        return df
    
    async def get_all_symbols_data(self, interval: str = "1m") -> Dict[str, pd.DataFrame]:
        """获取所有监控标的的数据"""
        all_data = {}
        
        # 获取股票数据
        for symbol in MONITOR_SYMBOLS["stocks"]:
            data = await self.fetch_stock_data(symbol, interval)
            if data is not None:
                all_data[f"stock:{symbol}"] = data
        
        # 获取加密货币数据
        for symbol in MONITOR_SYMBOLS["crypto"]:
            data = await self.fetch_crypto_data(symbol, "binance", interval)
            if data is not None:
                all_data[f"crypto:{symbol}"] = data
        
        # 获取指数数据
        for symbol in MONITOR_SYMBOLS["indices"]:
            data = await self.fetch_stock_data(symbol, interval)
            if data is not None:
                all_data[f"index:{symbol}"] = data
        
        logger.info(f"📊 获取到 {len(all_data)} 个标的的数据")
        return all_data
    
    async def fetch_stock_data_for_web(self, symbol: str) -> Optional[Dict[str, Any]]:
        """为Web应用获取股票数据（返回字典格式）"""
        if self.use_simulator:
            # 使用模拟数据
            return await simulator.fetch_stock_data(symbol)
        else:
            # 使用真实数据
            try:
                ticker = yf.Ticker(symbol)
                
                # 获取基本信息
                info = ticker.info
                
                # 获取最新价格
                history = ticker.history(period="1d", interval="1m")
                if history.empty:
                    return None
                
                latest = history.iloc[-1]
                
                # 计算涨跌幅
                if len(history) > 1:
                    prev_close = history.iloc[-2]['close']
                    change = latest['close'] - prev_close
                    change_percent = (change / prev_close) * 100
                else:
                    change = 0
                    change_percent = 0
                
                return {
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
                    "currency": "HKD" if ".HK" in symbol else "USD"
                }
                
            except Exception as e:
                logger.error(f"获取股票数据失败 {symbol}: {e}")
                # 失败时回退到模拟数据
                return await simulator.fetch_stock_data(symbol)
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理数据获取器资源...")
        self.ccxt_exchanges.clear()