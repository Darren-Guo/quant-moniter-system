"""
量化监控系统配置
"""

import os
from pathlib import Path
from typing import Dict, List

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据源配置
DATA_SOURCES = {
    "yfinance": {
        "enabled": True,
        "timeout": 10,
        "retry_count": 3
    },
    "ccxt": {
        "enabled": True,
        "exchanges": ["binance", "okx", "huobi"],
        "timeout": 10
    }
}

# 监控标的配置
MONITOR_SYMBOLS = {
    "stocks": [
        "AAPL",  # 苹果
        "MSFT",  # 微软
        "GOOGL", # 谷歌
        "AMZN",  # 亚马逊
        "TSLA",  # 特斯拉
        "NVDA",  # 英伟达
        "META",  # Meta
        "BABA",  # 阿里巴巴
        "TSM",   # 台积电
        "0050.TW" # 台湾50
    ],
    "crypto": [
        "BTC/USDT",
        "ETH/USDT",
        "BNB/USDT",
        "SOL/USDT",
        "XRP/USDT"
    ],
    "indices": [
        "^GSPC",  # S&P 500
        "^IXIC",  # NASDAQ
        "^DJI",   # 道琼斯
        "^HSI",   # 恒生指数
        "^TWII"   # 台湾加权指数
    ]
}

# 监控频率配置（秒）
MONITOR_INTERVALS = {
    "realtime": 5,      # 实时数据（5秒）
    "minute": 60,       # 分钟数据
    "hourly": 3600,     # 小时数据
    "daily": 86400      # 日数据
}

# 告警配置
ALERT_CONFIG = {
    "price_change_threshold": 0.05,  # 5%价格变动
    "volume_spike_threshold": 2.0,   # 2倍成交量异常
    "rsi_overbought": 70,           # RSI超买线
    "rsi_oversold": 30,             # RSI超卖线
    "notification_channels": ["console", "log"]  # 告警通道
}

# 存储配置
STORAGE_CONFIG = {
    "redis": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": 0
    },
    "database": {
        "url": os.getenv("DATABASE_URL", "sqlite:///data/monitor.db"),
        "echo": False
    }
}

# API配置
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": True,
    "cors_origins": ["http://localhost:3000"]
}

# Web应用配置
WEB_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "debug": True,
    "static_path": "static",
    "templates_path": "templates"
}

# 监控配置
MONITOR_CONFIG = {
    "update_interval": 10,  # 数据更新间隔（秒）
    "max_stocks": 20,       # 最大监控股票数量
    "data_retention_days": 7,  # 数据保留天数
    "cache_ttl": 300        # 缓存过期时间（秒）
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/monitor.log",
    "max_size": 10485760,  # 10MB
    "backup_count": 5
}