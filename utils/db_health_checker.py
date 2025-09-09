# -*- coding: utf-8 -*-
"""
数据库健康检查和连接管理工具
"""

import logging
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from utils.mysql_handler import MySQLHandler
from config import DATABASE_CONFIG, DATA_CONFIG


class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    def __init__(self):
        self.logger = logging.getLogger('OptionMonitor.DatabaseHealthChecker')
        self.mysql_handler = None
        self.last_check_time = None
        self.check_interval = 60  # 1分钟检查一次
        self.is_healthy = False
        self.health_check_thread = None
        self.stop_event = threading.Event()
        
        # 健康检查统计
        self.check_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_failure_time = None
        self.last_failure_reason = None
        
        # 初始化MySQL处理器
        if DATA_CONFIG.get('save_to_db', False):
            self._initialize_mysql_handler()
    
    def _initialize_mysql_handler(self):
        """初始化MySQL处理器"""
        try:
            self.mysql_handler = MySQLHandler()
            self.logger.info("数据库健康检查器初始化成功")
        except Exception as e:
            self.logger.error(f"数据库健康检查器初始化失败: {e}")
            self.mysql_handler = None
    
    def check_health(self) -> bool:
        """执行健康检查"""
        if not self.mysql_handler:
            self.logger.warning("MySQL处理器未初始化，跳过健康检查")
            return False
        
        self.check_count += 1
        self.last_check_time = datetime.now()
        
        try:
            # 执行健康检查
            health_result = self.mysql_handler.health_check()
            
            if health_result:
                self.success_count += 1
                self.is_healthy = True
                self.logger.debug("数据库健康检查通过")
                return True
            else:
                self.failure_count += 1
                self.is_healthy = False
                self.last_failure_time = datetime.now()
                self.last_failure_reason = "Health check query failed"
                self.logger.warning("数据库健康检查失败")
                return False
                
        except Exception as e:
            self.failure_count += 1
            self.is_healthy = False
            self.last_failure_time = datetime.now()
            self.last_failure_reason = str(e)
            self.logger.error(f"数据库健康检查异常: {e}")
            return False
    
    def start_monitoring(self):
        """启动健康监控线程"""
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.logger.warning("健康监控线程已在运行")
            return
        
        if not self.mysql_handler:
            self.logger.warning("MySQL处理器未初始化，无法启动健康监控")
            return
        
        self.stop_event.clear()
        self.health_check_thread = threading.Thread(
            target=self._monitoring_loop,
            name="DatabaseHealthMonitor",
            daemon=True
        )
        self.health_check_thread.start()
        self.logger.info("数据库健康监控线程已启动")
    
    def stop_monitoring(self):
        """停止健康监控线程"""
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.stop_event.set()
            self.health_check_thread.join(timeout=5)
            self.logger.info("数据库健康监控线程已停止")
    
    def _monitoring_loop(self):
        """健康监控循环"""
        while not self.stop_event.is_set():
            try:
                self.check_health()
                
                # 如果数据库不健康，尝试重连
                if not self.is_healthy and self.mysql_handler:
                    self.logger.info("数据库不健康，尝试重新连接...")
                    if self.mysql_handler.connect():
                        self.logger.info("数据库重连成功")
                    else:
                        self.logger.error("数据库重连失败")
                
                # 等待下次检查
                self.stop_event.wait(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"健康监控循环异常: {e}")
                self.stop_event.wait(self.check_interval)
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态信息"""
        status = {
            'is_healthy': self.is_healthy,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'check_count': self.check_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': (self.success_count / self.check_count * 100) if self.check_count > 0 else 0,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_failure_reason': self.last_failure_reason,
            'monitoring_active': self.health_check_thread and self.health_check_thread.is_alive(),
        }
        
        # 添加连接信息
        if self.mysql_handler:
            connection_info = self.mysql_handler.get_connection_info()
            status.update({
                'database_host': connection_info.get('host'),
                'database_port': connection_info.get('port'),
                'database_name': connection_info.get('database'),
                'database_connected': connection_info.get('connected', False),
                'last_ping_time': connection_info.get('last_ping')
            })
        
        return status
    
    def force_reconnect(self) -> bool:
        """强制重新连接数据库"""
        if not self.mysql_handler:
            self.logger.warning("MySQL处理器未初始化，无法重连")
            return False
        
        try:
            self.logger.info("强制重新连接数据库...")
            self.mysql_handler.disconnect()
            success = self.mysql_handler.connect()
            
            if success:
                self.logger.info("数据库强制重连成功")
                # 立即执行一次健康检查
                self.check_health()
            else:
                self.logger.error("数据库强制重连失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"数据库强制重连异常: {e}")
            return False
    
    def get_mysql_handler(self) -> Optional[MySQLHandler]:
        """获取MySQL处理器实例"""
        return self.mysql_handler
    
    def is_database_available(self) -> bool:
        """检查数据库是否可用"""
        return self.is_healthy and self.mysql_handler is not None
    
    def get_uptime_info(self) -> Dict[str, Any]:
        """获取运行时间信息"""
        if not self.last_check_time:
            return {'uptime': 0, 'status': 'Not started'}
        
        uptime_seconds = (datetime.now() - self.last_check_time).total_seconds()
        uptime_hours = uptime_seconds / 3600
        
        return {
            'uptime_seconds': int(uptime_seconds),
            'uptime_hours': round(uptime_hours, 2),
            'status': 'Healthy' if self.is_healthy else 'Unhealthy',
            'check_interval': self.check_interval
        }
    
    def reset_statistics(self):
        """重置健康检查统计"""
        self.check_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_failure_time = None
        self.last_failure_reason = None
        self.logger.info("健康检查统计已重置")
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop_monitoring()
        except:
            pass


# 全局健康检查器实例
_health_checker_instance = None


def get_health_checker() -> DatabaseHealthChecker:
    """获取全局健康检查器实例"""
    global _health_checker_instance
    if _health_checker_instance is None:
        _health_checker_instance = DatabaseHealthChecker()
    return _health_checker_instance


def start_database_monitoring():
    """启动数据库监控"""
    health_checker = get_health_checker()
    health_checker.start_monitoring()


def stop_database_monitoring():
    """停止数据库监控"""
    health_checker = get_health_checker()
    health_checker.stop_monitoring()


def check_database_health() -> bool:
    """检查数据库健康状态"""
    health_checker = get_health_checker()
    return health_checker.check_health()


def get_database_status() -> Dict[str, Any]:
    """获取数据库状态信息"""
    health_checker = get_health_checker()
    return health_checker.get_health_status()
