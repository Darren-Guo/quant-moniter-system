#!/usr/bin/env python3
"""
支持WebSocket的量化监控系统Web服务器
"""

import asyncio
import json
import random
import logging
from datetime import datetime
from aiohttp import web
import socketio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Socket.IO服务器
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')

# 模拟股票数据
STOCK_TEMPLATES = {
    "9988.HK": {"name": "阿里巴巴", "base": 85.0, "volatility": 0.02},
    "1810.HK": {"name": "小米集团", "base": 15.5, "volatility": 0.03},
    "AAPL": {"name": "苹果公司", "base": 185.0, "volatility": 0.01},
    "NVDA": {"name": "英伟达", "base": 650.0, "volatility": 0.025},
    "XPEV": {"name": "小鹏汽车", "base": 12.5, "volatility": 0.04},
    "BABA": {"name": "阿里巴巴", "base": 78.0, "volatility": 0.02},
    "MI": {"name": "小米", "base": 14.2, "volatility": 0.025},
    "TSLA": {"name": "特斯拉", "base": 210.0, "volatility": 0.03},
    "MSFT": {"name": "微软", "base": 420.0, "volatility": 0.015},
    "GOOGL": {"name": "谷歌", "base": 150.0, "volatility": 0.018}
}

current_prices = {symbol: template["base"] for symbol, template in STOCK_TEMPLATES.items()}

class QuantWebSocketServer:
    def __init__(self):
        self.app = web.Application()
        self.sio = sio
        self.sio.attach(self.app)
        self.is_monitoring = False
        self.monitored_symbols = []
        self.monitoring_task = None
        
        self.setup_socketio_events()
        self.setup_routes()
        
    def setup_socketio_events(self):
        """设置Socket.IO事件处理器"""
        
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"客户端连接: {sid}")
            await self.sio.emit('connected', {'message': 'Connected to Quant Monitor'}, room=sid)
            
        @self.sio.event
        async def disconnect(sid):
            logger.info(f"客户端断开: {sid}")
            
        @self.sio.event
        async def subscribe_stock(sid, data):
            """订阅股票数据"""
            symbol = data.get('symbol')
            if symbol:
                logger.info(f"客户端 {sid} 订阅股票: {symbol}")
                await self.sio.emit('stock_subscribed', {'symbol': symbol}, room=sid)
                
        @self.sio.event
        async def unsubscribe_stock(sid, data):
            """取消订阅股票数据"""
            symbol = data.get('symbol')
            if symbol:
                logger.info(f"客户端 {sid} 取消订阅股票: {symbol}")
                await self.sio.emit('stock_unsubscribed', {'symbol': symbol}, room=sid)
    
    def setup_routes(self):
        """设置HTTP路由"""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/market-data', self.handle_market_data)
        self.app.router.add_get('/api/alerts', self.handle_alerts)
        self.app.router.add_post('/api/start-monitoring', self.handle_start_monitoring)
        self.app.router.add_post('/api/stop-monitoring', self.handle_stop_monitoring)
        self.app.router.add_static('/static/', './static')
        
    async def handle_index(self, request):
        return web.FileResponse('./templates/index.html')
    
    async def handle_status(self, request):
        status = {
            "status": "running" if self.is_monitoring else "stopped",
            "monitored_symbols": self.monitored_symbols,
            "active_alerts": random.randint(0, 3),
            "last_update": datetime.now().isoformat(),
            "server_time": datetime.now().isoformat(),
            "uptime": "0:05:23" if self.is_monitoring else None
        }
        return web.json_response(status)
    
    async def handle_market_data(self, request):
        data = {
            "stocks": {},
            "alerts": [],
            "last_update": datetime.now().isoformat()
        }
        
        for symbol in self.monitored_symbols:
            if symbol in STOCK_TEMPLATES:
                stock_data = self.generate_stock_data(symbol)
                data["stocks"][symbol] = stock_data
                
                # 随机生成告警
                if random.random() < 0.2:
                    alert = self.generate_alert(symbol, stock_data)
                    if alert:
                        data["alerts"].append(alert)
        
        return web.json_response(data)
    
    async def handle_alerts(self, request):
        alerts = []
        for _ in range(random.randint(0, 5)):
            symbol = random.choice(list(STOCK_TEMPLATES.keys()))
            stock_data = self.generate_stock_data(symbol)
            alert = self.generate_alert(symbol, stock_data)
            if alert:
                alerts.append(alert)
        
        return web.json_response({"alerts": alerts, "count": len(alerts)})
    
    async def handle_start_monitoring(self, request):
        try:
            data = await request.json()
            symbols = data.get('symbols', [])
            
            if not symbols:
                # 使用默认股票
                symbols = ["9988.HK", "1810.HK", "AAPL", "NVDA", "XPEV", "MI"]
            
            self.monitored_symbols = symbols
            self.is_monitoring = True
            
            logger.info(f"开始监控股票: {symbols}")
            
            # 启动监控任务
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            self.monitoring_task = asyncio.create_task(self.monitoring_loop(symbols))
            
            return web.json_response({
                "status": "started",
                "message": f"开始监控 {len(symbols)} 只股票",
                "symbols": symbols
            })
            
        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_stop_monitoring(self, request):
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
        
        logger.info("监控已停止")
        
        return web.json_response({
            "status": "stopped",
            "message": "监控已停止"
        })
    
    def generate_stock_data(self, symbol):
        """生成模拟股票数据"""
        template = STOCK_TEMPLATES.get(symbol, {"name": symbol, "base": 100.0, "volatility": 0.02})
        
        # 更新价格
        old_price = current_prices.get(symbol, template["base"])
        change_percent = random.uniform(-template["volatility"], template["volatility"])
        new_price = old_price * (1 + change_percent)
        current_prices[symbol] = new_price
        
        change = new_price - old_price
        
        return {
            "symbol": symbol,
            "name": template["name"],
            "price": round(new_price, 2),
            "change": round(change, 2),
            "changePercent": round(change_percent * 100, 2),
            "high": round(new_price * random.uniform(1.0, 1.02), 2),
            "low": round(new_price * random.uniform(0.98, 1.0), 2),
            "open": round(old_price, 2),
            "volume": random.randint(1000000, 10000000),
            "marketCap": round(new_price * random.uniform(1e9, 1e11), 2),
            "timestamp": datetime.now().isoformat(),
            "exchange": "HK" if ".HK" in symbol else "US",
            "currency": "HKD" if ".HK" in symbol else "USD"
        }
    
    def generate_alert(self, symbol, stock_data):
        """生成模拟告警"""
        alert_types = [
            ("price_drop", f"{stock_data['name']} 价格下跌超过3%", stock_data['changePercent'] < -3),
            ("price_surge", f"{stock_data['name']} 价格上涨超过3%", stock_data['changePercent'] > 3),
            ("volume_spike", f"{stock_data['name']} 成交量异常放大", random.random() < 0.3)
        ]
        
        for alert_type, message, condition in alert_types:
            if condition and random.random() < 0.5:
                alert = {
                    "symbol": symbol,
                    "type": alert_type,
                    "message": message,
                    "severity": "high" if "price" in alert_type else "medium",
                    "timestamp": datetime.now().isoformat()
                }
                
                # 通过WebSocket发送告警
                asyncio.create_task(self.sio.emit('alert', alert))
                
                return alert
        
        return None
    
    async def monitoring_loop(self, symbols):
        """监控循环，定期更新股票数据"""
        logger.info(f"启动监控循环，监控 {len(symbols)} 只股票")
        
        while self.is_monitoring:
            try:
                for symbol in symbols:
                    if symbol in STOCK_TEMPLATES:
                        # 生成股票数据
                        stock_data = self.generate_stock_data(symbol)
                        
                        # 通过WebSocket发送更新
                        await self.sio.emit('stock_update', {
                            'symbol': symbol,
                            'data': stock_data,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # 生成告警
                        alert = self.generate_alert(symbol, stock_data)
                        if alert:
                            # 告警已通过generate_alert函数发送
                            pass
                
                # 发送市场摘要
                await self.sio.emit('market_summary', {
                    'stocks_count': len(symbols),
                    'alerts_count': random.randint(0, 3),
                    'last_update': datetime.now().isoformat()
                })
                
                # 等待3秒后再次更新
                await asyncio.sleep(3)
                
            except asyncio.CancelledError:
                logger.info("监控循环被取消")
                break
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(5)
    
    async def start(self):
        """启动服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        
        logger.info("🚀 量化监控系统WebSocket服务器已启动")
        logger.info("🌐 访问地址: http://localhost:8080")
        logger.info("📡 WebSocket已启用，支持实时数据推送")
        logger.info("📊 默认监控股票: 阿里巴巴(9988.HK), 小米(1810.HK), 苹果(AAPL), 英伟达(NVDA)")
        logger.info("💡 提示: 打开浏览器访问 http://localhost:8080 开始监控")
        
        # 保持服务器运行
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            logger.info("🛑 服务器停止")
        finally:
            await runner.cleanup()

async def main():
    server = QuantWebSocketServer()
    await server.start()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌐 量化监控系统 - WebSocket版本")
    print("="*60)
    print("服务器地址: http://localhost:8080")
    print("WebSocket: ws://localhost:8080/socket.io/")
    print("实时数据: 支持股票价格实时推送")
    print("按 Ctrl+C 停止服务器")
    print("="*60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")