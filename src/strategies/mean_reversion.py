#!/usr/bin/env python3
"""
均值回归策略
基于布林带、RSI、ATR等指标识别价格偏离和回归机会
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""
    
    def __init__(self, name: str = "均值回归策略", config: Dict[str, Any] = None):
        """
        初始化均值回归策略
        
        Args:
            name: 策略名称
            config: 策略配置
        """
        default_config = {
            'bollinger_period': 20,      # 布林带周期
            'bollinger_std': 2.0,        # 布林带标准差倍数
            'rsi_period': 14,            # RSI周期
            'rsi_overbought': 70,        # RSI超买线
            'rsi_oversold': 30,          # RSI超卖线
            'atr_period': 14,            # ATR周期
            'atr_multiplier': 1.5,       # ATR止损倍数
            'position_size': 0.1,        # 单次交易仓位
            'max_position': 0.2,         # 最大仓位
            'timeframes': ['5m', '15m', '1h'],  # 分析时间框架
            'reversion_confirmation': 2,  # 回归确认所需时间框架数
            'profit_target_std': 1.0,     # 盈利目标标准差倍数
            'stop_loss_std': 2.0,        # 止损标准差倍数
            'min_holding_period': 5,     # 最小持有期（分钟）
            'max_holding_period': 240,   # 最大持有期（分钟）
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(name, default_config)
        
        # 持仓记录
        self.positions = {}
        # 技术指标缓存
        self.indicators_cache = {}
        
    async def initialize(self):
        """初始化策略"""
        logger.info(f"初始化均值回归策略: {self.name}")
        
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = None, 
                                 std: float = None) -> Dict[str, pd.Series]:
        """计算布林带"""
        if period is None:
            period = self.config['bollinger_period']
        if std is None:
            std = self.config['bollinger_std']
        
        sma = prices.rolling(window=period).mean()
        rolling_std = prices.rolling(window=period).std()
        
        upper_band = sma + (rolling_std * std)
        lower_band = sma - (rolling_std * std)
        
        # 计算带宽和位置
        bandwidth = (upper_band - lower_band) / sma
        position = (prices - lower_band) / (upper_band - lower_band)
        
        return {
            'sma': sma,
            'upper': upper_band,
            'lower': lower_band,
            'bandwidth': bandwidth,
            'position': position
        }
    
    def calculate_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        """计算RSI指标"""
        if period is None:
            period = self.config['rsi_period']
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = None) -> pd.Series:
        """计算ATR指标"""
        if period is None:
            period = self.config['atr_period']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_zscore(self, prices: pd.Series, period: int = None) -> pd.Series:
        """计算Z-Score（标准化分数）"""
        if period is None:
            period = self.config['bollinger_period']
        
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        zscore = (prices - sma) / std
        
        return zscore
    
    def analyze_mean_reversion(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析均值回归机会
        
        Args:
            symbol: 交易标的
            data: K线数据
            
        Returns:
            回归分析结果
        """
        if len(data) < self.config['bollinger_period']:
            return {'signal': 'hold', 'deviation': 0, 'confidence': 0}
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # 计算技术指标
        bb = self.calculate_bollinger_bands(close)
        rsi = self.calculate_rsi(close)
        atr = self.calculate_atr(high, low, close)
        zscore = self.calculate_zscore(close)
        
        # 获取最新值
        latest_close = close.iloc[-1]
        latest_upper = bb['upper'].iloc[-1]
        latest_lower = bb['lower'].iloc[-1]
        latest_sma = bb['sma'].iloc[-1]
        latest_position = bb['position'].iloc[-1]
        latest_rsi = rsi.iloc[-1]
        latest_zscore = zscore.iloc[-1]
        latest_atr = atr.iloc[-1]
        
        # 计算偏离度
        deviation_from_sma = (latest_close - latest_sma) / latest_sma
        deviation_from_upper = (latest_close - latest_upper) / latest_upper
        deviation_from_lower = (latest_close - latest_lower) / latest_lower
        
        # 判断回归信号
        signal = 'hold'
        deviation = 0
        confidence = 0
        
        # 超卖信号（价格低于下轨，RSI超卖）
        if latest_close < latest_lower and latest_rsi < self.config['rsi_oversold']:
            signal = 'buy'
            deviation = abs(deviation_from_lower)
            # 计算置信度：偏离越大，RSI越低，置信度越高
            rsi_factor = 1.0 - (latest_rsi / self.config['rsi_oversold'])
            confidence = min(deviation * 10 + rsi_factor, 1.0)
        
        # 超买信号（价格高于上轨，RSI超买）
        elif latest_close > latest_upper and latest_rsi > self.config['rsi_overbought']:
            signal = 'sell'
            deviation = abs(deviation_from_upper)
            # 计算置信度：偏离越大，RSI越高，置信度越高
            rsi_factor = (latest_rsi - self.config['rsi_overbought']) / (100 - self.config['rsi_overbought'])
            confidence = min(deviation * 10 + rsi_factor, 1.0)
        
        # Z-Score极端值信号
        elif abs(latest_zscore) > 2.5:
            if latest_zscore < -2.5:
                signal = 'buy'
            else:
                signal = 'sell'
            deviation = abs(latest_zscore) / 3.0
            confidence = min(deviation, 1.0)
        
        # 检查带宽（波动率）
        bandwidth = bb['bandwidth'].iloc[-1]
        if bandwidth < 0.05:  # 带宽太小，波动率不足
            confidence *= 0.5
        
        return {
            'symbol': symbol,
            'signal': signal,
            'deviation': deviation,
            'confidence': confidence,
            'indicators': {
                'close': latest_close,
                'sma': latest_sma,
                'upper_band': latest_upper,
                'lower_band': latest_lower,
                'bb_position': latest_position,
                'rsi': latest_rsi,
                'zscore': latest_zscore,
                'atr': latest_atr,
                'bandwidth': bandwidth,
                'deviation_from_sma': deviation_from_sma
            }
        }
    
    def check_exit_conditions(self, symbol: str, entry_price: float, 
                             current_price: float, entry_time: datetime) -> Dict[str, Any]:
        """
        检查退出条件
        
        Args:
            symbol: 交易标的
            entry_price: 入场价格
            current_price: 当前价格
            entry_time: 入场时间
            
        Returns:
            退出条件检查结果
        """
        if symbol not in self.positions:
            return {'exit': False, 'reason': '无持仓'}
        
        position = self.positions[symbol]
        position_type = position['type']  # 'long' or 'short'
        
        # 计算盈亏
        if position_type == 'long':
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # short
            pnl_pct = (entry_price - current_price) / entry_price
        
        # 计算持有时间
        holding_minutes = (datetime.now() - entry_time).total_seconds() / 60
        
        # 检查盈利目标
        profit_target = self.config['profit_target_std'] * position.get('atr', 0) / entry_price
        if pnl_pct >= profit_target:
            return {
                'exit': True,
                'reason': f'达到盈利目标: {pnl_pct:.2%}',
                'pnl_pct': pnl_pct,
                'signal': 'take_profit'
            }
        
        # 检查止损
        stop_loss = self.config['stop_loss_std'] * position.get('atr', 0) / entry_price
        if pnl_pct <= -stop_loss:
            return {
                'exit': True,
                'reason': f'触发止损: {pnl_pct:.2%}',
                'pnl_pct': pnl_pct,
                'signal': 'stop_loss'
            }
        
        # 检查最大持有时间
        if holding_minutes > self.config['max_holding_period']:
            return {
                'exit': True,
                'reason': f'超过最大持有时间: {holding_minutes:.0f}分钟',
                'pnl_pct': pnl_pct,
                'signal': 'time_exit'
            }
        
        # 检查最小持有时间
        if holding_minutes < self.config['min_holding_period']:
            return {'exit': False, 'reason': '未达到最小持有时间'}
        
        # 检查回归到均值
        if symbol in self.indicators_cache:
            bb_position = self.indicators_cache[symbol].get('bb_position', pd.Series())
            if len(bb_position) > 0:
                current_position = bb_position.iloc[-1]
                # 如果价格回归到布林带中间区域（0.3-0.7）
                if 0.3 <= current_position <= 0.7:
                    return {
                        'exit': True,
                        'reason': f'价格回归到均值区域: {current_position:.2f}',
                        'pnl_pct': pnl_pct,
                        'signal': 'mean_reversion'
                    }
        
        return {'exit': False, 'reason': '继续持有'}
    
    async def generate_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            market_data: 市场数据
            
        Returns:
            交易信号
        """
        if not self.is_active:
            return {'signal': 'hold', 'reason': '策略未激活'}
        
        entry_signals = []
        exit_signals = []
        
        for symbol in self.symbols:
            if symbol not in market_data:
                continue
            
            symbol_data = market_data[symbol]
            
            # 检查退出信号（如果有持仓）
            if symbol in self.positions:
                position = self.positions[symbol]
                current_price = None
                
                # 获取当前价格
                for timeframe in self.config['timeframes']:
                    if timeframe in symbol_data and not symbol_data[timeframe].empty:
                        current_price = symbol_data[timeframe]['close'].iloc[-1]
                        break
                
                if current_price:
                    exit_check = self.check_exit_conditions(
                        symbol, 
                        position['entry_price'],
                        current_price,
                        position['entry_time']
                    )
                    
                    if exit_check['exit']:
                        exit_signals.append({
                            'symbol': symbol,
                            'signal': 'exit',
                            'position_type': position['type'],
                            'reason': exit_check['reason'],
                            'pnl_pct': exit_check.get('pnl_pct', 0),
                            'exit_signal': exit_check.get('signal', 'unknown')
                        })
            
            # 检查入场信号
            timeframe_signals = []
            for timeframe in self.config['timeframes']:
                if timeframe in symbol_data:
                    data = symbol_data[timeframe]
                    analysis = self.analyze_mean_reversion(symbol, data)
                    
                    # 缓存指标
                    if symbol not in self.indicators_cache:
                        self.indicators_cache[symbol] = {}
                    
                    # 计算并缓存指标
                    close = data['close']
                    high = data['high']
                    low = data['low']
                    
                    bb = self.calculate_bollinger_bands(close)
                    self.indicators_cache[symbol]['bb_position'] = bb['position']
                    
                    timeframe_signals.append(analysis)
            
            if not timeframe_signals:
                continue
            
            # 综合多时间框架信号
            buy_count = sum(1 for s in timeframe_signals if s['signal'] == 'buy')
            sell_count = sum(1 for s in timeframe_signals if s['signal'] == 'sell')
            avg_confidence = np.mean([s['confidence'] for s in timeframe_signals])
            avg_deviation = np.mean([s['deviation'] for s in timeframe_signals])
            
            # 信号确认
            required_confirmation = self.config['reversion_confirmation']
            signal = 'hold'
            reason = '回归信号不明确'
            
            if buy_count >= required_confirmation and avg_confidence > 0.3:
                signal = 'buy'
                reason = f'超卖回归信号，{buy_count}/{len(timeframe_signals)}时间框架确认'
            elif sell_count >= required_confirmation and avg_confidence > 0.3:
                signal = 'sell'
                reason = f'超买回归信号，{sell_count}/{len(timeframe_signals)}时间框架确认'
            
            if signal != 'hold':
                entry_signals.append({
                    'symbol': symbol,
                    'signal': signal,
                    'reason': reason,
                    'confidence': avg_confidence,
                    'deviation': avg_deviation,
                    'timeframe_analysis': timeframe_signals
                })
        
        # 处理信号
        if exit_signals:
            # 优先处理退出信号
            best_exit = max(exit_signals, key=lambda x: abs(x.get('pnl_pct', 0)))
            return {
                'signal_type': 'mean_reversion',
                'action': 'exit',
                'symbol': best_exit['symbol'],
                'position_type': best_exit['position_type'],
                'reason': best_exit['reason'],
                'pnl_pct': best_exit['pnl_pct'],
                'all_exit_signals': exit_signals,
                'timestamp': datetime.now()
            }
        elif entry_signals:
            # 选择最佳入场信号
            entry_signals.sort(key=lambda x: x['confidence'] * x['deviation'], reverse=True)
            best_signal = entry_signals[0]
            
            return {
                'signal_type': 'mean_reversion',
                'action': best_signal['signal'],
                'symbol': best_signal['symbol'],
                'confidence': best_signal['confidence'],
                'deviation': best_signal['deviation'],
                'reason': best_signal['reason'],
                'all_entry_signals': entry_signals,
                'timestamp': datetime.now()
            }
        
        return {
            'signal_type': 'mean_reversion',
            'action': 'hold',
            'reason': '无明确回归信号',
            'confidence': 0,
            'timestamp': datetime.now()
        }
    
    async def calculate_position(self, signal: Dict[str, Any]) -> float:
        """
        计算仓位大小
        
        Args:
            signal: 交易信号
            
        Returns:
            仓位比例
        """
        if signal['action'] == 'hold' or signal['action'] == 'exit':
            return 0.0
        
        # 基础仓位
        base_position = self.config['position_size']
        
        # 根据偏离度和置信度调整仓位
        deviation = signal.get('deviation', 0)
        confidence = signal.get('confidence', 0)
        
        # 偏离越大，仓位可以适当增加（但有限制）
        deviation_multiplier = min(1.0 + deviation * 2, 2.0)
        
        # 置信度调整
        confidence_multiplier = confidence
        
        # 波动率调整（ATR）
        symbol = signal['symbol']
        volatility_adjustment = 1.0
        if symbol in self.indicators_cache:
            atr_series = self.indicators_cache[symbol].get('atr', pd.Series())
            if len(atr_series) > 0:
                latest_atr = atr_series.iloc[-1]
                # 获取当前价格
                if symbol in self.market_data:
                    for timeframe in self.config['timeframes']:
                        if timeframe in self.market_data[symbol]:
                            latest_close = self.market_data[symbol][timeframe]['close'].iloc[-1]
                            atr_percent = latest_atr / latest_close
                            # ATR越大，仓位越小
                            volatility_adjustment = max(0.3, 1.0 - atr_percent * 5)
                            break
        
        # 最终仓位
        final_position = base_position * deviation_multiplier * confidence_multiplier * volatility_adjustment
        
        # 确保不超过最大仓位限制
        max_position = self.config['max_position']
        if signal['action'] == 'buy':
            final_position = min(final_position, max_position)
        elif signal['action'] == 'sell':
            final_position = max(-final_position, -max_position)
        
        return final_position
    
    async def execute_trade(self, symbol: str, position: float, price: float) -> Dict[str, Any]:
        """
        执行交易（重写以记录持仓信息）
        
        Args:
            symbol: 交易标的
            position: 仓位比例
            price: 交易价格
            
        Returns:
            交易结果
        """
        result = await super().execute_trade(symbol, position, price)
        
        if result['success']:
            trade = result['trade']
            
            # 记录持仓信息
            if position > 0:
                position_type = 'long'
            elif position < 0:
                position_type = 'short'
            else:
                # 平仓
                if symbol in self.positions:
                    del self.positions[symbol]
                return result
            
            # 获取ATR用于止损止盈计算
            atr_value = 0
            if symbol in self.indicators_cache:
                atr_series = self.indicators_cache[symbol].get('atr', pd.Series())
                if len(atr_series) > 0:
                    atr_value = atr_series.iloc[-1]
            
            self.positions[symbol] = {
                'type': position_type,
                'entry_price': price,
                'entry_time': trade['timestamp'],
                'position': position,
                'atr': atr_value,
                'capital': trade['capital']
            }
        
        return result
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息
        
        Returns:
            策略信息
        """
        current_positions = []
        for symbol, position in self.positions.items():
            current_positions.append({
                'symbol': symbol,
                'type': position['type'],
                'entry_price': position['entry_price'],
                'entry_time': position['entry_time'],
                'position': position['position'],
                'capital': position['capital']
            })
        
        return {
            'name': self.name,
            'type': 'mean_reversion',
            'description': '基于布林带、RSI、Z-Score等指标的均值回归策略',
            'config': self.config,
            'performance': self.performance,
            'active_symbols': self.symbols,
            'current_position': self.position,
            'current_positions': current_positions
        }