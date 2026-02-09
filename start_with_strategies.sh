#!/bin/bash

echo "🚀 启动量化监控系统（含策略系统）"
echo "=================================="

# 激活虚拟环境
if [ -f "venv2/bin/activate" ]; then
    echo "✅ 激活虚拟环境..."
    source venv2/bin/activate
else
    echo "❌ 虚拟环境不存在，请先创建虚拟环境"
    exit 1
fi

# 检查依赖
echo "✅ 检查Python依赖..."
python3 -c "import aiohttp, socketio, yfinance, ccxt" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  正在安装依赖..."
    pip install -r requirements.txt
fi

# 启动Web应用
echo "✅ 启动Web应用..."
echo ""
echo "============================================================"
echo "🌐 量化监控系统 - Web应用"
echo "============================================================"
echo "服务器地址: http://0.0.0.0:8080"
echo "功能:"
echo "  • 实时股票数据监控 (港股、美股)"
echo "  • WebSocket实时数据推送"
echo "  • REST API数据查询"
echo "  • 可视化图表展示"
echo "  • 价格异常告警"
echo "  • 量化策略管理"
echo "  • 策略绩效跟踪"
echo "============================================================"
echo ""

python3 web_app.py