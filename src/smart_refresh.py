"""
智能刷新策略管理器
根据市场活跃度、数据源状态和系统负载动态调整刷新频率
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class SmartRefreshManager:
    """智能刷新管理器"""
    
    def __init__(self):
        self.market_activity = {}  # 市场活跃度记录
        self.data_source_status = {}  # 数据源状态
        self.system_load = 0.0  # 系统负载（0-1）
        self.refresh_history = []  # 刷新历史记录
        self.optimal_intervals = {}  # 最优刷新间隔
        
    async def initialize(self):
        """初始化智能刷新管理器"""
        logger.info("初始化智能刷新管理器...")
        
        # 初始化默认刷新间隔
        self.optimal_intervals = {
            "realtime": 5,      # 实时数据
            "minute": 60,       # 分钟数据
            "hourly": 3600,     # 小时数据
            "daily": 86400      # 日数据
        }
        
        logger.info("✅ 智能刷新管理器初始化完成")
    
    def update_market_activity(self, symbol: str, volume: float, volatility: float):
        """更新市场活跃度"""
        if symbol not in self.market_activity:
            self.market_activity[symbol] = {
                "volumes": [],
                "volatilities": [],
                "last_update": datetime.now()
            }
        
        # 记录最近10个数据点
        self.market_activity[symbol]["volumes"].append(volume)
        self.market_activity[symbol]["volatilities"].append(volatility)
        
        if len(self.market_activity[symbol]["volumes"]) > 10:
            self.market_activity[symbol]["volumes"].pop(0)
            self.market_activity[symbol]["volatilities"].pop(0)
        
        self.market_activity[symbol]["last_update"] = datetime.now()
    
    def update_data_source_status(self, source: str, response_time: float, success: bool):
        """更新数据源状态"""
        if source not in self.data_source_status:
            self.data_source_status[source] = {
                "response_times": [],
                "success_rate": 1.0 if success else 0.0,
                "last_check": datetime.now()
            }
        
        # 记录响应时间
        self.data_source_status[source]["response_times"].append(response_time)
        if len(self.data_source_status[source]["response_times"]) > 20:
            self.data_source_status[source]["response_times"].pop(0)
        
        # 更新成功率
        current = self.data_source_status[source]
        if success:
            current["success_rate"] = min(1.0, current["success_rate"] + 0.05)
        else:
            current["success_rate"] = max(0.0, current["success_rate"] - 0.1)
        
        current["last_check"] = datetime.now()
    
    def update_system_load(self, cpu_usage: float, memory_usage: float):
        """更新系统负载"""
        # 简单加权平均
        self.system_load = (cpu_usage * 0.6 + memory_usage * 0.4)
    
    def calculate_optimal_interval(self, symbol: str, interval_type: str) -> int:
        """计算最优刷新间隔"""
        base_interval = self.optimal_intervals.get(interval_type, 5)
        
        # 根据市场活跃度调整
        activity_factor = 1.0
        if symbol in self.market_activity:
            activity = self.market_activity[symbol]
            if activity["volumes"] and activity["volatilities"]:
                avg_volume = statistics.mean(activity["volumes"])
                avg_volatility = statistics.mean(activity["volatilities"])
                
                # 高交易量和高波动性需要更频繁刷新
                if avg_volume > 1000000 or avg_volatility > 0.02:
                    activity_factor = 0.5  # 加倍刷新频率
                elif avg_volume < 100000 and avg_volatility < 0.005:
                    activity_factor = 2.0  # 降低刷新频率
        
        # 根据数据源状态调整
        source_factor = 1.0
        for source, status in self.data_source_status.items():
            if status["response_times"]:
                avg_response = statistics.mean(status["response_times"])
                if avg_response > 5.0:  # 响应时间超过5秒
                    source_factor = max(source_factor, 1.5)
                if status["success_rate"] < 0.8:  # 成功率低于80%
                    source_factor = max(source_factor, 2.0)
        
        # 根据系统负载调整
        load_factor = 1.0
        if self.system_load > 0.8:
            load_factor = 2.0  # 高负载时降低刷新频率
        elif self.system_load < 0.3:
            load_factor = 0.8  # 低负载时可适当提高刷新频率
        
        # 计算最终间隔
        optimal = int(base_interval * activity_factor * source_factor * load_factor)
        
        # 确保间隔在合理范围内
        if interval_type == "realtime":
            optimal = max(2, min(optimal, 30))  # 实时数据：2-30秒
        elif interval_type == "minute":
            optimal = max(30, min(optimal, 300))  # 分钟数据：30-300秒
        elif interval_type == "hourly":
            optimal = max(1800, min(optimal, 7200))  # 小时数据：30-120分钟
        elif interval_type == "daily":
            optimal = max(43200, min(optimal, 172800))  # 日数据：12-48小时
        
        # 记录刷新历史
        self.refresh_history.append({
            "timestamp": datetime.now(),
            "symbol": symbol,
            "interval_type": interval_type,
            "base_interval": base_interval,
            "optimal_interval": optimal,
            "activity_factor": activity_factor,
            "source_factor": source_factor,
            "load_factor": load_factor
        })
        
        # 保持历史记录大小
        if len(self.refresh_history) > 100:
            self.refresh_history.pop(0)
        
        return optimal
    
    def get_refresh_stats(self) -> Dict[str, Any]:
        """获取刷新统计信息"""
        if not self.refresh_history:
            return {}
        
        recent = self.refresh_history[-10:]  # 最近10次刷新
        
        return {
            "total_refreshes": len(self.refresh_history),
            "recent_avg_interval": statistics.mean([r["optimal_interval"] for r in recent]),
            "market_activity_count": len(self.market_activity),
            "data_source_count": len(self.data_source_status),
            "current_system_load": self.system_load,
            "optimal_intervals": self.optimal_intervals.copy()
        }
    
    async def adaptive_refresh(self, symbol: str, interval_type: str, 
                              fetch_func, *args, **kwargs) -> Optional[Any]:
        """自适应刷新：根据智能策略获取数据"""
        try:
            # 计算最优刷新间隔
            optimal_interval = self.calculate_optimal_interval(symbol, interval_type)
            
            # 记录开始时间
            start_time = datetime.now()
            
            # 执行数据获取
            result = await fetch_func(*args, **kwargs)
            
            # 计算响应时间
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 更新数据源状态
            source_name = fetch_func.__module__ + "." + fetch_func.__name__
            self.update_data_source_status(source_name, response_time, True)
            
            # 如果获取到数据，更新市场活跃度
            if result and "volume" in result and "volatility" in result:
                self.update_market_activity(symbol, result["volume"], result["volatility"])
            
            return result
            
        except Exception as e:
            logger.error(f"自适应刷新失败: {e}")
            
            # 更新数据源状态（失败）
            source_name = fetch_func.__module__ + "." + fetch_func.__name__
            self.update_data_source_status(source_name, 10.0, False)
            
            return None
    
    async def monitor_system_resources(self):
        """监控系统资源（简化版本）"""
        # 在实际应用中，这里会调用系统API获取CPU和内存使用率
        # 这里使用模拟数据
        import psutil
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent / 100.0
            
            self.update_system_load(cpu_percent / 100.0, memory_percent)
            
            logger.debug(f"系统负载监控: CPU={cpu_percent}%, Memory={memory_percent*100}%")
            
        except ImportError:
            # 如果没有psutil，使用模拟数据
            import random
            cpu_percent = random.uniform(20, 60)
            memory_percent = random.uniform(0.3, 0.7)
            
            self.update_system_load(cpu_percent / 100.0, memory_percent)
            
            logger.debug(f"模拟系统负载: CPU={cpu_percent}%, Memory={memory_percent*100}%")