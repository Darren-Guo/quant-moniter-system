"""
告警管理器 - 处理和发送告警通知
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

from config.settings import ALERT_CONFIG, LOG_CONFIG

logger = logging.getLogger(__name__)


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alerts_history = []
        self.max_history_size = 1000
        self.notification_channels = ALERT_CONFIG["notification_channels"]
        
    async def initialize(self):
        """初始化告警管理器"""
        logger.info("初始化告警管理器...")
        # 这里可以初始化邮件、短信、Webhook等通知渠道
        logger.info("✅ 告警管理器初始化完成")
    
    async def send_alerts(self, alerts: List[Dict], interval: str):
        """发送告警"""
        if not alerts:
            return
        
        logger.info(f"发送 {len(alerts)} 个告警 (间隔: {interval})")
        
        for alert in alerts:
            # 添加到历史记录
            self._add_to_history(alert)
            
            # 根据严重程度发送到不同渠道
            await self._dispatch_alert(alert)
    
    async def _dispatch_alert(self, alert: Dict):
        """分发告警到不同渠道"""
        severity = alert.get("severity", "medium")
        alert_type = alert.get("type", "unknown")
        message = alert.get("message", "")
        
        # 根据配置的渠道发送告警
        for channel in self.notification_channels:
            try:
                if channel == "console":
                    await self._send_to_console(alert, severity)
                elif channel == "log":
                    await self._send_to_log(alert, severity)
                # 可以扩展其他渠道：email, telegram, discord, webhook等
                
            except Exception as e:
                logger.error(f"发送告警到渠道 {channel} 失败: {e}")
    
    async def _send_to_console(self, alert: Dict, severity: str):
        """发送告警到控制台"""
        symbol = alert.get("symbol", "unknown")
        alert_type = alert.get("type", "unknown")
        message = alert.get("message", "")
        timestamp = alert.get("timestamp", datetime.now().isoformat())
        
        # 根据严重程度使用不同颜色（在支持颜色的终端中）
        if severity == "high":
            prefix = "🔴 [高危]"
        elif severity == "medium":
            prefix = "🟡 [中危]"
        else:
            prefix = "🔵 [低危]"
        
        print(f"\n{prefix} {timestamp}")
        print(f"  标的: {symbol}")
        print(f"  类型: {alert_type}")
        print(f"  信息: {message}")
        
        # 打印详细数据
        data = alert.get("data", {})
        if data:
            print(f"  数据: {json.dumps(data, indent=2, default=str)}")
        print("-" * 50)
    
    async def _send_to_log(self, alert: Dict, severity: str):
        """发送告警到日志文件"""
        log_message = {
            "timestamp": alert.get("timestamp", datetime.now().isoformat()),
            "severity": severity,
            "symbol": alert.get("symbol"),
            "type": alert.get("type"),
            "message": alert.get("message"),
            "data": alert.get("data", {})
        }
        
        # 根据严重程度使用不同的日志级别
        if severity == "high":
            logger.error(json.dumps(log_message, default=str))
        elif severity == "medium":
            logger.warning(json.dumps(log_message, default=str))
        else:
            logger.info(json.dumps(log_message, default=str))
    
    def _add_to_history(self, alert: Dict):
        """添加告警到历史记录"""
        self.alerts_history.append(alert)
        
        # 限制历史记录大小
        if len(self.alerts_history) > self.max_history_size:
            self.alerts_history = self.alerts_history[-self.max_history_size:]
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """获取最近的告警"""
        return self.alerts_history[-limit:] if self.alerts_history else []
    
    def get_alerts_by_symbol(self, symbol: str, limit: int = 20) -> List[Dict]:
        """获取指定标的的告警"""
        symbol_alerts = [alert for alert in self.alerts_history 
                        if alert.get("symbol") == symbol]
        return symbol_alerts[-limit:] if symbol_alerts else []
    
    def get_alerts_by_type(self, alert_type: str, limit: int = 20) -> List[Dict]:
        """获取指定类型的告警"""
        type_alerts = [alert for alert in self.alerts_history 
                      if alert.get("type") == alert_type]
        return type_alerts[-limit:] if type_alerts else []
    
    def get_alerts_summary(self, hours: int = 24) -> Dict:
        """获取告警摘要"""
        now = datetime.now()
        cutoff_time = now.timestamp() - (hours * 3600)
        
        recent_alerts = [
            alert for alert in self.alerts_history
            if datetime.fromisoformat(alert.get("timestamp", now.isoformat())).timestamp() > cutoff_time
        ]
        
        summary = {
            "total_alerts": len(recent_alerts),
            "by_severity": {
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "by_type": {},
            "by_symbol": {}
        }
        
        for alert in recent_alerts:
            # 统计严重程度
            severity = alert.get("severity", "medium")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # 统计类型
            alert_type = alert.get("type", "unknown")
            summary["by_type"][alert_type] = summary["by_type"].get(alert_type, 0) + 1
            
            # 统计标的
            symbol = alert.get("symbol", "unknown")
            summary["by_symbol"][symbol] = summary["by_symbol"].get(symbol, 0) + 1
        
        return summary
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理告警管理器资源...")
        # 这里可以关闭数据库连接、网络连接等
        self.alerts_history.clear()