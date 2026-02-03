#!/usr/bin/env python3
"""
量化监控系统 - 简化启动脚本
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main as system_main


def main():
    """主函数"""
    print("\n" + "="*60)
    print("📈 量化信息实时监控系统 - 启动")
    print("="*60)
    
    try:
        # 运行系统
        exit_code = asyncio.run(system_main())
        return exit_code
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
        return 0
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())