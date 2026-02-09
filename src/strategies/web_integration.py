#!/usr/bin/env python3
"""
策略Web集成模块 - 将策略系统集成到Web界面
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .strategy_manager import StrategyManager
from .trend_following import TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy

logger = logging.getLogger(__name__)


class StrategyWebIntegration:
    """策略Web集成"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化策略Web集成
        
        Args:
            config: 配置
        """
        self.config = config or {}
        self.strategy_manager = None
        self.is_initialized = False
        
        # 默认配置
        self.default_config = {
            'initial_capital': 100000.0,
            'default_symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
            'auto_start': False,
            'update_interval': 10,  # 秒
        }
        
        # 更新配置
        self.default_config.update(self.config)
        self.config = self.default_config
        
    async def initialize(self):
        """初始化"""
        if self.is_initialized:
            return
        
        logger.info("初始化策略Web集成...")
        
        # 创建策略管理器
        manager_config = {
            'max_total_position': 0.8,
            'max_single_strategy_position': 0.3,
            'signal_check_interval': self.config['update_interval'],
            'position_update_interval': 60,
            'performance_report_interval': 300,
        }
        
        self.strategy_manager = StrategyManager(manager_config)
        
        # 创建默认策略
        await self._create_default_strategies()
        
        # 分配资金
        self.strategy_manager.allocate_capital(self.config['initial_capital'])
        
        # 启动策略（如果配置了自动启动）
        if self.config['auto_start']:
            await self.strategy_manager.start_all_strategies()
        
        self.is_initialized = True
        logger.info("策略Web集成初始化完成")
    
    async def _create_default_strategies(self):
        """创建默认策略"""
        # 趋势跟踪策略
        trend_config = {
            'position_size': 0.15,
            'max_position': 0.3,
            'timeframes': ['1h', '4h', '1d'],
            'symbols': self.config['default_symbols']
        }
        
        trend_strategy = TrendFollowingStrategy("趋势跟踪策略", trend_config)
        
        # 均值回归策略
        reversion_config = {
            'position_size': 0.1,
            'max_position': 0.2,
            'timeframes': ['15m', '1h', '4h'],
            'symbols': self.config['default_symbols']
        }
        
        reversion_strategy = MeanReversionStrategy("均值回归策略", reversion_config)
        
        # 添加到管理器
        self.strategy_manager.add_strategy(trend_strategy, weight=1.0)
        self.strategy_manager.add_strategy(reversion_strategy, weight=1.0)
        
        # 添加交易标的
        for symbol in self.config['default_symbols']:
            self.strategy_manager.add_symbol_to_all(symbol)
    
    async def start_strategies(self):
        """启动所有策略"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            await self.strategy_manager.start_all_strategies()
            logger.info("所有策略已启动")
            
            return {
                "success": True,
                "message": "所有策略已启动",
                "running_strategies": len(self.strategy_manager.strategies)
            }
        except Exception as e:
            logger.error(f"启动策略失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_strategies(self):
        """停止所有策略"""
        try:
            if self.strategy_manager:
                await self.strategy_manager.stop_all_strategies()
                logger.info("所有策略已停止")
            
            return {
                "success": True,
                "message": "所有策略已停止"
            }
        except Exception as e:
            logger.error(f"停止策略失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_market_data(self, market_data: Dict[str, Any]):
        """
        更新市场数据
        
        Args:
            market_data: 市场数据
        """
        if self.strategy_manager and self.strategy_manager.is_running:
            await self.strategy_manager.update_market_data(market_data)
    
    async def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息
        
        Returns:
            策略信息
        """
        if not self.strategy_manager:
            return {'error': '策略管理器未初始化'}
        
        return self.strategy_manager.get_strategy_info()
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """
        获取绩效报告
        
        Returns:
            绩效报告
        """
        if not self.strategy_manager:
            return {'error': '策略管理器未初始化'}
        
        return self.strategy_manager.get_performance_report()
    
    async def collect_signals(self) -> List[Dict[str, Any]]:
        """
        收集信号
        
        Returns:
            信号列表
        """
        if not self.strategy_manager or not self.strategy_manager.is_running:
            return []
        
        return await self.strategy_manager.collect_signals()
    
    async def analyze_signals(self) -> Dict[str, Any]:
        """
        分析信号
        
        Returns:
            信号分析结果
        """
        signals = await self.collect_signals()
        
        if not self.strategy_manager:
            return {'consensus': 'hold', 'confidence': 0, 'signals': []}
        
        return self.strategy_manager.analyze_signals(signals)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取仪表板数据
        
        Returns:
            仪表板数据
        """
        if not self.strategy_manager:
            return {
                'status': '未初始化',
                'total_strategies': 0,
                'is_running': False,
                'total_capital': self.config['initial_capital'],
                'total_position': 0,
                'strategies': []
            }
        
        strategy_info = self.strategy_manager.get_strategy_info()
        
        # 计算总体仓位
        total_position = 0
        if self.strategy_manager.strategies:
            total_position = sum(
                strategy.position 
                for strategy in self.strategy_manager.strategies.values()
            )
        
        return {
            'status': '运行中' if self.strategy_manager.is_running else '已停止',
            'total_strategies': len(self.strategy_manager.strategies),
            'is_running': self.strategy_manager.is_running,
            'total_capital': self.strategy_manager.total_capital,
            'total_position': total_position,
            'strategies': [
                {
                    'name': name,
                    'type': strategy.__class__.__name__,
                    'position': strategy.position,
                    'capital': strategy.capital,
                    'performance': strategy.performance
                }
                for name, strategy in self.strategy_manager.strategies.items()
            ]
        }
    
    async def add_strategy(self, strategy_type: str, name: str, 
                          config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        添加策略
        
        Args:
            strategy_type: 策略类型
            name: 策略名称
            config: 策略配置
            
        Returns:
            添加结果
        """
        if not self.strategy_manager:
            return {'success': False, 'error': '策略管理器未初始化'}
        
        try:
            strategy = self.strategy_manager.create_strategy(strategy_type, name, config)
            self.strategy_manager.add_strategy(strategy, weight=1.0)
            
            # 添加默认交易标的
            for symbol in self.config['default_symbols']:
                strategy.add_symbol(symbol)
            
            # 重新分配资金
            self.strategy_manager.allocate_capital(self.strategy_manager.total_capital)
            
            return {'success': True, 'strategy_name': name}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def remove_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """
        移除策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            移除结果
        """
        if not self.strategy_manager:
            return {'success': False, 'error': '策略管理器未初始化'}
        
        if strategy_name not in self.strategy_manager.strategies:
            return {'success': False, 'error': '策略不存在'}
        
        self.strategy_manager.remove_strategy(strategy_name)
        
        # 重新分配资金
        self.strategy_manager.allocate_capital(self.strategy_manager.total_capital)
        
        return {'success': True}
    
    async def update_strategy_config(self, strategy_name: str, 
                                    new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新策略配置
        
        Args:
            strategy_name: 策略名称
            new_config: 新配置
            
        Returns:
            更新结果
        """
        if not self.strategy_manager:
            return {'success': False, 'error': '策略管理器未初始化'}
        
        if strategy_name not in self.strategy_manager.strategies:
            return {'success': False, 'error': '策略不存在'}
        
        strategy = self.strategy_manager.strategies[strategy_name]
        strategy.update_config(new_config)
        
        return {'success': True}
    
    async def set_strategy_weight(self, strategy_name: str, 
                                 weight: float) -> Dict[str, Any]:
        """
        设置策略权重
        
        Args:
            strategy_name: 策略名称
            weight: 策略权重
            
        Returns:
            设置结果
        """
        if not self.strategy_manager:
            return {'success': False, 'error': '策略管理器未初始化'}
        
        if strategy_name not in self.strategy_manager.strategies:
            return {'success': False, 'error': '策略不存在'}
        
        self.strategy_manager.set_strategy_weight(strategy_name, weight)
        
        # 重新分配资金
        self.strategy_manager.allocate_capital(self.strategy_manager.total_capital)
        
        return {'success': True}
    
    async def set_total_capital(self, capital: float) -> Dict[str, Any]:
        """
        设置总资金
        
        Args:
            capital: 总资金
            
        Returns:
            设置结果
        """
        if not self.strategy_manager:
            return {'success': False, 'error': '策略管理器未初始化'}
        
        self.strategy_manager.allocate_capital(capital)
        
        return {'success': True}
    
    def get_available_strategy_types(self) -> List[Dict[str, Any]]:
        """
        获取可用的策略类型
        
        Returns:
            策略类型列表
        """
        return [
            {
                'type': 'trend_following',
                'name': '趋势跟踪策略',
                'description': '基于移动平均线、MACD、ADX等指标的趋势跟踪策略',
                'default_config': {
                    'position_size': 0.15,
                    'max_position': 0.3,
                    'timeframes': ['1h', '4h', '1d'],
                    'symbols': self.config['default_symbols']
                }
            },
            {
                'type': 'mean_reversion',
                'name': '均值回归策略',
                'description': '基于布林带、RSI、Z-Score等指标的均值回归策略',
                'default_config': {
                    'position_size': 0.1,
                    'max_position': 0.2,
                    'timeframes': ['15m', '1h', '4h'],
                    'symbols': self.config['default_symbols']
                }
            }
        ]


# 全局实例
_strategy_web_integration = None


def get_strategy_web_integration() -> StrategyWebIntegration:
    """
    获取策略Web集成实例（单例模式）
    
    Returns:
        策略Web集成实例
    """
    global _strategy_web_integration
    
    if _strategy_web_integration is None:
        _strategy_web_integration = StrategyWebIntegration()
    
    return _strategy_web_integration


async def initialize_strategy_web_integration():
    """初始化策略Web集成"""
    integration = get_strategy_web_integration()
    await integration.initialize()