#!/usr/bin/env python3
"""
量化监控系统 - Web应用后端
提供API接口和WebSocket实时数据推送
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from aiohttp import web
import aiohttp_cors
import socketio

from config.settings import WEB_CONFIG, MONITOR_CONFIG
from src.data_fetcher import DataFetcher
from src.monitor import QuantMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Socket.IO服务器
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')


class QuantWebApp:
    """量化监控Web应用"""
    
    def __init__(self):
        self.app = web.Application()
        self.sio = sio
        self.data_fetcher = DataFetcher()
        self.monitor = QuantMonitor()
        self.is_running = False
        
        # 存储监控数据
        self.market_data: Dict[str, Any] = {
            "stocks": {},
            "crypto": {},
            "indices": {},
            "alerts": [],
            "last_update": None
        }
        
        # 设置路由
        self.setup_routes()
        self.setup_socketio()
        self.setup_cors()
        
    def setup_routes(self):
        """设置HTTP路由"""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/market-data', self.handle_market_data)
        self.app.router.get('/api/stocks/{symbol}', self.handle_stock_data)
        self.app.router.add_get('/api/alerts', self.handle_alerts)
        self.app.router.add_post('/api/start-monitoring', self.handle_start_monitoring)
        self.app.router.add_post('/api/stop-monitoring', self.handle_stop_monitoring)
        
        # 静态文件服务
        self.app.router.add_static('/static/', Path(__file__).parent / 'static')
        
    def setup_socketio(self):
        """设置Socket.IO事件处理器"""
        self.sio.attach(self.app)
        
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
    
    def setup_cors(self):
        """设置CORS"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def handle_index(self, request):
        """处理首页请求"""
        return web.FileResponse(Path(__file__).parent / 'templates' / 'index.html')
    
    async def handle_status(self, request):
        """获取系统状态"""
        status = {
            "status": "running" if self.is_running else "stopped",
            "uptime": str(datetime.now() - self.start_time) if self.is_running else None,
            "monitored_symbols": list(self.market_data["stocks"].keys()),
            "active_alerts": len(self.market_data["alerts"]),
            "last_update": self.market_data["last_update"],
            "server_time": datetime.now().isoformat()
        }
        return web.json_response(status)
    
    async def handle_market_data(self, request):
        """获取市场数据"""
        return web.json_response(self.market_data)
    
    async def handle_stock_data(self, request):
        """获取特定股票数据"""
        symbol = request.match_info.get('symbol', '').upper()
        
        if symbol in self.market_data["stocks"]:
            return web.json_response(self.market_data["stocks"][symbol])
        else:
            return web.json_response({
                "error": f"Symbol {symbol} not found",
                "available_symbols": list(self.market_data["stocks"].keys())
            }, status=404)
    
    async def handle_alerts(self, request):
        """获取告警信息"""
        return web.json_response({
            "alerts": self.market_data["alerts"],
            "count": len(self.market_data["alerts"])
        })
    
    async def handle_start_monitoring(self, request):
        """启动监控"""
        if self.is_running:
            return web.json_response({
                "status": "already_running",
                "message": "监控已在运行中"
            })
        
        try:
            data = await request.json()
            symbols = data.get('symbols', [])
            
            # 启动数据获取
            await self.data_fetcher.initialize()
            
            # 启动监控任务
            self.is_running = True
            self.start_time = datetime.now()
            
            # 启动后台监控任务
            asyncio.create_task(self.monitoring_task(symbols))
            
            logger.info(f"开始监控股票: {symbols}")
            
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
        """停止监控"""
        if not self.is_running:
            return web.json_response({
                "status": "already_stopped",
                "message": "监控已停止"
            })
        
        self.is_running = False
        await self.data_fetcher.cleanup()
        
        logger.info("监控已停止")
        
        return web.json_response({
            "status": "stopped",
            "message": "监控已停止"
        })
    
    async def monitoring_task(self, symbols: List[str]):
        """后台监控任务"""
        logger.info(f"开始监控任务，监控 {len(symbols)} 只股票")
        
        while self.is_running:
            try:
                # 获取股票数据
                stock_data = {}
                for symbol in symbols:
                    try:
                        data = await self.data_fetcher.fetch_stock_data(symbol)
                        if data:
                            stock_data[symbol] = data
                            
                            # 通过WebSocket实时推送
                            await self.sio.emit('stock_update', {
                                'symbol': symbol,
                                'data': data,
                                'timestamp': datetime.now().isoformat()
                            })
                    except Exception as e:
                        logger.error(f"获取股票 {symbol} 数据失败: {e}")
                
                # 更新市场数据
                self.market_data["stocks"] = stock_data
                self.market_data["last_update"] = datetime.now().isoformat()
                
                # 检查告警
                alerts = await self.monitor.check_alerts(stock_data)
                if alerts:
                    self.market_data["alerts"].extend(alerts)
                    # 保留最近100条告警
                    self.market_data["alerts"] = self.market_data["alerts"][-100:]
                    
                    # 推送告警
                    for alert in alerts:
                        await self.sio.emit('alert', alert)
                
                # 定期广播市场数据摘要
                await self.sio.emit('market_summary', {
                    'stocks_count': len(stock_data),
                    'alerts_count': len(alerts),
                    'last_update': self.market_data["last_update"]
                })
                
                # 等待下一次更新
                await asyncio.sleep(MONITOR_CONFIG.get("update_interval", 10))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控任务出错: {e}")
                await asyncio.sleep(5)
    
    async def start_server(self):
        """启动Web服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(
            runner, 
            WEB_CONFIG.get("host", "0.0.0.0"), 
            WEB_CONFIG.get("port", 8080)
        )
        
        await site.start()
        
        logger.info(f"🚀 Web服务器已启动: http://{WEB_CONFIG.get('host', '0.0.0.0')}:{WEB_CONFIG.get('port', 8080)}")
        logger.info(f"📊 前端访问地址: http://localhost:{WEB_CONFIG.get('port', 8080)}")
        
        # 保持服务器运行
        try:
            await asyncio.Future()  # 永久运行
        except KeyboardInterrupt:
            logger.info("🛑 收到停止信号")
        finally:
            await runner.cleanup()


async def main():
    """主函数"""
    app = QuantWebApp()
    
    print("\n" + "="*60)
    print("🌐 量化监控系统 - Web应用")
    print("="*60)
    print(f"服务器地址: http://{WEB_CONFIG.get('host', '0.0.0.0')}:{WEB_CONFIG.get('port', 8080)}")
    print("功能:")
    print("  • 实时股票数据监控 (港股、美股)")
    print("  • WebSocket实时数据推送")
    print("  • REST API数据查询")
    print("  • 可视化图表展示")
    print("  • 价格异常告警")
    print("="*60)
    
    await app.start_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        sys.exit(1)