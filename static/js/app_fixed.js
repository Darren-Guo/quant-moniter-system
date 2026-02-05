/**
 * 量化监控系统 - 修复版前端JavaScript
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
        // 启动监控按钮
        document.getElementById('startMonitoring')?.addEventListener('click', () => {
            this.startMonitoring();
        });
        
        // 停止监控按钮
        document.getElementById('stopMonitoring')?.addEventListener('click', () => {
            this.stopMonitoring();
        });
        
        // 添加股票按钮
        document.getElementById('addStock')?.addEventListener('click', () => {
            this.addStock();
        });
        
        // 清除警报按钮
        document.getElementById('clearAlerts')?.addEventListener('click', () => {
            this.clearAlerts();
        });
    }
    
    initChart() {
        const ctx = document.getElementById('priceChart')?.getContext('2d');
        if (!ctx) return;
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: '股票价格走势'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: '价格 ($)'
                        }
                    }
                }
            }
        });
    }
    
    loadSystemStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'running') {
                    this.updateStatus('系统运行中', 'running');
                }
            })
            .catch(error => {
                console.error('加载系统状态失败:', error);
                this.updateStatus('系统状态未知', 'unknown');
            });
    }
    
    updateStatus(message, statusClass) {
        const statusElement = document.getElementById('systemStatus');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `status ${statusClass}`;
        }
    }
    
    handleStockUpdate(data) {
        const { symbol, data: stockData, timestamp } = data;
        
        // 更新股票数据
        this.stocks[symbol] = {
            ...stockData,
            symbol: symbol,
            lastUpdate: timestamp
        };
        
        // 更新股票显示
        this.updateStockDisplay();
        
        // 更新图表数据
        this.updateChartData(symbol, stockData);
    }
    
    handleAlert(data) {
        this.alerts.push(data);
        this.updateAlertsDisplay();
        
        // 显示通知
        if (Notification.permission === 'granted') {
            new Notification(`股票警报: ${data.symbol}`, {
                body: data.message,
                icon: '/static/images/alert.png'
            });
        }
    }
    
    updateStockDisplay() {
        const stocksContainer = document.getElementById('stocksContainer');
        const stocks = Object.values(this.stocks);
        
        if (stocks.length === 0) {
            stocksContainer.innerHTML = '<div class="empty-state">暂无股票数据，请启动监控</div>';
            return;
        }
        
        stocksContainer.innerHTML = stocks.map(stock => this.createStockCard(stock)).join('');
    }
    
    createStockCard(stock) {
        // 从data对象中获取数据，如果data不存在则使用stock对象
        const stockData = stock.data || stock;
        const price = stockData.price || 0;
        const change = stockData.change || 0;
        const changePercent = stockData.change_percent || stockData.changePercent || 0;
        const high = stockData.high || 0;
        const low = stockData.low || 0;
        const volume = stockData.volume || 0;
        const marketCap = stockData.market_cap || stockData.marketCap || 0;
        const lastUpdate = stock.lastUpdate || stock.timestamp || new Date().toISOString();
        
        // 获取股票名称 - 优先使用data.name，其次使用data.company，最后使用symbol
        let stockName = stock.symbol;
        if (stock.data) {
            stockName = stock.data.name || stock.data.company || stock.symbol;
        }
        
        // 备用名称映射
        const stockNames = {
            '9988.HK': '阿里巴巴 (港股)',
            '1810.HK': '小米集团',
            'AAPL': '苹果公司',
            'NVDA': '英伟达',
            'XPEV': '小鹏汽车',
            'BABA': '阿里巴巴 (美股)',
            'MI': '小米 (美股)',
            'GOOGL': '谷歌',
            'MSFT': '微软',
            'AMZN': '亚马逊'
        };
        
        // 如果从data中没获取到名称，使用映射
        if (stockName === stock.symbol && stockNames[stock.symbol]) {
            stockName = stockNames[stock.symbol];
        }
        
        const changeClass = change >= 0 ? 'positive' : 'negative';
        const changeSign = change >= 0 ? '+' : '';
        
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
                <div class="stock-price">$${price?.toFixed(2) || 'N/A'}</div>
                <div class="stock-info">
                    <div>
                        <div>最高: $${high?.toFixed(2) || 'N/A'}</div>
                        <div>最低: $${low?.toFixed(2) || 'N/A'}</div>
                    </div>
                    <div>
                        <div>成交量: ${this.formatVolume(volume)}</div>
                        <div>市值: ${this.formatMarketCap(marketCap)}</div>
                    </div>
                </div>
                <div class="stock-update">
                    <div>更新时间: ${new Date(lastUpdate).toLocaleTimeString()}</div>
                </div>
            </div>
        `;
    }
    
    formatVolume(volume) {
        if (volume >= 1000000) {
            return (volume / 1000000).toFixed(1) + 'M';
        } else if (volume >= 1000) {
            return (volume / 1000).toFixed(1) + 'K';
        }
        return volume;
    }
    
    formatMarketCap(marketCap) {
        if (marketCap >= 1000000000) {
            return '$' + (marketCap / 1000000000).toFixed(1) + 'B';
        } else if (marketCap >= 1000000) {
            return '$' + (marketCap / 1000000).toFixed(1) + 'M';
        }
        return '$' + marketCap;
    }
    
    updateChartData(symbol, stockData) {
        const price = stockData.price;
        if (!price) return;
        
        const now = new Date().toLocaleTimeString();
        
        if (!this.chartData[symbol]) {
            this.chartData[symbol] = {
                label: symbol,
                data: [],
                borderColor: this.getRandomColor(),
                fill: false
            };
        }
        
        this.chartData[symbol].data.push({
            x: now,
            y: price
        });
        
        // 保持最近20个数据点
        if (this.chartData[symbol].data.length > 20) {
            this.chartData[symbol].data.shift();
        }
        
        this.updateChart();
    }
    
    updateChart() {
        if (!this.chart) return;
        
        const datasets = Object.values(this.chartData);
        if (datasets.length === 0) return;
        
        // 使用第一个数据集的时间戳作为标签
        const labels = datasets[0].data.map(point => point.x);
        
        this.chart.data.labels = labels;
        this.chart.data.datasets = datasets;
        this.chart.update();
    }
    
    getRandomColor() {
        const colors = [
            '#4FD1C7', '#F6AD55', '#FC8181', '#68D391',
            '#63B3ED', '#B794F4', '#F687B3', '#81E6D9'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }
    
    updateMarketOverview(data) {
        const overviewElement = document.getElementById('marketOverview');
        if (overviewElement) {
            overviewElement.innerHTML = `
                <div>监控股票: ${data.total_stocks || 0}</div>
                <div>总市值: $${(data.total_value || 0).toFixed(2)}</div>
                <div>平均涨跌: ${(data.average_change || 0).toFixed(2)}%</div>
                <div>活跃连接: ${data.active_clients || 0}</div>
            `;
        }
    }
    
    updateAlertsDisplay() {
        const alertsContainer = document.getElementById('alertsContainer');
        if (!alertsContainer) return;
        
        alertsContainer.innerHTML = this.alerts.map(alert => `
            <div class="alert">
                <div class="alert-symbol">${alert.symbol}</div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</div>
            </div>
        `).join('');
    }
    
    startMonitoring() {
        if (!this.isConnected) {
            alert('请先连接到服务器');
            return;
        }
        
        fetch('/api/start-monitoring', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.isMonitoring = true;
                this.updateStatus('监控已启动', 'monitoring');
                alert('监控已启动');
            }
        })
        .catch(error => {
            console.error('启动监控失败:', error);
            alert('启动监控失败: ' + error.message);
        });
    }
    
    stopMonitoring() {
        fetch('/api/stop-monitoring', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.isMonitoring = false;
                this.updateStatus('监控已停止', 'stopped');
                alert('监控已停止');
            }
        })
        .catch(error => {
            console.error('停止监控失败:', error);
            alert('停止监控失败: ' + error.message);
        });
    }
    
    addStock() {
        const symbolInput = document.getElementById('stockSymbol');
        const symbol = symbolInput?.value.trim().toUpperCase();
        
        if (!symbol) {
            alert('请输入股票代码');
            return;
        }
        
        if (this.stocks[symbol]) {
            alert(`股票 ${symbol} 已在监控列表中`);
            return;
        }
        
        // 发送订阅请求
        this.socket.emit('subscribe_stock', { symbol });
        symbolInput.value = '';
    }
    
    clearAlerts() {
        this.alerts = [];
        this.updateAlertsDisplay();
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.QuantMonitorApp = new QuantMonitorApp();
});