/**
 * 量化监控系统 - 前端JavaScript
 */

class QuantMonitorApp {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isMonitoring = false;
        this.stocks = {};
        this.alerts = [];
        this.chart = null;
        this.chartData = {};
        
        this.init();
    }
    
    init() {
        // 初始化Socket.IO连接
        this.connectSocket();
        
        // 初始化事件监听器
        this.initEventListeners();
        
        // 初始化图表
        this.initChart();
        
        // 加载系统状态
        this.loadSystemStatus();
    }
    
    connectSocket() {
        // 连接到WebSocket服务器
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('✅ 已连接到服务器');
            this.isConnected = true;
            this.updateStatus('已连接', 'connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('❌ 服务器连接断开');
            this.isConnected = false;
            this.updateStatus('连接断开', 'disconnected');
        });
        
        this.socket.on('connected', (data) => {
            console.log('服务器消息:', data.message);
        });
        
        this.socket.on('stock_update', (data) => {
            this.handleStockUpdate(data);
        });
        
        this.socket.on('alert', (data) => {
            this.handleAlert(data);
        });
        
        this.socket.on('market_summary', (data) => {
            this.updateMarketOverview(data);
        });
        
        this.socket.on('stock_subscribed', (data) => {
            console.log(`已订阅股票: ${data.symbol}`);
        });
        
        this.socket.on('stock_unsubscribed', (data) => {
            console.log(`已取消订阅股票: ${data.symbol}`);
        });
    }
    
    initEventListeners() {
        // 监听股票输入框回车键
        document.getElementById('symbolInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.startMonitoring();
            }
        });
        
        // 定期更新系统信息
        setInterval(() => {
            this.loadSystemStatus();
        }, 10000); // 每10秒更新一次
    }
    
    initChart() {
        const ctx = document.getElementById('priceChart').getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '价格',
                        data: [],
                        borderColor: '#4fd1c7',
                        backgroundColor: 'rgba(79, 209, 199, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: '成交量',
                        data: [],
                        borderColor: '#4299e1',
                        backgroundColor: 'rgba(66, 153, 225, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#a0aec0'
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(26, 32, 44, 0.9)',
                        titleColor: '#e6e6e6',
                        bodyColor: '#cbd5e0',
                        borderColor: '#4a5568',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(74, 85, 104, 0.3)'
                        },
                        ticks: {
                            color: '#a0aec0'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: 'rgba(74, 85, 104, 0.3)'
                        },
                        ticks: {
                            color: '#a0aec0'
                        },
                        title: {
                            display: true,
                            text: '价格 ($)',
                            color: '#a0aec0'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#a0aec0'
                        },
                        title: {
                            display: true,
                            text: '成交量',
                            color: '#a0aec0'
                        }
                    }
                }
            }
        });
    }
    
    updateStatus(status, type = 'info') {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        statusText.textContent = status;
        
        // 更新状态点颜色
        statusDot.className = 'status-dot';
        if (type === 'connected') {
            statusDot.classList.add('connected');
        } else if (type === 'disconnected') {
            statusDot.classList.add('stopped');
        } else if (type === 'monitoring') {
            statusDot.style.background = '#ed8936';
        }
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            this.updateSystemInfo(data);
            
            // 更新监控状态
            this.isMonitoring = data.status === 'running';
            if (this.isMonitoring) {
                this.updateStatus('监控中', 'monitoring');
            } else if (this.isConnected) {
                this.updateStatus('已连接', 'connected');
            }
            
        } catch (error) {
            console.error('获取系统状态失败:', error);
        }
    }
    
    updateSystemInfo(data) {
        const systemInfo = document.getElementById('systemInfo');
        
        const infoItems = [
            { label: '系统状态', value: data.status === 'running' ? '运行中' : '已停止' },
            { label: '监控股票', value: data.monitored_symbols?.length || 0 },
            { label: '活跃告警', value: data.active_alerts || 0 },
            { label: '最后更新', value: data.last_update ? new Date(data.last_update).toLocaleTimeString() : '无' },
            { label: '运行时间', value: data.uptime || '未运行' },
            { label: '服务器时间', value: new Date(data.server_time).toLocaleTimeString() }
        ];
        
        systemInfo.innerHTML = infoItems.map(item => `
            <div class="info-item">
                <span class="info-label">${item.label}</span>
                <span class="info-value">${item.value}</span>
            </div>
        `).join('');
    }
    
    async startMonitoring() {
        const symbolInput = document.getElementById('symbolInput');
        const symbols = symbolInput.value
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0);
        
        if (symbols.length === 0) {
            alert('请输入至少一个股票代码');
            return;
        }
        
        try {
            const response = await fetch('/api/start-monitoring', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ symbols })
            });
            
            const data = await response.json();
            
            if (data.status === 'started') {
                this.isMonitoring = true;
                this.updateStatus('监控中', 'monitoring');
                
                // 清空股票容器显示加载状态
                const stocksContainer = document.getElementById('stocksContainer');
                stocksContainer.innerHTML = `
                    <div class="loading">
                        <i class="fas fa-sync fa-spin"></i>
                        <p>开始监控 ${symbols.length} 只股票...</p>
                    </div>
                `;
                
                // 订阅股票
                symbols.forEach(symbol => {
                    this.socket.emit('subscribe_stock', { symbol });
                });
                
                alert(`✅ ${data.message}`);
            } else {
                alert(`❌ ${data.message}`);
            }
            
        } catch (error) {
            console.error('启动监控失败:', error);
            alert('启动监控失败，请检查服务器连接');
        }
    }
    
    async stopMonitoring() {
        if (!confirm('确定要停止监控吗？')) {
            return;
        }
        
        try {
            const response = await fetch('/api/stop-monitoring', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'stopped') {
                this.isMonitoring = false;
                this.updateStatus('已连接', 'connected');
                
                // 重置股票容器
                const stocksContainer = document.getElementById('stocksContainer');
                stocksContainer.innerHTML = `
                    <div class="loading">
                        <i class="fas fa-sync fa-spin"></i>
                        <p>监控已停止</p>
                    </div>
                `;
                
                alert('✅ 监控已停止');
            }
            
        } catch (error) {
            console.error('停止监控失败:', error);
            alert('停止监控失败');
        }
    }
    
    handleStockUpdate(data) {
        const { symbol, data: stockData, timestamp } = data;
        
        // 更新股票数据
        this.stocks[symbol] = {
            ...stockData,
            lastUpdate: timestamp
        };
        
        // 更新股票显示
        this.updateStockDisplay();
        
        // 更新图表数据
        this.updateChartData(symbol, stockData);
    }
    
    updateStockDisplay() {
        const stocksContainer = document.getElementById('stocksContainer');
        const stocks = Object.values(this.stocks);
        
        if (stocks.length === 0) {
            stocksContainer.innerHTML = `
                <div class="loading">
                    <i class="fas fa-eye"></i>
                    <p>等待股票数据...</p>
                </div>
            `;
            return;
        }
        
        stocksContainer.innerHTML = `
            <div class="stock-grid">
                ${stocks.map(stock => this.createStockCard(stock)).join('')}
            </div>
        `;
    }
    
    createStockCard(stock) {
        const change = stock.change || 0;
        const changePercent = stock.changePercent || 0;
        const changeClass = change >= 0 ? 'positive' : 'negative';
        const changeSign = change >= 0 ? '+' : '';
        
        // 获取股票名称映射
        const stockNames = {
            '9988.HK': '阿里巴巴 (港股)',
            '1810.HK': '小米集团',
            'AAPL': '苹果公司',
            'NVDA': '英伟达',
            'XPEV': '小鹏汽车',
            'BABA': '阿里巴巴 (美股)',
            'MI': '小米 (美股)'
        };
        
        const stockName = stockNames[stock.symbol] || stock.symbol;
        
        return `
            <div class="stock-card">
                <div class="stock-header">
                    <div>
                        <div class="stock-symbol">${stock.symbol}</div>
                        <div class="stock-name">${stockName}</div>
                    </div>
                    <div class="stock-change ${changeClass}">
                        ${changeSign}${change.toFixed(2)} (${changeSign}${changePercent.toFixed(2)}%)
                    </div>
                </div>
                <div class="stock-price">$${stock.price?.toFixed(2) || 'N/A'}</div>
                <div class="stock-info">
                    <div>
                        <div>最高: $${stock.high?.toFixed(2) || 'N/A'}</div>
                        <div>最低: $${stock.low?.toFixed(2) || 'N/A'}</div>
                    </div>
                    <div>
                        <div>成交量: ${this.formatVolume(stock.volume)}</div>
                        <div>市值: ${this.formatMarketCap(stock.marketCap)}</div>
                    </div>
                </div>
                <div class="stock-info">
                    <div>更新时间: ${new Date(stock.lastUpdate).toLocaleTimeString()}</div>
                </div>
            </div>
        `;
    }
    
    formatVolume(volume) {
        if (!volume) return 'N/A';
        if (volume >= 1e9) return (volume / 1e9).toFixed(2) + 'B';
        if (volume >= 1e6) return (volume / 1e6).toFixed(2) + 'M';
        if (volume >= 1e3) return (volume / 1e3).toFixed(2) + 'K';
        return volume.toString();
    }
    
    formatMarketCap(marketCap) {
        if (!marketCap) return 'N/A';
        if (marketCap >= 1e12) return '$' + (marketCap / 1e12).toFixed(2) + 'T';
        if (marketCap >= 1e9) return '$' + (marketCap / 1e9).toFixed(2) + 'B';
        if (marketCap >= 1e6) return '$' + (marketCap / 1e6).toFixed(2) + 'M';
        return '$' + marketCap.toString();
    }
    
    updateChartData(symbol, stockData) {
        if (!this.chartData[symbol]) {
            this.chartData[symbol] = {
                prices: [],
                volumes: [],
                timestamps: []
            };
        }
        
        const data = this.chartData[symbol];
        const now = new Date();
        
        // 添加新数据点
        data.prices.push(stockData.price || 0);
        data.volumes.push(stockData.volume || 0);
        data.timestamps.push(now.toLocaleTimeString());
        
        // 只保留最近20个数据点
        if (data.prices.length > 20) {
            data.prices.shift();
            data.volumes.shift();
            data.timestamps.shift();
        }
        
        // 更新图表
        this.chart.data.labels = data.timestamps;
        this.chart.data.datasets[0].data = data.prices;
        this.chart.data.datasets[1].data = data.volumes;
        this.chart.update();
    }
    
    handleAlert(alert) {
        // 添加新告警到数组开头
        this.alerts.unshift(alert);
        
        // 只保留最近20条告警
        if (this.alerts.length > 20) {
            this.alerts.pop();
        }
        
        // 更新告警显示
        this.updateAlertsDisplay();
        
        // 显示桌面通知（如果浏览器支持）
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`股票告警: ${alert.symbol}`, {
                body: alert.message,
                icon: '/static/images/alert-icon.png'
            });
        }
    }
    
    updateAlertsDisplay() {
        const alertsContainer = document.getElementById('alertsContainer');
        
        if (this.alerts.length === 0) {
            alertsContainer.innerHTML = `
                <div class="loading">
                    <i class="fas fa-bell"></i>
                    <p>暂无告警</p>
                </div>
            `;
            return;
        }
        
        alertsContainer.innerHTML = this.alerts.map(alert => `
            <div class="alert-item ${alert.type || 'warning'}">
                <div class="alert-header">
                    <span class="alert-symbol">${alert.symbol}</span>
                    <span class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="alert-message">${alert.message}</div>
            </div>
        `).join('');
    }
    
    updateMarketOverview(data) {
        const marketOverview = document.getElementById('marketOverview');
        
        marketOverview.innerHTML = `
            <div class="system-info">
                <div class="info-item">
                    <span class="info-label">监控股票数</span>
                    <span class="info-value">${data.stocks_count}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">今日告警</span>
                    <span class="info-value">${data.alerts_count}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">最后更新</span>
                    <span class="info-value">${new Date(data.last_update).toLocaleTimeString()}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">数据延迟</span>
                    <span class="info-value">< 1秒</span>
                </div>
            </div>
        `;
    }
    
    // 请求通知权限
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new QuantMonitorApp();
    
    // 请求通知权限
    if ('Notification' in window) {
        Notification.requestPermission();
    }
    
    // 全局函数供HTML按钮调用
    window.startMonitoring = () => app.startMonitoring();
    window.stopMonitoring = () => app.stopMonitoring();
});