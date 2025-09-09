#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理脚本
用于启动/停止/管理MySQL容器和数据库操作
"""

import os
import sys
import subprocess
import time
import argparse
import json
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.mysql_handler import MySQLHandler
from utils.db_health_checker import DatabaseHealthChecker
from config import DATABASE_CONFIG, DATA_CONFIG


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.docker_compose_file = os.path.join(self.project_root, 'docker-compose.yml')
        self.env_file = os.path.join(self.project_root, '.env')
        
    def start_mysql_container(self) -> bool:
        """启动MySQL容器"""
        print("🚀 启动MySQL容器...")
        
        if not os.path.exists(self.docker_compose_file):
            print(f"❌ 找不到docker-compose.yml文件: {self.docker_compose_file}")
            return False
        
        try:
            # 启动容器
            cmd = ['docker', 'compose', 'up', '-d', 'mysql']
            result = subprocess.run(cmd, cwd=self.project_root, 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ MySQL容器启动成功")
                
                # 等待容器完全启动
                print("⏳ 等待MySQL服务启动...")
                self._wait_for_mysql_ready()
                
                return True
            else:
                print(f"❌ MySQL容器启动失败: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("❌ 找不到docker命令，请确保Docker已正确安装")
            return False
        except Exception as e:
            print(f"❌ 启动MySQL容器时出错: {e}")
            return False
    
    def stop_mysql_container(self) -> bool:
        """停止MySQL容器"""
        print("🛑 停止MySQL容器...")
        
        try:
            cmd = ['docker', 'compose', 'down']
            result = subprocess.run(cmd, cwd=self.project_root,
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ MySQL容器已停止")
                return True
            else:
                print(f"❌ 停止MySQL容器失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 停止MySQL容器时出错: {e}")
            return False
    
    def restart_mysql_container(self) -> bool:
        """重启MySQL容器"""
        print("🔄 重启MySQL容器...")
        return self.stop_mysql_container() and self.start_mysql_container()
    
    def _wait_for_mysql_ready(self, max_wait_time: int = 60):
        """等待MySQL服务准备就绪"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                mysql_handler = MySQLHandler()
                if mysql_handler.connect():
                    mysql_handler.disconnect()
                    print("✅ MySQL服务已就绪")
                    return True
            except Exception:
                pass
            
            print(".", end="", flush=True)
            time.sleep(2)
        
        print("\n⚠️  MySQL服务启动超时，请检查容器状态")
        return False
    
    def check_container_status(self) -> Dict[str, Any]:
        """检查容器状态"""
        try:
            cmd = ['docker', 'compose', 'ps', '--format', 'json']
            result = subprocess.run(cmd, cwd=self.project_root,
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                # 解析JSON输出
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            container_info = json.loads(line)
                            containers.append(container_info)
                        except json.JSONDecodeError:
                            pass
                
                return {
                    'success': True,
                    'containers': containers
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_database_connection(self) -> bool:
        """测试数据库连接"""
        print("🔍 测试数据库连接...")
        
        try:
            mysql_handler = MySQLHandler()
            
            if mysql_handler.connect():
                print("✅ 数据库连接成功")
                
                # 执行简单查询测试
                result = mysql_handler.execute_query("SELECT VERSION() as version")
                if result:
                    version = result[0]['version']
                    print(f"📊 MySQL版本: {version}")
                
                # 检查表是否存在
                tables = mysql_handler.execute_query("SHOW TABLES")
                if tables:
                    print(f"📋 数据库表数量: {len(tables)}")
                    for table in tables:
                        table_name = list(table.values())[0]
                        print(f"   - {table_name}")
                
                mysql_handler.disconnect()
                return True
            else:
                print("❌ 数据库连接失败")
                return False
                
        except Exception as e:
            print(f"❌ 数据库连接测试失败: {e}")
            return False
    
    def run_health_check(self) -> bool:
        """运行健康检查"""
        print("🏥 运行数据库健康检查...")
        
        try:
            health_checker = DatabaseHealthChecker()
            health_result = health_checker.check_health()
            
            status = health_checker.get_health_status()
            
            print(f"健康状态: {'✅ 健康' if health_result else '❌ 不健康'}")
            print(f"检查次数: {status['check_count']}")
            print(f"成功率: {status['success_rate']:.1f}%")
            
            if status['last_failure_time']:
                print(f"最后失败时间: {status['last_failure_time']}")
                print(f"失败原因: {status['last_failure_reason']}")
            
            return health_result
            
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return False
    
    def show_database_info(self):
        """显示数据库信息"""
        print("📊 数据库配置信息:")
        print(f"   主机: {DATABASE_CONFIG['host']}")
        print(f"   端口: {DATABASE_CONFIG['port']}")
        print(f"   数据库: {DATABASE_CONFIG['database']}")
        print(f"   用户: {DATABASE_CONFIG['user']}")
        print(f"   字符集: {DATABASE_CONFIG['charset']}")
        print(f"   数据库存储: {'启用' if DATA_CONFIG.get('save_to_db', False) else '禁用'}")
    
    def reset_database(self) -> bool:
        """重置数据库（删除所有数据）"""
        print("⚠️  警告：这将删除所有数据库中的数据！")
        confirm = input("请输入 'YES' 确认重置数据库: ")
        
        if confirm != 'YES':
            print("❌ 操作已取消")
            return False
        
        try:
            mysql_handler = MySQLHandler()
            if not mysql_handler.connect():
                print("❌ 无法连接到数据库")
                return False
            
            # 获取所有表
            tables = mysql_handler.execute_query("SHOW TABLES")
            if not tables:
                print("✅ 数据库中没有表需要清理")
                return True
            
            print("🗑️  清理数据库表...")
            for table in tables:
                table_name = list(table.values())[0]
                if table_name != 'stock_info':  # 保留股票信息表
                    mysql_handler.execute_insert(f"TRUNCATE TABLE {table_name}")
                    print(f"   - 已清空表: {table_name}")
            
            mysql_handler.disconnect()
            print("✅ 数据库重置完成")
            return True
            
        except Exception as e:
            print(f"❌ 重置数据库失败: {e}")
            return False
    
    def show_logs(self, lines: int = 50):
        """显示MySQL容器日志"""
        print(f"📋 显示MySQL容器日志 (最近{lines}行):")
        
        try:
            cmd = ['docker', 'compose', 'logs', '--tail', str(lines), 'mysql']
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ 获取日志失败: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据库管理工具')
    parser.add_argument('action', choices=[
        'start', 'stop', 'restart', 'status', 'test', 'health', 
        'info', 'reset', 'logs'
    ], help='要执行的操作')
    parser.add_argument('--lines', type=int, default=50, 
                       help='显示日志行数 (用于logs命令)')
    
    args = parser.parse_args()
    
    manager = DatabaseManager()
    
    print(f"🗄️  港股期权监控系统 - 数据库管理工具")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    if args.action == 'start':
        success = manager.start_mysql_container()
        sys.exit(0 if success else 1)
    
    elif args.action == 'stop':
        success = manager.stop_mysql_container()
        sys.exit(0 if success else 1)
    
    elif args.action == 'restart':
        success = manager.restart_mysql_container()
        sys.exit(0 if success else 1)
    
    elif args.action == 'status':
        status = manager.check_container_status()
        if status['success']:
            print("📊 容器状态:")
            for container in status['containers']:
                name = container.get('Name', 'Unknown')
                state = container.get('State', 'Unknown')
                status_info = container.get('Status', 'Unknown')
                print(f"   - {name}: {state} ({status_info})")
        else:
            print(f"❌ 获取容器状态失败: {status['error']}")
            sys.exit(1)
    
    elif args.action == 'test':
        success = manager.test_database_connection()
        sys.exit(0 if success else 1)
    
    elif args.action == 'health':
        success = manager.run_health_check()
        sys.exit(0 if success else 1)
    
    elif args.action == 'info':
        manager.show_database_info()
    
    elif args.action == 'reset':
        success = manager.reset_database()
        sys.exit(0 if success else 1)
    
    elif args.action == 'logs':
        success = manager.show_logs(args.lines)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
