#!/usr/bin/env python3
"""
策略基类 - 所有交易策略的基类
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            name: 策略名称
            config: 策略配置
        """
        self.name = name
        self.config = config or {}
        self.is_active = False
        self.position = 0.0  # 当前仓位，-1到1之间
        self.capital = 0.0   # 分配资金
        self.performance = {
            'total_return': 0.0,
            'win_rate': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
        self.trade_history = []
        self.symbols = []
        
        # 默认配置
        self.default_config = {
            'position_size': 0.1,      # 单次交易仓位比例
            'stop_loss': 0.05,         # 止损比例
            'take_profit': 0.10,       # 止盈比例
            'max_position': 0.2,       # 最大仓位
            'min_capital': 10000,      # 最小资金要求
            'timeframes': ['15m', '1h', '4h'],  # 分析时间框架
            'symbols': []              # 交易标的
        }
        
        # 更新配置
        self.default_config.update(self.config)
        self.config = self.default_config
        
    @abstractmethod
    async def initialize(self):
        """初始化策略"""
        pass
    
    @abstractmethod
    async def generate_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            market_data: 市场数据
            
        Returns:
            交易信号字典
        """
        pass
    
    @abstractmethod
    async def calculate_position(self, signal: Dict[str, Any]) -> float:
        """
        计算仓位大小
        
        Args:
            signal: 交易信号
            
        Returns:
            仓位比例 (-1到1之间)
        """
        pass
    
    async def start(self):
        """启动策略"""
        logger.info(f"启动策略: {self.name}")
        await self.initialize()
        self.is_active = True
        
    async def stop(self):
        """停止策略"""
        logger.info(f"停止策略: {self.name}")
        self.is_active = False
        
    async def update_market_data(self, market_data: Dict[str, Any]):
        """
        更新市场数据
        
        Args:
            market_data: 市场数据
        """
        # 这里可以添加数据预处理逻辑
        self.market_data = market_data
        
    async def execute_trade(self, symbol: str, position: float, price: float) -> Dict[str, Any]:
        """
        执行交易
        
        Args:
            symbol: 交易标的
            position: 仓位比例
            price: 交易价格
            
        Returns:
            交易结果
        """
        if not self.is_active:
            return {'success': False, 'error': '策略未激活'}
        
        # 检查仓位限制
        if abs(position) > self.config['max_position']:
            position = np.sign(position) * self.config['max_position']
            logger.warning(f"仓位超过限制，调整为: {position}")
        
        # 检查资金要求
        required_capital = abs(position) * self.capital
        if required_capital < self.config['min_capital']:
            return {'success': False, 'error': '资金不足'}
        
        # 记录交易
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'position': position,
            'price': price,
            'capital': required_capital,
            'strategy': self.name
        }
        
        self.trade_history.append(trade)
        self.position = position
        self.performance['total_trades'] += 1
        
        logger.info(f"执行交易: {symbol} 仓位: {position} 价格: {price}")
        
        return {
            'success': True,
            'trade': trade,
            'position': position,
            'remaining_capital': self.capital - required_capital
        }
    
    def update_performance(self, pnl: float):
        """
        更新绩效数据
        
        Args:
            pnl: 盈亏金额
        """
        self.performance['total_return'] += pnl
        
        if pnl > 0:
            self.performance['winning_trades'] += 1
        elif pnl < 0:
            self.performance['losing_trades'] += 1
            
        total_trades = self.performance['total_trades']
        if total_trades > 0:
            self.performance['win_rate'] = self.performance['winning_trades'] / total_trades
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取绩效报告
        
        Returns:
            绩效报告字典
        """
        return {
            'strategy_name': self.name,
            'is_active': self.is_active,
            'current_position': self.position,
            'allocated_capital': self.capital,
            'performance': self.performance.copy(),
            'recent_trades': self.trade_history[-10:] if self.trade_history else [],
            'config': self.config
        }
    
    def set_capital(self, capital: float):
        """
        设置分配资金
        
        Args:
            capital: 资金金额
        """
        self.capital = capital
        logger.info(f"策略 {self.name} 分配资金: {capital}")
    
    def add_symbol(self, symbol: str):
        """
        添加交易标的
        
        Args:
            symbol: 交易标的
        """
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            logger.info(f"策略 {self.name} 添加标的: {symbol}")
    
    def remove_symbol(self, symbol: str):
        """
        移除交易标的
        
        Args:
            symbol: 交易标的
        """
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            logger.info(f"策略 {self.name} 移除标的: {symbol}")
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        更新策略配置
        
        Args:
            new_config: 新配置
        """
        self.config.update(new_config)
        logger.info(f"策略 {self.name} 更新配置: {new_config}")


class StrategyError(Exception):
    """策略异常"""
    pass


class InsufficientCapitalError(StrategyError):
    """资金不足异常"""
    pass


class PositionLimitError(StrategyError):
    """仓位限制异常"""
    pass