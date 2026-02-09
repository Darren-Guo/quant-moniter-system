"""
监控核心模块 - 实时监控市场数据
"""

import asyncio
import logging
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta

from config.settings import MONITOR_INTERVALS, MONITOR_SYMBOLS, ALERT_CONFIG
from src.data_fetcher import DataFetcher
from src.alert_manager import AlertManager
from src.smart_refresh import SmartRefreshManager

logger = logging.getLogger(__name__)


class QuantMonitor:
    """量化监控器"""
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.alert_manager = AlertManager()
        self.smart_refresh = SmartRefreshManager()
        self.is_monitoring = False
        self.monitor_tasks = []
        self.market_data = {}
        self.last_update_time = {}
        
    async def start(self):
        """启动监控"""
        logger.info("启动量化监控...")
        
        # 初始化组件
        await self.data_fetcher.initialize()
        await self.alert_manager.initialize()
        await self.smart_refresh.initialize()
        
        self.is_monitoring = True
        
        # 启动不同频率的监控任务
        self.monitor_tasks = [
            asyncio.create_task(self._monitor_realtime()),
            asyncio.create_task(self._monitor_minute()),
            asyncio.create_task(self._monitor_hourly()),
            asyncio.create_task(self._monitor_daily()),
            asyncio.create_task(self._monitor_system_resources())
        ]
        
        logger.info("✅ 量化监控已启动")
    
    async def stop(self):
        """停止监控"""
        logger.info("停止量化监控...")
        self.is_monitoring = False
        
        # 取消所有监控任务
        for task in self.monitor_tasks:
            task.cancel()
        
        # 等待任务完成
        try:
            await asyncio.gather(*self.monitor_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        
        await self.data_fetcher.cleanup()
        await self.alert_manager.cleanup()
        
        logger.info("✅ 量化监控已停止")
    
    async def _monitor_realtime(self):
        """实时监控（智能间隔）"""
        logger.info("启动实时监控（智能间隔）...")
        
        while self.is_monitoring:
            try:
                # 使用智能刷新获取数据
                all_data = {}
                for symbol in MONITOR_SYMBOLS["stocks"][:5]:  # 先监控前5个标的
                    data = await self.smart_refresh.adaptive_refresh(
                        symbol=symbol,
                        interval_type="realtime",
                        fetch_func=self.data_fetcher.fetch_stock_data,
                        interval="1m"
                    )
                    if data:
                        all_data[symbol] = data
                
                # 分析数据并触发告警
                await self._analyze_and_alert(all_data, "realtime")
                
                # 更新市场数据
                self.market_data.update(all_data)
                
                # 记录更新时间
                self.last_update_time["realtime"] = datetime.now()
                
                logger.debug(f"实时监控完成，监控 {len(all_data)} 个标的")
                
            except Exception as e:
                logger.error(f"实时监控出错: {e}")
            
            # 使用智能刷新间隔
            refresh_stats = self.smart_refresh.get_refresh_stats()
            interval = refresh_stats.get("recent_avg_interval", MONITOR_INTERVALS["realtime"])
            await asyncio.sleep(interval)
    
    async def _monitor_minute(self):
        """分钟级监控（60秒间隔）"""
        logger.info("启动分钟级监控（60秒间隔）...")
        
        while self.is_monitoring:
            try:
                # 获取分钟数据
                all_data = await self.data_fetcher.get_all_symbols_data("5m")
                
                # 分析数据
                await self._analyze_and_alert(all_data, "minute")
                
                # 记录更新时间
                self.last_update_time["minute"] = datetime.now()
                
                logger.info(f"分钟监控完成，监控 {len(all_data)} 个标的")
                
            except Exception as e:
                logger.error(f"分钟监控出错: {e}")
            
            # 等待60秒
            await asyncio.sleep(MONITOR_INTERVALS["minute"])
    
    async def _monitor_hourly(self):
        """小时级监控"""
        logger.info("启动小时级监控...")
        
        while self.is_monitoring:
            try:
                # 获取小时数据
                all_data = await self.data_fetcher.get_all_symbols_data("1h")
                
                # 分析数据
                await self._analyze_and_alert(all_data, "hourly")
                
                # 记录更新时间
                self.last_update_time["hourly"] = datetime.now()
                
                logger.info(f"小时监控完成，监控 {len(all_data)} 个标的")
                
            except Exception as e:
                logger.error(f"小时监控出错: {e}")
            
            # 等待1小时
            await asyncio.sleep(MONITOR_INTERVALS["hourly"])
    
    async def _monitor_daily(self):
        """日级监控"""
        logger.info("启动日级监控...")
        
        while self.is_monitoring:
            try:
                # 获取日数据
                all_data = await self.data_fetcher.get_all_symbols_data("1d")
                
                # 分析数据
                await self._analyze_and_alert(all_data, "daily")
                
                # 记录更新时间
                self.last_update_time["daily"] = datetime.now()
                
                logger.info(f"日监控完成，监控 {len(all_data)} 个标的")
                
            except Exception as e:
                logger.error(f"日监控出错: {e}")
            
            # 等待1天
            await asyncio.sleep(MONITOR_INTERVALS["daily"])
    
    async def _analyze_and_alert(self, all_data: Dict[str, pd.DataFrame], interval: str):
        """分析数据并触发告警"""
        alerts = []
        
        for symbol, data in all_data.items():
            if data.empty:
                continue
            
            # 获取最新数据点
            latest = data.iloc[-1]
            
            # 检查价格异常变动
            price_alerts = await self._check_price_abnormalities(symbol, data, interval)
            alerts.extend(price_alerts)
            
            # 检查成交量异常
            volume_alerts = await self._check_volume_abnormalities(symbol, data, interval)
            alerts.extend(volume_alerts)
            
            # 检查技术指标信号
            indicator_alerts = await self._check_technical_indicators(symbol, data, interval)
            alerts.extend(indicator_alerts)
        
        # 发送告警
        if alerts:
            await self.alert_manager.send_alerts(alerts, interval)
    
    async def _check_price_abnormalities(self, symbol: str, data: pd.DataFrame, interval: str) -> List[Dict]:
        """检查价格异常"""
        alerts = []
        
        if len(data) < 2:
            return alerts
        
        # 计算最新价格变动
        latest_close = data['close'].iloc[-1]
        prev_close = data['close'].iloc[-2]
        price_change = (latest_close - prev_close) / prev_close
        
        # 检查是否超过阈值
        threshold = ALERT_CONFIG["price_change_threshold"]
        if abs(price_change) > threshold:
            alert = {
                "symbol": symbol,
                "type": "price_abnormal",
                "severity": "high" if abs(price_change) > threshold * 2 else "medium",
                "message": f"{symbol} 价格异常变动: {price_change:.2%}",
                "data": {
                    "current_price": latest_close,
                    "price_change": price_change,
                    "threshold": threshold,
                    "interval": interval
                },
                "timestamp": datetime.now().isoformat()
            }
            alerts.append(alert)
            logger.warning(f"⚠️ {symbol} 价格异常变动: {price_change:.2%}")
        
        return alerts
    
    async def _check_volume_abnormalities(self, symbol: str, data: pd.DataFrame, interval: str) -> List[Dict]:
        """检查成交量异常"""
        alerts = []
        
        if len(data) < 21:  # 需要足够数据计算移动平均
            return alerts
        
        # 计算成交量异常
        latest_volume = data['volume'].iloc[-1]
        volume_ma = data['volume'].rolling(window=20).mean().iloc[-1]
        
        if volume_ma > 0:
            volume_ratio = latest_volume / volume_ma
            
            # 检查是否超过阈值
            threshold = ALERT_CONFIG["volume_spike_threshold"]
            if volume_ratio > threshold:
                alert = {
                    "symbol": symbol,
                    "type": "volume_spike",
                    "severity": "high" if volume_ratio > threshold * 2 else "medium",
                    "message": f"{symbol} 成交量异常: {volume_ratio:.1f}倍于平均",
                    "data": {
                        "current_volume": latest_volume,
                        "volume_average": volume_ma,
                        "volume_ratio": volume_ratio,
                        "threshold": threshold,
                        "interval": interval
                    },
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)
                logger.warning(f"⚠️ {symbol} 成交量异常: {volume_ratio:.1f}倍")
        
        return alerts
    
    async def _check_technical_indicators(self, symbol: str, data: pd.DataFrame, interval: str) -> List[Dict]:
        """检查技术指标信号"""
        alerts = []
        
        # 检查RSI超买超卖
        if 'RSI' in data.columns and not pd.isna(data['RSI'].iloc[-1]):
            rsi = data['RSI'].iloc[-1]
            
            if rsi > ALERT_CONFIG["rsi_overbought"]:
                alert = {
                    "symbol": symbol,
                    "type": "rsi_overbought",
                    "severity": "medium",
                    "message": f"{symbol} RSI超买: {rsi:.1f}",
                    "data": {
                        "rsi": rsi,
                        "threshold": ALERT_CONFIG["rsi_overbought"],
                        "interval": interval
                    },
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)
                logger.warning(f"⚠️ {symbol} RSI超买: {rsi:.1f}")
            
            elif rsi < ALERT_CONFIG["rsi_oversold"]:
                alert = {
                    "symbol": symbol,
                    "type": "rsi_oversold",
                    "severity": "medium",
                    "message": f"{symbol} RSI超卖: {rsi:.1f}",
                    "data": {
                        "rsi": rsi,
                        "threshold": ALERT_CONFIG["rsi_oversold"],
                        "interval": interval
                    },
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)
                logger.warning(f"⚠️ {symbol} RSI超卖: {rsi:.1f}")
        
        # 检查MACD信号
        if 'MACD' in data.columns and 'MACD_signal' in data.columns:
            if len(data) >= 2:
                macd = data['MACD'].iloc[-1]
                macd_signal = data['MACD_signal'].iloc[-1]
                prev_macd = data['MACD'].iloc[-2]
                prev_macd_signal = data['MACD_signal'].iloc[-2]
                
                # 检查MACD金叉
                if prev_macd < prev_macd_signal and macd > macd_signal:
                    alert = {
                        "symbol": symbol,
                        "type": "macd_golden_cross",
                        "severity": "low",
                        "message": f"{symbol} MACD金叉信号",
                        "data": {
                            "macd": macd,
                            "macd_signal": macd_signal,
                            "interval": interval
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    alerts.append(alert)
                    logger.info(f"📈 {symbol} MACD金叉信号")
                
                # 检查MACD死叉
                elif prev_macd > prev_macd_signal and macd < macd_signal:
                    alert = {
                        "symbol": symbol,
                        "type": "macd_death_cross",
                        "severity": "low",
                        "message": f"{symbol} MACD死叉信号",
                        "data": {
                            "macd": macd,
                            "macd_signal": macd_signal,
                            "interval": interval
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    alerts.append(alert)
                    logger.info(f"📉 {symbol} MACD死叉信号")
        
        return alerts
    
    async def _monitor_system_resources(self):
        """监控系统资源"""
        logger.info("启动系统资源监控...")
        
        while self.is_monitoring:
            try:
                await self.smart_refresh.monitor_system_resources()
                
                # 每30秒监控一次系统资源
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"系统资源监控出错: {e}")
                await asyncio.sleep(60)
    
    def get_smart_refresh_stats(self) -> Dict:
        """获取智能刷新统计信息"""
        return self.smart_refresh.get_refresh_stats()
    
    async def check_alerts(self, stock_data: Dict) -> List[Dict]:
        """检查股票数据告警"""
        alerts = []
        try:
            for symbol, data in stock_data.items():
                if isinstance(data, dict) and 'price' in data:
                    # 检查价格异常
                    current_price = data['price']
                    # 这里可以添加更复杂的告警逻辑
                    # 暂时返回空列表，避免影响现有功能
                    pass
        except Exception as e:
            logger.error(f"检查告警出错: {e}")
        
        return alerts
    
    def get_status(self) -> Dict:
        """获取监控状态"""
        return {
            "is_monitoring": self.is_monitoring,
            "monitored_symbols_count": len(self.market_data),
            "last_update_time": self.last_update_time,
            "active_tasks": len(self.monitor_tasks)
        }