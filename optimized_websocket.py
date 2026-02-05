#!/usr/bin/env python3
"""
优化的量化监控系统WebSocket服务器
集成智能刷新、数据缓存和真实API数据
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from aiohttp import web
import socketio

from config.settings import MONITOR_SYMBOLS, WEB_CONFIG
from src.enhanced_data_fetcher import enhanced_fetcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Socket.IO服务器
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')


class OptimizedQuantWebSocketServer:
    """优化的量化WebSocket服务器"""
    
    def __init__(self):
        self.app = web.Application()
        self.sio = sio
        self.sio.attach(self.app)
        
        # 监控状态
        self.is_monitoring = False
        self.monitored_symbols = set()
        self.user_sessions = {}  # sid -> {subscribed_symbols, ...}
        self.monitoring_task = None
        
        # 初始化数据获取器
        self.data_fetcher = enhanced_fetcher
        
        # 设置事件处理器和路由
        self.setup_socketio_events()
        self.setup_routes()
        
        logger.info("初始化优化的WebSocket服务器")
    
    def setup_socketio_events(self):
        """设置Socket.IO事件处理器"""
        
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"客户端连接: {sid}")
            self.user_sessions[sid] = {
                'subscribed_symbols': set(),
                'connected_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            await self.sio.emit('connected', {
                'message': 'Connected to Optimized Quant Monitor',
                'server_time': datetime.now().isoformat(),
                'features': ['smart_refresh', 'real_data', 'caching']
            }, room=sid)
            
        @self.sio.event
        async def disconnect(sid):
            logger.info(f"客户端断开: {sid}")
            if sid in self.user_sessions:
                # 从监控列表中移除用户订阅的标的
                user_symbols = self.user_sessions[sid]['subscribed_symbols']
                for symbol in user_symbols:
                    self._update_symbol_subscription(symbol, remove=True)
                del self.user_sessions[sid]
            
        @self.sio.event
        async def subscribe_stock(sid, data):
            """订阅股票数据"""
            symbol = data.get('symbol')
            if symbol:
                logger.info(f"客户端 {sid} 订阅股票: {symbol}")
                
                # 更新用户会话
                if sid in self.user_sessions:
                    self.user_sessions[sid]['subscribed_symbols'].add(symbol)
                    self.user_sessions[sid]['last_activity'] = datetime.now().isoformat()
                
                # 更新监控列表
                self.monitored_symbols.add(symbol)
                self.data_fetcher.update_user_activity(symbol)
                
                # 立即发送当前数据
                stock_data = await self.data_fetcher.fetch_stock_data_with_cache(symbol)
                if stock_data:
                    await self.sio.emit('stock_update', {
                        'symbol': symbol,
                        'data': stock_data,
                        'timestamp': datetime.now().isoformat(),
                        'priority': 'immediate'
                    }, room=sid)
                
                await self.sio.emit('stock_subscribed', {
                    'symbol': symbol,
                    'message': f'已订阅 {symbol} 实时数据',
                    'refresh_interval': self.data_fetcher.priority_manager.get_refresh_interval(symbol)
                }, room=sid)
                
        @self.sio.event
        async def unsubscribe_stock(sid, data):
            """取消订阅股票数据"""
            symbol = data.get('symbol')
            if symbol and sid in self.user_sessions:
                logger.info(f"客户端 {sid} 取消订阅股票: {symbol}")
                self.user_sessions[sid]['subscribed_symbols'].discard(symbol)
                self._update_symbol_subscription(symbol)
                await self.sio.emit('stock_unsubscribed', {'symbol': symbol}, room=sid)
        
        @self.sio.event
        async def get_stock_data(sid, data):
            """立即获取股票数据（不订阅）"""
            symbol = data.get('symbol')
            if symbol:
                stock_data = await self.data_fetcher.fetch_stock_data_with_cache(symbol)
                if stock_data:
                    await self.sio.emit('stock_data_response', {
                        'symbol': symbol,
                        'data': stock_data,
                        'timestamp': datetime.now().isoformat()
                    }, room=sid)
        
        @self.sio.event
        async def get_system_status(sid, data):
            """获取系统状态"""
            status = self.get_system_status()
            await self.sio.emit('system_status', status, room=sid)
    
    def _update_symbol_subscription(self, symbol: str, remove: bool = False):
        """更新标的订阅状态"""
        # 检查是否还有其他用户订阅此标的
        still_subscribed = False
        for session in self.user_sessions.values():
            if symbol in session['subscribed_symbols']:
                still_subscribed = True
                break
        
        if not still_subscribed and symbol in self.monitored_symbols:
            self.monitored_symbols.remove(symbol)
            logger.info(f"标的 {symbol} 已无用户订阅，从监控列表移除")
    
    def setup_routes(self):
        """设置HTTP路由"""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/market-data', self.handle_market_data)
        self.app.router.add_get('/api/system-stats', self.handle_system_stats)
        self.app.router.add_get('/api/alerts', self.handle_alerts)
        self.app.router.add_post('/api/start-monitoring', self.handle_start_monitoring)
        self.app.router.add_post('/api/stop-monitoring', self.handle_stop_monitoring)
        self.app.router.add_static('/static/', Path(__file__).parent / 'static')
    
    async def handle_index(self, request):
        return web.FileResponse('./templates/index.html')
    
    async def handle_status(self, request):
        status = self.get_system_status()
        return web.json_response(status)
    
    async def handle_market_data(self, request):
        """获取市场数据（HTTP API）"""
        symbols = list(self.monitored_symbols)[:20]  # 限制返回数量
        market_data = {}
        
        for symbol in symbols:
            data = await self.data_fetcher.fetch_stock_data_with_cache(symbol)
            if data:
                market_data[symbol] = data
        
        return web.json_response({
            'data': market_data,
            'count': len(market_data),
            'timestamp': datetime.now().isoformat()
        })
    
    async def handle_system_stats(self, request):
        """获取系统统计信息"""
        stats = self.data_fetcher.get_refresh_stats()
        stats.update({
            'active_users': len(self.user_sessions),
            'monitored_symbols': len(self.monitored_symbols),
            'is_monitoring': self.is_monitoring,
            'server_time': datetime.now().isoformat()
        })
        return web.json_response(stats)
    
    async def handle_alerts(self, request):
        """获取告警信息（模拟）"""
        import random
        alerts = []
        alert_types = [
            ("价格异常", "high", ["AAPL", "MSFT", "GOOGL"]),
            ("成交量放大", "medium", ["TSLA", "NVDA"]),
            ("技术指标信号", "low", ["AMZN", "META"])
        ]
        
        for alert_type, severity, symbols in alert_types:
            if random.random() < 0.3:  # 30%概率生成告警
                symbol = random.choice(symbols)
                alerts.append({
                    "id": f"alert_{len(alerts)+1}",
                    "symbol": symbol,
                    "type": alert_type,
                    "message": f"{symbol} 检测到{alert_type}",
                    "severity": severity,
                    "timestamp": datetime.now().isoformat()
                })
        
        return web.json_response({
            'alerts': alerts,
            'count': len(alerts),
            'timestamp': datetime.now().isoformat()
        })
    
    async def handle_start_monitoring(self, request):
        """启动监控"""
        if self.is_monitoring:
            return web.json_response({
                'status': 'error',
                'message': '监控已在运行中'
            })
        
        try:
            data = await request.json()
            symbols = data.get('symbols', [])
            
            if symbols:
                self.monitored_symbols.update(symbols)
            
            # 启动监控任务
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
            
            return web.json_response({
                'status': 'success',
                'message': '监控已启动',
                'monitored_symbols': list(self.monitored_symbols),
                'started_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': f'启动监控失败: {str(e)}'
            })
    
    async def handle_stop_monitoring(self, request):
        """停止监控"""
        if not self.is_monitoring:
            return web.json_response({
                'status': 'error',
                'message': '监控未在运行'
            })
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        return web.json_response({
            'status': 'success',
            'message': '监控已停止',
            'stopped_at': datetime.now().isoformat()
        })
    
    def get_system_status(self):
        """获取系统状态"""
        return {
            "status": "running" if self.is_monitoring else "stopped",
            "monitored_symbols": list(self.monitored_symbols),
            "active_users": len(self.user_sessions),
            "last_update": datetime.now().isoformat(),
            "server_time": datetime.now().isoformat(),
            "data_source": "yfinance (15min delay)" if self.data_fetcher.use_real_data else "simulator",
            "features": ["smart_refresh", "caching", "priority_management"],
            "version": "2.0.0"
        }
    
    async def monitoring_loop(self):
        """智能监控循环"""
        logger.info(f"启动智能监控循环，监控 {len(self.monitored_symbols)} 个标的")
        
        # 初始获取所有数据
        initial_data = {}
        for symbol in self.monitored_symbols:
            data = await self.data_fetcher.fetch_stock_data_with_cache(symbol)
            if data:
                initial_data[symbol] = data
        
        # 广播初始数据
        if initial_data:
            await self.sio.emit('initial_data', {
                'data': initial_data,
                'count': len(initial_data),
                'timestamp': datetime.now().isoformat()
            })
        
        # 上次刷新时间跟踪
        last_refresh = {symbol: 0 for symbol in self.monitored_symbols}
        
        while self.is_monitoring:
            try:
                refresh_tasks = []
                
                for symbol in list(self.monitored_symbols):
                    # 检查是否需要刷新
                    if self.data_fetcher.priority_manager.should_refresh(symbol, last_refresh.get(symbol, 0)):
                        refresh_tasks.append(symbol)
                
                if refresh_tasks:
                    logger.debug(f"本轮需要刷新 {len(refresh_tasks)} 个标的: {refresh_tasks[:5]}...")
                    
                    # 并发获取数据
                    for symbol in refresh_tasks:
                        data = await self.data_fetcher.fetch_stock_data_with_cache(symbol)
                        if data:
                            last_refresh[symbol] = time.time()
                            
                            # 通过WebSocket发送更新
                            await self.sio.emit('stock_update', {
                                'symbol': symbol,
                                'data': data,
                                'timestamp': datetime.now().isoformat(),
                                'priority': self.data_fetcher.priority_manager.priorities.get(symbol, 'low')
                            })
                
                # 发送系统状态更新（每分钟一次）
                current_time = time.time()
                if current_time - getattr(self, '_last_status_update', 0) > 60:
                    status = self.get_system_status()
                    await self.sio.emit('system_status', status)
                    self._last_status_update = current_time
                
                # 智能等待：根据活跃度调整等待时间
                active_symbols = len([s for s in self.monitored_symbols 
                                    if self.data_fetcher.priority_manager.priorities.get(s, 'low') in ['high', 'medium']])
                
                if active_symbols > 0:
                    wait_time = max(1, 10 - min(active_symbols, 5))  # 活跃标的多时等待时间短
                else:
                    wait_time = 5  # 默认5秒
                
                await asyncio.sleep(wait_time)
                
            except asyncio.CancelledError:
                logger.info("监控循环被取消")
                break
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(5)
    
    async def start(self):
        """启动服务器"""
        # 初始化数据获取器
        await self.data_fetcher.initialize()
        
        # 启动Web服务器
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, WEB_CONFIG['host'], WEB_CONFIG['port'])
        await site.start()
        
        logger.info("🚀 优化的量化监控系统WebSocket服务器已启动")
        logger.info(f"🌐 访问地址: http://{WEB_CONFIG['host']}:{WEB_CONFIG['port']}")
        logger.info("📡 WebSocket已启用，支持智能刷新和实时数据推送")
        logger.info("💾 数据缓存已启用，减少API调用")
        logger.info("🎯 智能优先级管理：根据用户活动和价格波动调整刷新频率")
        logger.info("💡 提示: 打开浏览器访问上述地址开始监控")
        
        # 启动默认监控
        if not self.is_monitoring:
            self.monitored_symbols.update(MONITOR_SYMBOLS["stocks"][:4])  # 默认监控前4只股票
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
            logger.info(f"已启动默认监控: {list(self.monitored_symbols)}")
        
        # 保持服务器运行
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            logger.info("🛑 服务器停止")
        finally:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            await self.data_fetcher.cleanup()
            await runner.cleanup()


import time  # 在文件顶部添加

async def main():
    server = OptimizedQuantWebSocketServer()
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        sys.exit(1)