#!/bin/bash
# 量化监控系统Web应用启动脚本

echo "🚀 启动量化监控系统Web应用..."
echo "========================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查Python依赖..."
pip3 install -r requirements.txt --quiet

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs data

# 设置环境变量
export PYTHONPATH=$(pwd):$PYTHONPATH

# 显示配置信息
echo ""
echo "📊 系统配置信息:"
echo "----------------------------------------"
echo "Web服务器地址: http://localhost:8080"
echo "API接口地址: http://localhost:8080/api/"
echo "WebSocket地址: ws://localhost:8080"
echo "监控股票: 港股、美股、中概股"
echo "默认端口: 8080"
echo "----------------------------------------"

# 启动Web服务器
echo ""
echo "🌐 启动Web服务器..."
echo "按 Ctrl+C 停止服务器"
echo "========================================"

# 运行Web应用
python3 web_app.py