#!/usr/bin/env python3
"""
回测引擎 - 策略回测和验证
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from ..strategies.base_strategy import BaseStrategy
from ..strategies.strategy_manager import StrategyManager

logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
        """
        self.config = config or {}
        self.strategy_manager = None
        self.historical_data = {}
        self.results = {}
        
        # 默认配置
        self.default_config = {
            'initial_capital': 100000.0,      # 初始资金
            'commission_rate': 0.0005,        # 手续费率
            'slippage_rate': 0.0001,          # 滑点率
            'start_date': '2025-01-01',       # 开始日期
            'end_date': '2025-12-31',         # 结束日期
            'timeframe': '1h',                # 时间框架
            'symbols': ['AAPL', 'MSFT', 'GOOGL'],  # 交易标的
            'warmup_period': 20,              # 预热期（K线数）
            'output_dir': 'backtest_results', # 输出目录
            'save_plots': True,               # 是否保存图表
            'save_report': True,              # 是否保存报告
        }
        
        # 更新配置
        self.default_config.update(self.config)
        self.config = self.default_config
        
        # 创建输出目录
        self.output_dir = Path(self.config['output_dir'])
        self.output_dir.mkdir(exist_ok=True)
        
    def load_historical_data(self, data_source: str = 'yfinance'):
        """
        加载历史数据
        
        Args:
            data_source: 数据源
        """
        logger.info(f"加载历史数据，数据源: {data_source}")
        
        # 这里可以扩展支持多种数据源
        if data_source == 'yfinance':
            self._load_yfinance_data()
        elif data_source == 'csv':
            self._load_csv_data()
        else:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        logger.info(f"历史数据加载完成，共 {len(self.historical_data)} 个标的")
    
    def _load_yfinance_data(self):
        """加载yfinance数据"""
        try:
            import yfinance as yf
            
            start_date = self.config['start_date']
            end_date = self.config['end_date']
            timeframe = self.config['timeframe']
            symbols = self.config['symbols']
            
            for symbol in symbols:
                try:
                    logger.info(f"下载 {symbol} 数据...")
                    
                    # 根据时间框架设置interval
                    interval_map = {
                        '1m': '1m', '5m': '5m', '15m': '15m',
                        '30m': '30m', '1h': '60m', '1d': '1d'
                    }
                    
                    interval = interval_map.get(timeframe, '1d')
                    
                    # 下载数据
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(
                        start=start_date,
                        end=end_date,
                        interval=interval
                    )
                    
                    if data.empty:
                        logger.warning(f"{symbol} 数据为空")
                        continue
                    
                    # 重命名列
                    data.columns = [col.lower() for col in data.columns]
                    
                    # 确保必要的列存在
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    for col in required_cols:
                        if col not in data.columns:
                            logger.warning(f"{symbol} 缺少列: {col}")
                            continue
                    
                    self.historical_data[symbol] = data
                    logger.info(f"{symbol} 数据加载完成，共 {len(data)} 条记录")
                    
                except Exception as e:
                    logger.error(f"加载 {symbol} 数据失败: {e}")
        
        except ImportError:
            logger.error("请安装yfinance: pip install yfinance")
            # 创建模拟数据
            self._create_mock_data()
    
    def _load_csv_data(self):
        """加载CSV数据"""
        # 这里可以实现从CSV文件加载数据
        logger.warning("CSV数据源暂未实现，使用模拟数据")
        self._create_mock_data()
    
    def _create_mock_data(self):
        """创建模拟数据"""
        logger.info("创建模拟数据...")
        
        start_date = pd.Timestamp(self.config['start_date'])
        end_date = pd.Timestamp(self.config['end_date'])
        timeframe = self.config['timeframe']
        symbols = self.config['symbols']
        
        # 根据时间框架生成时间序列
        if timeframe == '1d':
            freq = 'D'
        elif timeframe == '1h':
            freq = 'H'
        elif timeframe == '15m':
            freq = '15T'
        elif timeframe == '5m':
            freq = '5T'
        elif timeframe == '1m':
            freq = '1T'
        else:
            freq = 'D'
        
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        
        for symbol in symbols:
            # 生成随机价格序列（几何布朗运动）
            n_periods = len(dates)
            
            # 基础价格
            base_price = 100 + np.random.randn() * 20
            
            # 收益率
            returns = np.random.randn(n_periods) * 0.01
            
            # 添加趋势
            trend = np.linspace(0, 0.0005, n_periods)
            returns += trend
            
            # 计算价格
            price_series = base_price * np.exp(np.cumsum(returns))
            
            # 生成OHLC数据
            data = pd.DataFrame(index=dates)
            data['close'] = price_series
            
            # 生成OHLC（基于收盘价）
            data['open'] = data['close'].shift(1) * (1 + np.random.randn(n_periods) * 0.002)
            data['high'] = data[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.randn(n_periods)) * 0.005)
            data['low'] = data[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.randn(n_periods)) * 0.005)
            data['volume'] = np.random.lognormal(10, 1, n_periods)
            
            # 处理第一行
            data.iloc[0] = data.iloc[1]
            
            self.historical_data[symbol] = data
            logger.info(f"创建 {symbol} 模拟数据，共 {len(data)} 条记录")
    
    def prepare_strategy_manager(self):
        """准备策略管理器"""
        logger.info("准备策略管理器...")
        
        # 创建策略管理器
        manager_config = {
            'max_total_position': 0.8,
            'max_single_strategy_position': 0.3,
            'signal_check_interval': 1,  # 回测中快速检查
        }
        
        self.strategy_manager = StrategyManager(manager_config)
        
        # 创建策略
        strategies = [
            {
                'type': 'trend_following',
                'name': '趋势跟踪策略',
                'config': {
                    'position_size': 0.15,
                    'timeframes': [self.config['timeframe']],
                    'symbols': self.config['symbols']
                },
                'weight': 1.0
            },
            {
                'type': 'mean_reversion',
                'name': '均值回归策略',
                'config': {
                    'position_size': 0.1,
                    'timeframes': [self.config['timeframe']],
                    'symbols': self.config['symbols']
                },
                'weight': 1.0
            }
        ]
        
        for strategy_info in strategies:
            strategy = self.strategy_manager.create_strategy(
                strategy_info['type'],
                strategy_info['name'],
                strategy_info['config']
            )
            
            self.strategy_manager.add_strategy(strategy, strategy_info['weight'])
            
            # 添加交易标的
            for symbol in self.config['symbols']:
                strategy.add_symbol(symbol)
        
        # 分配资金
        self.strategy_manager.allocate_capital(self.config['initial_capital'])
        
        logger.info(f"策略管理器准备完成，共 {len(self.strategy_manager.strategies)} 个策略")
    
    async def run_backtest(self):
        """
        运行回测
        
        Returns:
            回测结果
        """
        logger.info("开始回测...")
        
        # 准备数据
        if not self.historical_data:
            self.load_historical_data()
        
        # 准备策略
        if not self.strategy_manager:
            self.prepare_strategy_manager()
        
        # 启动策略
        await self.strategy_manager.start_all_strategies()
        
        # 获取所有时间点
        all_dates = set()
        for symbol, data in self.historical_data.items():
            all_dates.update(data.index)
        
        sorted_dates = sorted(all_dates)
        
        # 回测记录
        backtest_records = {
            'dates': [],
            'portfolio_value': [],
            'positions': [],
            'trades': [],
            'cash': [],
            'returns': []
        }
        
        # 初始状态
        current_cash = self.config['initial_capital']
        portfolio_value = current_cash
        positions = {}
        
        # 预热期
        warmup_period = self.config['warmup_period']
        
        logger.info(f"回测时间范围: {sorted_dates[0]} 到 {sorted_dates[-1]}")
        logger.info(f"共 {len(sorted_dates)} 个时间点")
        
        # 主回测循环
        for i, current_date in enumerate(sorted_dates):
            if i < warmup_period:
                continue
            
            # 准备当前市场数据
            market_data = {}
            for symbol in self.config['symbols']:
                if symbol in self.historical_data:
                    # 获取到当前日期的所有数据
                    historical = self.historical_data[symbol].loc[:current_date]
                    
                    # 为每个时间框架准备数据
                    market_data[symbol] = {
                        self.config['timeframe']: historical
                    }
            
            # 更新策略市场数据
            await self.strategy_manager.update_market_data(market_data)
            
            # 收集信号
            signals = await self.strategy_manager.collect_signals()
            
            # 分析信号
            signal_analysis = self.strategy_manager.analyze_signals(signals)
            
            # 执行交易（模拟）
            trades = await self._simulate_trades(
                signal_analysis, positions, current_cash, current_date
            )
            
            # 更新持仓和现金
            for trade in trades:
                symbol = trade['symbol']
                position_change = trade['position_change']
                trade_value = trade['trade_value']
                commission = trade['commission']
                
                # 更新持仓
                if symbol not in positions:
                    positions[symbol] = 0.0
                
                positions[symbol] += position_change
                
                # 更新现金
                current_cash -= trade_value + commission
                
                # 记录交易
                backtest_records['trades'].append({
                    'date': current_date,
                    'symbol': symbol,
                    'position_change': position_change,
                    'price': trade['price'],
                    'value': trade_value,
                    'commission': commission,
                    'type': trade['type']
                })
            
            # 计算当前投资组合价值
            portfolio_value = current_cash
            for symbol, position in positions.items():
                if symbol in self.historical_data and position != 0:
                    current_price = self.historical_data[symbol].loc[current_date, 'close']
                    position_value = position * current_price
                    portfolio_value += position_value
            
            # 记录
            backtest_records['dates'].append(current_date)
            backtest_records['portfolio_value'].append(portfolio_value)
            backtest_records['positions'].append(positions.copy())
            backtest_records['cash'].append(current_cash)
            
            # 计算收益率
            if i > warmup_period:
                prev_value = backtest_records['portfolio_value'][-2]
                daily_return = (portfolio_value - prev_value) / prev_value
                backtest_records['returns'].append(daily_return)
            else:
                backtest_records['returns'].append(0.0)
            
            # 进度显示
            if (i + 1) % 100 == 0 or i == len(sorted_dates) - 1:
                progress = (i + 1) / len(sorted_dates) * 100
                logger.info(f"回测进度: {progress:.1f}% ({i+1}/{len(sorted_dates)})")
        
        # 停止策略
        await self.strategy_manager.stop_all_strategies()
        
        # 整理结果
        self.results = self._process_results(backtest_records)
        
        logger.info("回测完成")
        
        return self.results
    
    async def _simulate_trades(self, signal_analysis: Dict[str, Any],
                              current_positions: Dict[str, float],
                              current_cash: float,
                              current_date: datetime) -> List[Dict[str, Any]]:
        """
        模拟交易执行
        
        Args:
            signal_analysis: 信号分析结果
            current_positions: 当前持仓
            current_cash: 当前现金
            current_date: 当前日期
            
        Returns:
            交易列表
        """
        trades = []
        
        for symbol in signal_analysis.get('buy_symbols', []) + signal_analysis.get('sell_symbols', []):
            if symbol not in self.historical_data:
                continue
            
            # 获取当前价格
            current_price = self.historical_data[symbol].loc[current_date, 'close']
            
            # 添加滑点
            slippage = current_price * self.config['slippage_rate']
            if symbol in signal_analysis.get('buy_symbols', []):
                execution_price = current_price + slippage
                position_change = 1  # 买入1股（实际会根据资金计算）
                trade_type = 'buy'
            else:
                execution_price = current_price - slippage
                position_change = -1  # 卖出1股
                trade_type = 'sell'
            
            # 计算交易价值（这里简化，实际应根据仓位管理计算）
            trade_value = execution_price * position_change
            
            # 计算手续费
            commission = abs(trade_value) * self.config['commission_rate']
            
            # 检查资金是否足够
            if trade_type == 'buy' and current_cash < (trade_value + commission):
                continue
            
            trades.append({
                'symbol': symbol,
                'date': current_date,
                'price': execution_price,
                'position_change': position_change,
                'trade_value': trade_value,
                'commission': commission,
                'type': trade_type
            })
        
        return trades
    
    def _process_results(self, backtest_records: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理回测结果
        
        Args:
            backtest_records: 回测记录
            
        Returns:
            处理后的结果
        """
        # 转换为DataFrame
        results_df = pd.DataFrame({
            'date': backtest_records['dates'],
            'portfolio_value': backtest_records['portfolio_value'],
            'cash': backtest_records['cash'],
            'return': backtest_records['returns']
        })
        
        results_df.set_index('date', inplace=True)
        
        # 计算绩效指标
        returns = results_df['return']
        
        # 总收益率
        total_return = (results_df['portfolio_value'].iloc[-1] / 
                       results_df['portfolio_value'].iloc[0] - 1)
        
        # 年化收益率
        days = (results_df.index[-1] - results_df.index[0]).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 年化波动率
        annual_volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        
        # 夏普比率
        risk_free_rate = 0.02  # 假设无风险利率2%
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 胜率
        winning_trades = sum(1 for trade in backtest_records['trades'] 
                           if trade['position_change'] > 0 and 
                           trade['price'] < self.historical_data[trade['symbol']].loc[trade['date']:].iloc[1:]['close'].max())
        total_trades = len(backtest_records['trades'])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 盈亏比
        winning_amount = sum(trade['trade_value'] for trade in backtest_records['trades'] 
                           if trade['trade_value'] > 0)
        losing_amount = abs(sum(trade['trade_value'] for trade in backtest_records['trades'] 
                              if trade['trade_value'] < 0))
        profit_factor = winning_amount / losing_amount if losing_amount > 0 else float('inf')
        
        # 整理结果
        results = {
            'summary': {
                'initial_capital': self.config['initial_capital'],
                'final_value': results_df['portfolio_value'].iloc[-1],
                'total_return': total_return,
                'annual_return': annual_return,
                'annual_volatility': annual_volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades
            },
            'returns': returns,
            'portfolio_values': results_df['portfolio_value'],
            'drawdown': drawdown,
            'trades': backtest_records['trades'],
            'config': self.config
        }
        
        return results
    
    def generate_report(self):
        """生成回测报告"""
        if not self.results:
            logger.warning("没有回测结果，请先运行回测")
            return
        
        logger.info("生成回测报告...")
        
        # 文本报告
        report_text = self._generate_text_report()
        
        # 图表
        if self.config['save_plots']:
            self._generate_plots()
        
        # 保存报告
        if self.config['save_report']:
            self._save_report(report_text)
        
        return report_text
    
    def _generate_text_report(self) -> str:
        """生成文本报告"""
        summary = self.results['summary']
        
        report = f"""
        ===========================================
                    量化策略回测报告
        ===========================================
        
        回测配置:
        ----------
        时间范围: {self.config['start_date']} 到 {self.config['end_date']}
        时间框架: {self.config['timeframe']}
        交易标的: {', '.join(self.config['symbols'])}
        初始资金: ¥{summary['initial_capital']:,.2f}
        手续费率: {self.config['commission_rate']:.4%}
        滑点率: {self.config['slippage_rate']:.4%}
        
        绩效摘要:
        ----------
        最终价值: ¥{summary['final_value']:,.2f}
        总收益率: {summary['total_return']:.2%}
        年化收益率: {summary['annual_return']:.2%}
        年化波动率: {summary['annual_volatility']:.2%}
        夏普比率: {summary['sharpe_ratio']:.2f}
        最大回撤: {summary['max_drawdown']:.2%}
        
        交易统计:
        ----------
        总交易次数: {summary['total_trades']}
        盈利交易: {summary['winning_trades']}
        亏损交易: {summary['losing_trades']}
        胜率: {summary['win_rate']:.2%}
        盈亏比: {summary['profit_factor']:.2f}
        
        策略评价:
        ----------
        """
        
        # 策略评价
        sharpe = summary['sharpe_ratio']
        max_dd = summary['max_drawdown']
        win_rate = summary['win_rate']
        
        if sharpe > 1.5:
            report += "✓ 夏普比率优秀 (>1.5)\n"
        elif sharpe > 1.0:
            report += "✓ 夏普比率良好 (1.0-1.5)\n"
        else:
            report += "✗ 夏普比率需要改进 (<1.0)\n"
        
        if abs(max_dd) < 0.10:
            report += "✓ 风险控制优秀 (最大回撤<10%)\n"
        elif abs(max_dd) < 0.20:
            report += "✓ 风险控制良好 (最大回撤10-20%)\n"
        else:
            report += "✗ 风险控制需要改进 (最大回撤>20%)\n"
        
        if win_rate > 0.55:
            report += "✓ 胜率优秀 (>55%)\n"
        elif win_rate > 0.45:
            report += "✓ 胜率良好 (45-55%)\n"
        else:
            report += "✗ 胜率需要改进 (<45%)\n"
        
        report += "\n生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report += "\n===========================================\n"
        
        return report
    
    def _generate_plots(self):
        """生成图表"""
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建图表
            fig, axes = plt.subplots(3, 2, figsize=(15, 12))
            fig.suptitle('量化策略回测分析', fontsize=16)
            
            # 1. 投资组合价值曲线
            ax1 = axes[0, 0]
            portfolio_values = self.results['portfolio_values']
            ax1.plot(portfolio_values.index, portfolio_values.values, 
                    linewidth=2, color='blue')
            ax1.set_title('投资组合价值曲线')
            ax1.set_xlabel('日期')
            ax1.set_ylabel('组合价值 (¥)')
            ax1.grid(True, alpha=0.3)
            
            # 2. 收益率分布
            ax2 = axes[0, 1]
            returns = self.results['returns']
            ax2.hist(returns, bins=50, alpha=0.7, color='green', edgecolor='black')
            ax2.set_title('收益率分布')
            ax2.set_xlabel('收益率')
            ax2.set_ylabel('频数')
            ax2.grid(True, alpha=0.3)
            
            # 3. 回撤曲线
            ax3 = axes[1, 0]
            drawdown = self.results['drawdown']
            ax3.fill_between(drawdown.index, 0, drawdown.values * 100, 
                           alpha=0.3, color='red')
            ax3.plot(drawdown.index, drawdown.values * 100, 
                    linewidth=1, color='red')
            ax3.set_title('回撤曲线')
            ax3.set_xlabel('日期')
            ax3.set_ylabel('回撤 (%)')
            ax3.grid(True, alpha=0.3)
            
            # 4. 滚动夏普比率
            ax4 = axes[1, 1]
            rolling_window = min(60, len(returns))
            if rolling_window > 10:
                rolling_sharpe = returns.rolling(window=rolling_window).mean() / \
                               returns.rolling(window=rolling_window).std() * np.sqrt(252)
                ax4.plot(rolling_sharpe.index, rolling_sharpe.values, 
                        linewidth=2, color='purple')
                ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
                ax4.set_title(f'滚动夏普比率 ({rolling_window}期)')
                ax4.set_xlabel('日期')
                ax4.set_ylabel('夏普比率')
                ax4.grid(True, alpha=0.3)
            
            # 5. 月度收益率热图
            ax5 = axes[2, 0]
            if len(returns) > 0:
                # 创建月度收益率数据
                monthly_returns = returns.resample('M').apply(
                    lambda x: (1 + x).prod() - 1
                )
                
                # 创建热图数据
                years = monthly_returns.index.year.unique()
                months = range(1, 13)
                
                heatmap_data = pd.DataFrame(index=years, columns=months)
                for date, ret in monthly_returns.items():
                    heatmap_data.loc[date.year, date.month] = ret
                
                # 绘制热图
                im = ax5.imshow(heatmap_data.values * 100, cmap='RdYlGn', 
                              aspect='auto', vmin=-10, vmax=10)
                ax5.set_title('月度收益率热图 (%)')
                ax5.set_xlabel('月份')
                ax5.set_ylabel('年份')
                ax5.set_xticks(range(12))
                ax5.set_xticklabels(['1月', '2月', '3月', '4月', '5月', '6月',
                                   '7月', '8月', '9月', '10月', '11月', '12月'])
                plt.colorbar(im, ax=ax5)
            
            # 6. 绩效指标雷达图
            ax6 = axes[2, 1]
            summary = self.results['summary']
            
            metrics = ['年化收益', '夏普比率', '最大回撤', '胜率', '盈亏比']
            values = [
                min(summary['annual_return'] * 100, 50),  # 年化收益，最大50%
                min(summary['sharpe_ratio'] * 10, 10),    # 夏普比率，最大10
                min(abs(summary['max_drawdown']) * 100 * 2, 100),  # 最大回撤，越小越好
                summary['win_rate'] * 100,                # 胜率
                min(summary['profit_factor'], 5) * 20     # 盈亏比，最大5
            ]
            
            # 闭合数据
            angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False)
            values = np.concatenate((values, [values[0]]))
            angles = np.concatenate((angles, [angles[0]]))
            
            ax6.plot(angles, values, 'o-', linewidth=2)
            ax6.fill(angles, values, alpha=0.25)
            ax6.set_thetagrids(angles[:-1] * 180/np.pi, metrics)
            ax6.set_title('绩效指标雷达图')
            ax6.grid(True)
            
            plt.tight_layout()
            
            # 保存图表
            plot_path = self.output_dir / 'backtest_plots.png'
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"图表已保存: {plot_path}")
            
        except Exception as e:
            logger.error(f"生成图表失败: {e}")
    
    def _save_report(self, report_text: str):
        """保存报告"""
        report_path = self.output_dir / 'backtest_report.txt'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"报告已保存: {report_path}")
    
    def run(self):
        """运行完整回测流程"""
        # 运行回测
        asyncio.run(self.run_backtest())
        
        # 生成报告
        report = self.generate_report()
        
        # 打印报告
        print(report)
        
        return self.results


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建回测引擎
    backtest_config = {
        'initial_capital': 100000,
        'start_date': '2025-01-01',
        'end_date': '2025-06-30',
        'timeframe': '1d',
        'symbols': ['AAPL', 'MSFT', 'GOOGL'],
        'output_dir': 'backtest_results'
    }
    
    engine = BacktestEngine(backtest_config)
    
    # 运行回测
    results = engine.run()
    
    print("\n回测完成！")