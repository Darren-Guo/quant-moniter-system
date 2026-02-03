# 量化信息实时监控系统

一个基于Python的实时量化监控系统，用于监控股票、加密货币和指数的市场数据，并提供实时告警功能。

## 🚀 功能特性

### 📊 数据监控
- **多市场覆盖**: 股票、加密货币、指数
- **实时数据**: 5秒间隔实时监控
- **多时间帧**: 分钟、小时、日级别数据
- **技术指标**: 自动计算RSI、MACD、布林带等指标

### ⚠️ 智能告警
- **价格异常**: 检测异常价格变动
- **成交量异常**: 识别成交量暴增
- **技术信号**: RSI超买超卖、MACD金叉死叉
- **分级告警**: 高、中、低三个严重等级

### 🛠️ 系统特性
- **模块化设计**: 易于扩展和维护
- **异步处理**: 高性能并发监控
- **配置驱动**: 灵活配置监控标的和参数
- **多数据源**: 支持yfinance、ccxt等数据源

## 📁 项目结构

```
quant_monitor/
├── src/                    # 源代码
│   ├── main.py           # 主程序入口
│   ├── data_fetcher.py   # 数据获取模块
│   ├── monitor.py        # 监控核心模块
│   └── alert_manager.py  # 告警管理模块
├── config/               # 配置文件
│   └── settings.py      # 系统设置
├── data/                # 数据存储
├── logs/                # 日志文件
├── tests/               # 测试文件
├── requirements.txt     # Python依赖
├── .env.example         # 环境变量示例
├── start.py            # 启动脚本
└── README.md           # 项目说明
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境
```bash
cp .env.example .env
# 编辑.env文件，配置API密钥等参数
```

### 3. 启动系统
```bash
# 方式1: 使用启动脚本
python start.py

# 方式2: 直接运行主程序
python -m src.main
```

### 4. 监控标的配置
编辑 `config/settings.py` 中的 `MONITOR_SYMBOLS` 配置：
```python
MONITOR_SYMBOLS = {
    "stocks": ["AAPL", "MSFT", "GOOGL"],
    "crypto": ["BTC/USDT", "ETH/USDT"],
    "indices": ["^GSPC", "^IXIC"]
}
```

## ⚙️ 配置说明

### 监控频率
```python
MONITOR_INTERVALS = {
    "realtime": 5,      # 5秒实时监控
    "minute": 60,       # 1分钟监控
    "hourly": 3600,     # 1小时监控
    "daily": 86400      # 1天监控
}
```

### 告警阈值
```python
ALERT_CONFIG = {
    "price_change_threshold": 0.05,  # 5%价格变动告警
    "volume_spike_threshold": 2.0,   # 2倍成交量异常
    "rsi_overbought": 70,           # RSI超买线
    "rsi_oversold": 30,             # RSI超卖线
}
```

## 📈 监控指标

### 技术指标
- **移动平均线**: SMA(20), SMA(50), EMA(12), EMA(26)
- **MACD**: 趋势跟踪动量指标
- **RSI**: 相对强弱指数
- **布林带**: 波动率指标
- **成交量均值**: 20周期平均成交量

### 告警类型
1. **价格异常**: 价格快速变动超过阈值
2. **成交量异常**: 成交量暴增超过平均
3. **RSI超买超卖**: RSI超过70或低于30
4. **MACD信号**: 金叉买入信号，死叉卖出信号

## 🔧 扩展开发

### 添加新数据源
1. 在 `data_fetcher.py` 中添加新的数据获取方法
2. 在 `settings.py` 中配置数据源参数
3. 在 `monitor.py` 中集成新的数据源

### 添加新告警规则
1. 在 `monitor.py` 的 `_check_*` 方法中添加新规则
2. 在 `settings.py` 中配置告警阈值
3. 在 `alert_manager.py` 中处理新告警类型

### 添加通知渠道
1. 在 `alert_manager.py` 中添加新的通知方法
2. 在 `settings.py` 中配置通知渠道
3. 在 `.env` 中配置渠道参数

## 📊 输出示例

```
🔴 [高危] 2024-01-01T10:30:00
   标的: crypto:BTC/USDT
   类型: price_abnormal
   信息: crypto:BTC/USDT 价格异常变动: +7.85%
   数据: {
     "current_price": 45000.0,
     "price_change": 0.0785,
     "threshold": 0.05,
     "interval": "realtime"
   }
```

## 🐛 故障排除

### 常见问题
1. **数据获取失败**: 检查网络连接和API密钥
2. **内存占用过高**: 减少监控标的或增加监控间隔
3. **告警过于频繁**: 调整告警阈值

### 日志查看
```bash
tail -f logs/monitor.log
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题，请提交Issue或联系维护者。