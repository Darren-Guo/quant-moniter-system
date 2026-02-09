#!/usr/bin/env python3
"""
策略管理器 - 管理多个策略的运行和协调
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy
from .trend_following import TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy

logger = logging.getLogger(__name__)


class StrategyManager:
    """策略管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化策略管理器
        
        Args:
            config: 管理器配置
        """
        self.config = config or {}
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_weights: Dict[str, float] = {}
        self.total_capital = 0.0
        self.is_running = False
        self.market_data = {}
        self.signal_history = []
        
        # 默认配置
        self.default_config = {
            'max_total_position': 0.8,           # 总仓位限制
            'max_single_strategy_position': 0.3, # 单策略仓位限制
            'signal_check_interval': 10,         # 信号检查间隔（秒）
            'position_update_interval': 60,      # 仓位更新间隔（秒）
            'performance_report_interval': 300,  # 绩效报告间隔（秒）
            'risk_free_rate': 0.02,              # 无风险利率
            'correlation_threshold': 0.7,        # 相关性阈值
            'diversification_min': 3,            # 最小分散标的数
        }
        
        # 更新配置
        self.default_config.update(self.config)
        self.config = self.default_config
        
    def create_strategy(self, strategy_type: str, name: str, 
                       config: Dict[str, Any] = None) -> BaseStrategy:
        """
        创建策略
        
        Args:
            strategy_type: 策略类型
            name: 策略名称
            config: 策略配置
            
        Returns:
            策略实例
        """
        strategy_map = {
            'trend_following': TrendFollowingStrategy,
            'mean_reversion': MeanReversionStrategy,
            # 后续添加其他策略
        }
        
        if strategy_type not in strategy_map:
            raise ValueError(f"未知的策略类型: {strategy_type}")
        
        strategy_class = strategy_map[strategy_type]
        strategy = strategy_class(name, config)
        
        return strategy
    
    def add_strategy(self, strategy: BaseStrategy, weight: float = 1.0):
        """
        添加策略
        
        Args:
            strategy: 策略实例
            weight: 策略权重
        """
        if strategy.name in self.strategies:
            logger.warning(f"策略 {strategy.name} 已存在，将被替换")
        
        self.strategies[strategy.name] = strategy
        self.strategy_weights[strategy.name] = weight
        
        logger.info(f"添加策略: {strategy.name}，权重: {weight}")
    
    def remove_strategy(self, strategy_name: str):
        """
        移除策略
        
        Args:
            strategy_name: 策略名称
        """
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            del self.strategy_weights[strategy_name]
            logger.info(f"移除策略: {strategy_name}")
        else:
            logger.warning(f"策略 {strategy_name} 不存在")
    
    def set_strategy_weight(self, strategy_name: str, weight: float):
        """
        设置策略权重
        
        Args:
            strategy_name: 策略名称
            weight: 策略权重
        """
        if strategy_name in self.strategies:
            self.strategy_weights[strategy_name] = weight
            logger.info(f"设置策略 {strategy_name} 权重为: {weight}")
        else:
            logger.warning(f"策略 {strategy_name} 不存在")
    
    def allocate_capital(self, total_capital: float):
        """
        分配资金
        
        Args:
            total_capital: 总资金
        """
        self.total_capital = total_capital
        
        # 计算总权重
        total_weight = sum(self.strategy_weights.values())
        if total_weight == 0:
            logger.warning("总权重为0，无法分配资金")
            return
        
        # 按权重分配资金
        for strategy_name, weight in self.strategy_weights.items():
            if strategy_name in self.strategies:
                strategy_capital = total_capital * (weight / total_weight)
                self.strategies[strategy_name].set_capital(strategy_capital)
                logger.info(f"策略 {strategy_name} 分配资金: {strategy_capital:.2f}")
    
    def add_symbol_to_strategy(self, strategy_name: str, symbol: str):
        """
        添加交易标到策略
        
        Args:
            strategy_name: 策略名称
            symbol: 交易标的
        """
        if strategy_name in self.strategies:
            self.strategies[strategy_name].add_symbol(symbol)
        else:
            logger.warning(f"策略 {strategy_name} 不存在")
    
    def add_symbol_to_all(self, symbol: str):
        """
        添加交易标到所有策略
        
        Args:
            symbol: 交易标的
        """
        for strategy_name in self.strategies:
            self.strategies[strategy_name].add_symbol(symbol)
    
    async def start_all_strategies(self):
        """启动所有策略"""
        logger.info("启动所有策略...")
        
        tasks = []
        for strategy_name, strategy in self.strategies.items():
            tasks.append(strategy.start())
        
        await asyncio.gather(*tasks)
        self.is_running = True
        
        logger.info(f"共启动 {len(self.strategies)} 个策略")
    
    async def stop_all_strategies(self):
        """停止所有策略"""
        logger.info("停止所有策略...")
        
        tasks = []
        for strategy_name, strategy in self.strategies.items():
            tasks.append(strategy.stop())
        
        await asyncio.gather(*tasks)
        self.is_running = False
        
        logger.info(f"共停止 {len(self.strategies)} 个策略")
    
    async def update_market_data(self, market_data: Dict[str, Any]):
        """
        更新市场数据
        
        Args:
            market_data: 市场数据
        """
        self.market_data = market_data
        
        # 更新每个策略的市场数据
        tasks = []
        for strategy in self.strategies.values():
            tasks.append(strategy.update_market_data(market_data))
        
        await asyncio.gather(*tasks)
    
    async def collect_signals(self) -> List[Dict[str, Any]]:
        """
        收集所有策略的信号
        
        Returns:
            信号列表
        """
        if not self.is_running:
            return []
        
        signals = []
        
        # 并行收集信号
        tasks = []
        for strategy_name, strategy in self.strategies.items():
            tasks.append(self._get_strategy_signal(strategy_name, strategy))
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result:
                signals.append(result)
        
        # 记录信号历史
        for signal in signals:
            self.signal_history.append({
                'timestamp': datetime.now(),
                'signal': signal
            })
        
        # 保留最近1000个信号
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]
        
        return signals
    
    async def _get_strategy_signal(self, strategy_name: str, 
                                  strategy: BaseStrategy) -> Optional[Dict[str, Any]]:
        """
        获取单个策略的信号
        
        Args:
            strategy_name: 策略名称
            strategy: 策略实例
            
        Returns:
            策略信号
        """
        try:
            signal = await strategy.generate_signal(self.market_data)
            signal['strategy_name'] = strategy_name
            return signal
        except Exception as e:
            logger.error(f"策略 {strategy_name} 生成信号失败: {e}")
            return None
    
    def analyze_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析信号
        
        Args:
            signals: 信号列表
            
        Returns:
            信号分析结果
        """
        if not signals:
            return {'consensus': 'hold', 'confidence': 0, 'signals': []}
        
        # 按交易标的分组
        symbol_signals = {}
        for signal in signals:
            symbol = signal.get('symbol')
            if not symbol:
                continue
            
            if symbol not in symbol_signals:
                symbol_signals[symbol] = []
            
            symbol_signals[symbol].append(signal)
        
        # 分析每个标的的信号
        symbol_analysis = {}
        for symbol, sig_list in symbol_signals.items():
            buy_count = sum(1 for s in sig_list if s.get('action') == 'buy')
            sell_count = sum(1 for s in sig_list if s.get('action') == 'sell')
            hold_count = sum(1 for s in sig_list if s.get('action') == 'hold')
            exit_count = sum(1 for s in sig_list if s.get('action') == 'exit')
            
            total = len(sig_list)
            buy_ratio = buy_count / total if total > 0 else 0
            sell_ratio = sell_count / total if total > 0 else 0
            
            # 计算平均置信度
            confidences = [s.get('confidence', 0) for s in sig_list]
            avg_confidence = np.mean(confidences) if confidences else 0
            
            # 判断共识
            consensus = 'hold'
            if exit_count > 0:
                consensus = 'exit'
            elif buy_ratio >= 0.5 and avg_confidence > 0.3:
                consensus = 'buy'
            elif sell_ratio >= 0.5 and avg_confidence > 0.3:
                consensus = 'sell'
            
            symbol_analysis[symbol] = {
                'consensus': consensus,
                'buy_ratio': buy_ratio,
                'sell_ratio': sell_ratio,
                'confidence': avg_confidence,
                'total_signals': total,
                'signals': sig_list
            }
        
        # 总体分析
        all_consensus = [analysis['consensus'] for analysis in symbol_analysis.values()]
        buy_symbols = [symbol for symbol, analysis in symbol_analysis.items() 
                      if analysis['consensus'] == 'buy']
        sell_symbols = [symbol for symbol, analysis in symbol_analysis.items() 
                       if analysis['consensus'] == 'sell']
        
        overall_consensus = 'hold'
        if buy_symbols:
            overall_consensus = 'buy'
        elif sell_symbols:
            overall_consensus = 'sell'
        
        return {
            'overall_consensus': overall_consensus,
            'buy_symbols': buy_symbols,
            'sell_symbols': sell_symbols,
            'symbol_analysis': symbol_analysis,
            'total_signals': len(signals),
            'timestamp': datetime.now()
        }
    
    def calculate_position_size(self, signal_analysis: Dict[str, Any], 
                               symbol: str) -> float:
        """
        计算仓位大小
        
        Args:
            signal_analysis: 信号分析结果
            symbol: 交易标的
            
        Returns:
            仓位比例
        """
        if symbol not in signal_analysis['symbol_analysis']:
            return 0.0
        
        analysis = signal_analysis['symbol_analysis'][symbol]
        
        if analysis['consensus'] == 'hold':
            return 0.0
        
        # 基础仓位
        base_position = 0.1
        
        # 根据信号强度调整
        signal_strength = analysis['confidence']
        
        # 根据信号一致性调整
        consensus_strength = max(analysis['buy_ratio'], analysis['sell_ratio'])
        
        # 根据策略数量调整
        strategy_count = analysis['total_signals']
        strategy_factor = min(strategy_count / 5, 1.0)  # 最多5个策略
        
        # 最终仓位
        position = base_position * signal_strength * consensus_strength * strategy_factor
        
        # 方向
        if analysis['consensus'] == 'sell':
            position = -position
        
        # 检查总仓位限制
        total_position = self.get_total_position()
        max_total = self.config['max_total_position']
        
        if abs(total_position + position) > max_total:
            # 按比例缩减
            available = max_total - abs(total_position)
            position = np.sign(position) * min(abs(position), available)
        
        return position
    
    def get_total_position(self) -> float:
        """
        获取总仓位
        
        Returns:
            总仓位比例
        """
        total = 0.0
        for strategy in self.strategies.values():
            total += strategy.position
        
        return total
    
    def get_strategy_positions(self) -> Dict[str, float]:
        """
        获取各策略仓位
        
        Returns:
            策略仓位字典
        """
        positions = {}
        for strategy_name, strategy in self.strategies.items():
            positions[strategy_name] = strategy.position
        
        return positions
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取绩效报告
        
        Returns:
            绩效报告
        """
        strategy_reports = {}
        total_return = 0.0
        total_trades = 0
        winning_trades = 0
        
        for strategy_name, strategy in self.strategies.items():
            report = strategy.get_performance_report()
            strategy_reports[strategy_name] = report
            
            total_return += report['performance']['total_return']
            total_trades += report['performance']['total_trades']
            winning_trades += report['performance']['winning_trades']
        
        # 计算总体绩效
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'timestamp': datetime.now(),
            'total_capital': self.total_capital,
            'total_position': self.get_total_position(),
            'total_return': total_return,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'strategy_reports': strategy_reports,
            'strategy_weights': self.strategy_weights.copy(),
            'signal_history_count': len(self.signal_history)
        }
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息
        
        Returns:
            策略信息
        """
        strategy_info = {}
        for strategy_name, strategy in self.strategies.items():
            if hasattr(strategy, 'get_strategy_info'):
                strategy_info[strategy_name] = strategy.get_strategy_info()
            else:
                strategy_info[strategy_name] = {
                    'name': strategy.name,
                    'type': 'unknown',
                    'config': strategy.config,
                    'performance': strategy.performance
                }
        
        return {
            'total_strategies': len(self.strategies),
            'is_running': self.is_running,
            'total_capital': self.total_capital,
            'strategies': strategy_info,
            'strategy_weights': self.strategy_weights.copy()
        }
    
    async def run_signal_loop(self):
        """
        运行信号循环
        """
        logger.info("启动信号循环...")
        
        while self.is_running:
            try:
                # 收集信号
                signals = await self.collect_signals()
                
                # 分析信号
                analysis = self.analyze_signals(signals)
                
                # 这里可以添加自动交易逻辑
                # await self.execute_trades_based_on_signals(analysis)
                
                # 记录日志
                if analysis['overall_consensus'] != 'hold':
                    logger.info(f"信号分析: {analysis['overall_consensus']}, "
                              f"买入标的: {analysis['buy_symbols']}, "
                              f"卖出标的: {analysis['sell_symbols']}")
                
                # 等待下一次检查
                await asyncio.sleep(self.config['signal_check_interval'])
                
            except Exception as e:
                logger.error(f"信号循环出错: {e}")
                await asyncio.sleep(5)  # 出错后等待5秒
    
    async def run_performance_monitoring(self):
        """
        运行绩效监控
        """
        logger.info("启动绩效监控...")
        
        while self.is_running:
            try:
                # 生成绩效报告
                report = self.get_performance_report()
                
                # 记录重要指标
                logger.info(f"绩效监控 - 总收益: {report['total_return']:.2f}, "
                          f"总仓位: {report['total_position']:.2%}, "
                          f"胜率: {report['win_rate']:.2%}")
                
                # 等待下一次报告
                await asyncio.sleep(self.config['performance_report_interval'])
                
            except Exception as e:
                logger.error(f"绩效监控出错: {e}")
                await asyncio.sleep(30)  # 出错后等待30秒