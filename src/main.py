#!/usr/bin/env python3
"""
量化信息实时监控系统 - 主程序
"""

import asyncio
import logging
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LOG_CONFIG
from src.monitor import QuantMonitor
from src.data_fetcher import DataFetcher
from src.alert_manager import AlertManager

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOG_CONFIG["file"]),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class QuantMonitorSystem:
    """量化监控系统主类"""
    
    def __init__(self):
        self.monitor = QuantMonitor()
        self.data_fetcher = DataFetcher()
        self.alert_manager = AlertManager()
        self.is_running = False
        
    async def start(self):
        """启动监控系统"""
        logger.info("🚀 启动量化信息实时监控系统...")
        
        try:
            # 初始化组件
            await self.data_fetcher.initialize()
            await self.alert_manager.initialize()
            
            # 启动监控
            self.is_running = True
            await self.monitor.start()
            
            logger.info("✅ 量化监控系统已启动")
            
            # 保持运行
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 收到停止信号")
        except Exception as e:
            logger.error(f"❌ 系统运行出错: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """停止监控系统"""
        logger.info("🛑 正在停止监控系统...")
        self.is_running = False
        await self.monitor.stop()
        await self.data_fetcher.cleanup()
        await self.alert_manager.cleanup()
        logger.info("✅ 监控系统已停止")


async def main():
    """主函数"""
    system = QuantMonitorSystem()
    
    # 显示启动信息
    print("\n" + "="*50)
    print("📈 量化信息实时监控系统")
    print("="*50)
    print("功能:")
    print("  • 实时监控股票、加密货币、指数")
    print("  • 技术指标计算 (RSI, MACD, 布林带等)")
    print("  • 异常价格和成交量告警")
    print("  • WebSocket实时数据推送")
    print("  • REST API数据查询")
    print("="*50)
    
    try:
        await system.start()
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)