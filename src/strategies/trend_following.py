#!/usr/bin/env python3
"""
趋势跟踪策略
基于移动平均线、MACD、ADX等指标识别和跟随趋势
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """趋势跟踪策略"""
    
    def __init__(self, name: str = "趋势跟踪策略", config: Dict[str, Any] = None):
        """
        初始化趋势跟踪策略
        
        Args:
            name: 策略名称
            config: 策略配置
        """
        default_config = {
            'fast_period': 10,      # 快速均线周期
            'slow_period': 30,      # 慢速均线周期
            'macd_fast': 12,        # MACD快速周期
            'macd_slow': 26,        # MACD慢速周期
            'macd_signal': 9,       # MACD信号周期
            'adx_period': 14,       # ADX周期
            'adx_threshold': 25,    # ADX趋势强度阈值
            'rsi_period': 14,       # RSI周期
            'rsi_overbought': 70,   # RSI超买线
            'rsi_oversold': 30,     # RSI超卖线
            'atr_period': 14,       # ATR周期
            'atr_multiplier': 2.0,  # ATR止损倍数
            'position_size': 0.15,  # 单次交易仓位
            'max_position': 0.3,    # 最大仓位
            'timeframes': ['1h', '4h', '1d'],  # 分析时间框架
            'trend_confirmation': 2,  # 趋势确认所需时间框架数
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(name, default_config)
        
        # 技术指标缓存
        self.indicators_cache = {}
        
    async def initialize(self):
        """初始化策略"""
        logger.info(f"初始化趋势跟踪策略: {self.name}")
        # 这里可以加载历史数据、训练模型等
        
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """计算简单移动平均线"""
        return prices.rolling(window=period).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """计算指数移动平均线"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """计算MACD指标"""
        fast_ema = self.calculate_ema(prices, self.config['macd_fast'])
        slow_ema = self.calculate_ema(prices, self.config['macd_slow'])
        macd_line = fast_ema - slow_ema
        signal_line = self.calculate_ema(macd_line, self.config['macd_signal'])
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
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
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = None) -> Dict[str, pd.Series]:
        """计算ADX指标"""
        if period is None:
            period = self.config['adx_period']
        
        # 计算+DM和-DM
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # 计算TR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算平滑值
        plus_di = 100 * pd.Series(plus_dm, index=high.index).rolling(period).mean() / tr.rolling(period).mean()
        minus_di = 100 * pd.Series(minus_dm, index=high.index).rolling(period).mean() / tr.rolling(period).mean()
        
        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }
    
    def analyze_trend(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析趋势
        
        Args:
            symbol: 交易标的
            data: K线数据
            
        Returns:
            趋势分析结果
        """
        if len(data) < max(self.config['slow_period'], self.config['adx_period']):
            return {'trend': 'neutral', 'strength': 0, 'confidence': 0}
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # 计算技术指标
        fast_sma = self.calculate_sma(close, self.config['fast_period'])
        slow_sma = self.calculate_sma(close, self.config['slow_period'])
        macd_data = self.calculate_macd(close)
        rsi = self.calculate_rsi(close)
        atr = self.calculate_atr(high, low, close)
        adx_data = self.calculate_adx(high, low, close)
        
        # 获取最新值
        latest_fast = fast_sma.iloc[-1]
        latest_slow = slow_sma.iloc[-1]
        latest_macd = macd_data['macd'].iloc[-1]
        latest_signal = macd_data['signal'].iloc[-1]
        latest_rsi = rsi.iloc[-1]
        latest_adx = adx_data['adx'].iloc[-1]
        latest_plus_di = adx_data['plus_di'].iloc[-1]
        latest_minus_di = adx_data['minus_di'].iloc[-1]
        
        # 判断趋势方向
        trend_score = 0
        
        # 1. 均线系统
        if latest_fast > latest_slow:
            trend_score += 1
        else:
            trend_score -= 1
        
        # 2. MACD系统
        if latest_macd > latest_signal:
            trend_score += 1
        else:
            trend_score -= 1
        
        # 3. ADX系统
        if latest_adx > self.config['adx_threshold']:
            if latest_plus_di > latest_minus_di:
                trend_score += 1
            else:
                trend_score -= 1
        
        # 4. RSI过滤
        rsi_signal = 0
        if latest_rsi > self.config['rsi_overbought']:
            rsi_signal = -1
        elif latest_rsi < self.config['rsi_oversold']:
            rsi_signal = 1
        
        # 综合判断
        if trend_score >= 2:
            trend = 'bullish'
            strength = min(trend_score / 3, 1.0)
        elif trend_score <= -2:
            trend = 'bearish'
            strength = min(abs(trend_score) / 3, 1.0)
        else:
            trend = 'neutral'
            strength = 0
        
        # 考虑RSI过滤
        if trend == 'bullish' and rsi_signal == -1:
            trend = 'neutral'
            strength *= 0.5
        elif trend == 'bearish' and rsi_signal == 1:
            trend = 'neutral'
            strength *= 0.5
        
        # 计算置信度
        confidence = strength * (latest_adx / 100 if latest_adx > 0 else 0)
        
        return {
            'symbol': symbol,
            'trend': trend,
            'strength': strength,
            'confidence': confidence,
            'indicators': {
                'fast_sma': latest_fast,
                'slow_sma': latest_slow,
                'macd': latest_macd,
                'signal': latest_signal,
                'rsi': latest_rsi,
                'adx': latest_adx,
                'plus_di': latest_plus_di,
                'minus_di': latest_minus_di,
                'atr': atr.iloc[-1]
            }
        }
    
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
        
        signals = []
        
        for symbol in self.symbols:
            if symbol not in market_data:
                continue
            
            symbol_data = market_data[symbol]
            
            # 多时间框架分析
            timeframe_signals = []
            for timeframe in self.config['timeframes']:
                if timeframe in symbol_data:
                    data = symbol_data[timeframe]
                    analysis = self.analyze_trend(symbol, data)
                    timeframe_signals.append(analysis)
            
            if not timeframe_signals:
                continue
            
            # 综合多时间框架信号
            bullish_count = sum(1 for s in timeframe_signals if s['trend'] == 'bullish')
            bearish_count = sum(1 for s in timeframe_signals if s['trend'] == 'bearish')
            avg_confidence = np.mean([s['confidence'] for s in timeframe_signals])
            
            # 趋势确认
            required_confirmation = self.config['trend_confirmation']
            signal = 'hold'
            reason = '趋势不明确'
            
            if bullish_count >= required_confirmation and avg_confidence > 0.3:
                signal = 'buy'
                reason = f'多头趋势确认，{bullish_count}/{len(timeframe_signals)}时间框架看多'
            elif bearish_count >= required_confirmation and avg_confidence > 0.3:
                signal = 'sell'
                reason = f'空头趋势确认，{bearish_count}/{len(timeframe_signals)}时间框架看空'
            
            signals.append({
                'symbol': symbol,
                'signal': signal,
                'reason': reason,
                'confidence': avg_confidence,
                'timeframe_analysis': timeframe_signals
            })
        
        # 选择最佳信号
        if signals:
            # 按置信度排序
            signals.sort(key=lambda x: x['confidence'], reverse=True)
            best_signal = signals[0]
            
            return {
                'signal_type': 'trend_following',
                'action': best_signal['signal'],
                'symbol': best_signal['symbol'],
                'confidence': best_signal['confidence'],
                'reason': best_signal['reason'],
                'all_signals': signals,
                'timestamp': datetime.now()
            }
        
        return {
            'signal_type': 'trend_following',
            'action': 'hold',
            'reason': '无明确趋势信号',
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
        if signal['action'] == 'hold':
            return 0.0
        
        # 基础仓位
        base_position = self.config['position_size']
        
        # 根据置信度调整仓位
        confidence = signal.get('confidence', 0)
        position_multiplier = min(confidence * 2, 1.0)  # 置信度0.5对应满仓
        
        # 根据ATR调整仓位（波动率越大，仓位越小）
        symbol = signal['symbol']
        if symbol in self.market_data:
            # 获取最新ATR
            latest_data = self.market_data[symbol].get('1h', pd.DataFrame())
            if not latest_data.empty and 'atr' in self.indicators_cache.get(symbol, {}):
                atr = self.indicators_cache[symbol]['atr']
                if len(atr) > 0:
                    latest_atr = atr.iloc[-1]
                    latest_close = latest_data['close'].iloc[-1]
                    atr_percent = latest_atr / latest_close
                    
                    # ATR越大，仓位越小
                    volatility_adjustment = max(0.5, 1.0 - atr_percent * 10)
                    position_multiplier *= volatility_adjustment
        
        # 最终仓位
        final_position = base_position * position_multiplier
        
        # 考虑当前仓位
        if signal['action'] == 'buy' and self.position > 0:
            # 已经有多头仓位，减少加仓
            final_position *= max(0, 1.0 - self.position)
        elif signal['action'] == 'sell' and self.position < 0:
            # 已经有空头仓位，减少加仓
            final_position *= max(0, 1.0 + self.position)
        
        # 确保不超过最大仓位限制
        max_position = self.config['max_position']
        if signal['action'] == 'buy':
            final_position = min(final_position, max_position - self.position)
        elif signal['action'] == 'sell':
            final_position = max(final_position, -max_position - self.position)
        
        return final_position
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息
        
        Returns:
            策略信息
        """
        return {
            'name': self.name,
            'type': 'trend_following',
            'description': '基于移动平均线、MACD、ADX等指标的趋势跟踪策略',
            'config': self.config,
            'performance': self.performance,
            'active_symbols': self.symbols,
            'current_position': self.position
        }