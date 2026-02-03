# 量化监控系统 - Web应用

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动Web服务器
```bash
# 方法1: 使用启动脚本
chmod +x start_web.sh
./start_web.sh

# 方法2: 直接运行
python web_app.py
```

### 3. 访问Web界面
打开浏览器访问：http://localhost:8080

## 📊 功能特性

### 前端界面
- ✅ 实时股票数据监控
- ✅ 可视化价格图表
- ✅ 实时告警通知
- ✅ 响应式设计（支持手机/平板）
- ✅ WebSocket实时数据推送

### 监控股票
默认监控以下股票：
- **港股**: 9988.HK (阿里巴巴), 1810.HK (小米)
- **美股**: AAPL (苹果), NVDA (英伟达)
- **中概股**: XPEV (小鹏汽车), BABA (阿里巴巴美股)

### 数据源
- **模拟数据**: 默认使用，无需API密钥
- **真实数据**: 可配置使用Yahoo Finance API

## 🔧 配置说明

### 修改配置文件
编辑 `config/settings.py`：

```python
# Web服务器配置
WEB_CONFIG = {
    "host": "0.0.0.0",  # 允许外部访问
    "port": 8080,       # 端口号
    "debug": True       # 调试模式
}

# 数据源配置
DATA_SOURCES = {
    "yfinance": {
        "enabled": True,  # 启用真实数据
        "timeout": 10
    }
}
```

### 添加监控股票
在Web界面输入框输入股票代码，用逗号分隔：
```
9988.HK, 1810.HK, AAPL, NVDA, XPEV, TSLA
```

## 🌐 API接口

### REST API
- `GET /api/status` - 系统状态
- `GET /api/market-data` - 市场数据
- `GET /api/stocks/{symbol}` - 特定股票数据
- `GET /api/alerts` - 告警信息
- `POST /api/start-monitoring` - 开始监控
- `POST /api/stop-monitoring` - 停止监控

### WebSocket事件
- `stock_update` - 股票数据更新
- `alert` - 新告警
- `market_summary` - 市场摘要
- `subscribe_stock` - 订阅股票
- `unsubscribe_stock` - 取消订阅

## 🐳 Docker部署

### 构建镜像
```bash
docker build -t quant-monitor-web .
```

### 运行容器
```bash
docker run -d -p 8080:8080 --name quant-monitor quant-monitor-web
```

## 🔍 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 修改端口号
   # 编辑 config/settings.py 中的 WEB_CONFIG["port"]
   ```

2. **依赖安装失败**
   ```bash
   # 升级pip
   pip install --upgrade pip
   
   # 使用国内镜像
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

3. **无法访问Web界面**
   ```bash
   # 检查防火墙
   sudo ufw allow 8080
   
   # 检查服务是否运行
   netstat -tlnp | grep 8080
   ```

### 日志查看
```bash
# 查看应用日志
tail -f logs/monitor.log

# 查看系统日志
journalctl -u quant-monitor.service
```

## 📱 移动端访问

系统支持移动端访问，可通过手机浏览器访问：
```
http://<服务器IP>:8080
```

## 🔒 安全建议

1. **生产环境配置**
   - 设置 `debug=False`
   - 配置HTTPS证书
   - 启用身份验证

2. **API限流**
   - 配置Nginx反向代理
   - 启用API密钥验证

3. **数据安全**
   - 定期备份数据
   - 监控系统日志
   - 设置访问白名单

## 📞 技术支持

如有问题，请检查：
1. 查看日志文件 `logs/monitor.log`
2. 检查Python依赖是否完整
3. 确认端口未被占用
4. 检查网络连接

## 📈 后续开发计划

- [ ] 添加用户认证系统
- [ ] 支持更多数据源
- [ ] 添加交易信号生成
- [ ] 支持多语言界面
- [ ] 添加移动端App
- [ ] 集成机器学习模型