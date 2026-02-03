#!/bin/bash
# 量化监控系统 - GitHub推送脚本

echo "🚀 准备推送量化监控系统到GitHub..."

# 检查是否在项目目录
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

# 检查Git状态
echo "📊 检查Git状态..."
git status

# 询问GitHub用户名
read -p "请输入你的GitHub用户名: " github_username

if [ -z "$github_username" ]; then
    echo "❌ 错误：需要GitHub用户名"
    exit 1
fi

# 设置远程仓库
echo "🔗 设置远程仓库..."
git remote remove origin 2>/dev/null
git remote add origin "https://github.com/${github_username}/quant-monitor-system.git"

# 尝试推送
echo "📤 推送代码到GitHub..."
echo "注意：如果仓库不存在，推送会失败。"
echo "请确保已创建仓库：https://github.com/new"
echo "仓库名：quant-monitor-system"
echo ""
read -p "按Enter键继续推送，或Ctrl+C取消..."

# 推送代码
if git push -u origin main; then
    echo ""
    echo "✅ 推送成功！"
    echo "🌐 仓库地址：https://github.com/${github_username}/quant-monitor-system"
    echo ""
    echo "🎉 量化监控系统已成功部署到GitHub！"
    echo ""
    echo "下一步："
    echo "1. 安装依赖：pip install -r requirements.txt"
    echo "2. 配置环境：cp .env.example .env"
    echo "3. 启动系统：python start.py"
else
    echo ""
    echo "❌ 推送失败！可能的原因："
    echo "  1. 仓库尚未创建"
    echo "  2. 认证失败"
    echo "  3. 网络问题"
    echo ""
    echo "解决方案："
    echo "1. 创建仓库：访问 https://github.com/new"
    echo "2. 仓库名填写：quant-monitor-system"
    echo "3. 描述：量化信息实时监控系统"
    echo "4. 选择Public（公开）"
    echo "5. 创建后重新运行此脚本"
fi