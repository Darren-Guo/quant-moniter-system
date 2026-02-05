#!/usr/bin/env python3
"""
简化的WebSocket服务器，使用模拟数据
"""

import asyncio
import aiohttp
from aiohttp import web
import socketio
import json
import random
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Socket.IO服务器
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='aiohttp')
app = web.Application()
sio.attach(app)

# 模拟股票数据 - 使用前端期望的股票代码
STOCKS = [
    {'symbol': 'AAPL', 'name': '苹果公司', 'price': 185.0, 'change': 0.0, 'change_percent': 0.0},
    {'symbol': 'NVDA', 'name': '英伟达', 'price': 415.0, 'change': 0.0, 'change_percent': 0.0},
    {'symbol': 'XPEV', 'name': '小鹏汽车', 'price': 155.0, 'change': 0.0, 'change_percent': 0.0},
    {'symbol': 'BABA', 'name': '阿里巴巴', 'price': 175.0, 'change': 0.0, 'change_percent': 0.0},
    {'symbol': '9988.HK', 'name': '阿里巴巴 (港股)', 'price': 75.0, 'change': 0.0, 'change_percent': 0.0},
    {'symbol': '1810.HK', 'name': '小米集团', 'price': 15.0, 'change': 0.0, 'change_percent': 0.0},
]

# 连接管理
connected_clients = set()

@sio.event
async def connect(sid, environ):
    """客户端连接"""
    connected_clients.add(sid)
    logger.info(f"客户端 {sid} 已连接，当前连接数: {len(connected_clients)}")
    
    # 发送欢迎消息
    await sio.emit('connected', {
        'message': '欢迎使用量化监控系统',
        'timestamp': datetime.now().isoformat(),
        'stocks_count': len(STOCKS)
    }, room=sid)
    
    # 发送初始股票数据
    for stock in STOCKS:
        stock_update = {
            'symbol': stock['symbol'],
            'data': {
                'name': stock['name'],
                'company': stock['name'],  # 添加company字段
                'price': round(stock['price'], 2),
                'change': round(stock['change'], 2),
                'change_percent': round(stock['change_percent'], 2),
                'volume': random.randint(1000, 100000),
                'market_cap': random.randint(1000000000, 5000000000),
                'high': round(stock['price'] * 1.02, 2),
                'low': round(stock['price'] * 0.98, 2)
            },
            'timestamp': datetime.now().isoformat()
        }
        await sio.emit('stock_update', stock_update, room=sid)

@sio.event
async def disconnect(sid):
    """客户端断开连接"""
    if sid in connected_clients:
        connected_clients.remove(sid)
    logger.info(f"客户端 {sid} 已断开，剩余连接数: {len(connected_clients)}")

@sio.event
async def start_monitoring(sid, data):
    """开始监控"""
    logger.info(f"客户端 {sid} 请求开始监控: {data}")
    
    # 发送确认消息
    await sio.emit('monitoring_started', {
        'message': '监控已启动',
        'timestamp': datetime.now().isoformat(),
        'stocks': [s['symbol'] for s in STOCKS]
    }, room=sid)
    
    return {'status': 'success', 'message': '监控已启动'}

@sio.event
async def stop_monitoring(sid, data):
    """停止监控"""
    logger.info(f"客户端 {sid} 请求停止监控")
    
    await sio.emit('monitoring_stopped', {
        'message': '监控已停止',
        'timestamp': datetime.now().isoformat()
    }, room=sid)
    
    return {'status': 'success', 'message': '监控已停止'}

@sio.event
async def get_stock_data(sid, data):
    """获取股票数据"""
    symbol = data.get('symbol', 'AAPL')
    
    # 查找股票
    stock = next((s for s in STOCKS if s['symbol'] == symbol), None)
    if stock:
        # 模拟价格波动
        change = random.uniform(-2.0, 2.0)
        new_price = max(0.1, stock['price'] + change)
        change_percent = (change / stock['price']) * 100
        
        # 更新股票数据
        stock['price'] = new_price
        stock['change'] = change
        stock['change_percent'] = change_percent
        
        return {
            'status': 'success',
            'symbol': symbol,
            'price': round(new_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'timestamp': datetime.now().isoformat()
        }
    else:
        return {'status': 'error', 'message': f'未找到股票: {symbol}'}

async def send_market_updates():
    """定期发送市场更新"""
    while True:
        if connected_clients:
            # 生成市场摘要
            total_value = sum(s['price'] for s in STOCKS)
            avg_change = sum(s['change_percent'] for s in STOCKS) / len(STOCKS)
            
            market_summary = {
                'timestamp': datetime.now().isoformat(),
                'total_stocks': len(STOCKS),
                'total_value': round(total_value, 2),
                'average_change': round(avg_change, 2),
                'active_clients': len(connected_clients)
            }
            
            # 发送市场摘要
            await sio.emit('market_summary', market_summary)
            
            # 发送股票更新（随机选择几只股票）
            stocks_to_update = random.sample(STOCKS, min(3, len(STOCKS)))
            for stock in stocks_to_update:
                # 模拟价格波动
                change = random.uniform(-1.5, 1.5)
                new_price = max(0.1, stock['price'] + change)
                change_percent = (change / stock['price']) * 100
                
                # 更新股票数据
                stock['price'] = new_price
                stock['change'] = change
                stock['change_percent'] = change_percent
                
                stock_update = {
                    'symbol': stock['symbol'],
                    'data': {
                        'name': stock['name'],
                        'company': stock['name'],  # 添加company字段
                        'price': round(new_price, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2),
                        'volume': random.randint(1000, 100000),
                        'market_cap': random.randint(1000000000, 5000000000),
                        'high': round(new_price * 1.02, 2),
                        'low': round(new_price * 0.98, 2)
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                await sio.emit('stock_update', stock_update)
        
        # 等待3秒
        await asyncio.sleep(3)

# REST API端点
async def handle_status(request):
    """状态检查"""
    return web.json_response({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'connected_clients': len(connected_clients),
        'monitored_stocks': len(STOCKS)
    })

async def handle_start_monitoring(request):
    """开始监控"""
    return web.json_response({
        'status': 'success',
        'message': '监控已启动',
        'timestamp': datetime.now().isoformat(),
        'stocks': [s['symbol'] for s in STOCKS]
    })

async def handle_stop_monitoring(request):
    """停止监控"""
    return web.json_response({
        'status': 'success',
        'message': '监控已停止',
        'timestamp': datetime.now().isoformat()
    })

async def handle_get_stocks(request):
    """获取所有股票"""
    return web.json_response({
        'status': 'success',
        'stocks': STOCKS,
        'timestamp': datetime.now().isoformat()
    })

async def index(request):
    """主页"""
    return web.FileResponse('/root/.openclaw/workspace/quant_monitor/templates/index.html')

async def test_data(request):
    """测试数据页面"""
    return web.FileResponse('/root/.openclaw/workspace/quant_monitor/test_data.html')

async def static_files(request):
    """静态文件"""
    path = request.match_info.get('path', '')
    file_path = f'/root/.openclaw/workspace/quant_monitor/static/{path}'
    
    try:
        return web.FileResponse(file_path)
    except:
        return web.Response(status=404)

# 设置路由
app.router.add_get('/', index)
app.router.add_get('/test_data.html', test_data)
app.router.add_get('/api/status', handle_status)
app.router.add_post('/api/start-monitoring', handle_start_monitoring)
app.router.add_post('/api/stop-monitoring', handle_stop_monitoring)
app.router.add_get('/api/stocks', handle_get_stocks)
app.router.add_get('/static/{path:.*}', static_files)

async def start_background_tasks(app):
    """启动后台任务"""
    app['market_updates'] = asyncio.create_task(send_market_updates())

async def cleanup_background_tasks(app):
    """清理后台任务"""
    app['market_updates'].cancel()
    await app['market_updates']

if __name__ == '__main__':
    # 添加启动和清理钩子
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    logger.info("🚀 启动简化的量化监控WebSocket服务器...")
    logger.info("🌐 访问地址: http://localhost:8080")
    logger.info("📡 WebSocket已启用，使用模拟数据")
    logger.info("💡 提示: 打开浏览器访问上述地址开始监控")
    
    web.run_app(app, host='0.0.0.0', port=8080)