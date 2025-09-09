# -*- coding: utf-8 -*-
"""
MySQL数据库操作工具类
提供数据库连接、数据插入、查询等功能
"""

import pymysql
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import threading
import time
from config import DATABASE_CONFIG


class MySQLHandler:
    """MySQL数据库操作处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger('OptionMonitor.MySQLHandler')
        self.connection = None
        self.connection_lock = threading.Lock()
        self.last_ping_time = 0
        self.ping_interval = 300  # 5分钟ping一次
        
        # 从环境变量读取配置（优先级高于配置文件）
        self.config = self._get_db_config()
        
    def _get_db_config(self) -> Dict[str, Any]:
        """获取数据库配置，支持环境变量覆盖"""
        config = DATABASE_CONFIG.copy()
        
        # 环境变量覆盖
        env_mappings = {
            'DB_HOST': 'host',
            'DB_PORT': 'port', 
            'DB_NAME': 'database',
            'DB_USER': 'user',
            'DB_PASSWORD': 'password',
            'DB_CHARSET': 'charset'
        }
        
        for env_key, config_key in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value:
                if config_key == 'port':
                    config[config_key] = int(env_value)
                else:
                    config[config_key] = env_value
                    
        return config
    
    def connect(self) -> bool:
        """连接到MySQL数据库"""
        try:
            with self.connection_lock:
                if self.connection and self.connection.open:
                    return True
                
                self.logger.info(f"正在连接MySQL数据库: {self.config['host']}:{self.config['port']}")
                
                self.connection = pymysql.connect(
                    host=self.config['host'],
                    port=self.config['port'],
                    user=self.config['user'],
                    password=self.config['password'],
                    database=self.config['database'],
                    charset=self.config['charset'],
                    autocommit=self.config.get('autocommit', True),
                    connect_timeout=self.config.get('connect_timeout', 10),
                    read_timeout=self.config.get('read_timeout', 10),
                    write_timeout=self.config.get('write_timeout', 10)
                )
                
                self.last_ping_time = time.time()
                self.logger.info("MySQL数据库连接成功")
                return True
                
        except Exception as e:
            self.logger.error(f"MySQL数据库连接失败: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        try:
            with self.connection_lock:
                if self.connection:
                    self.connection.close()
                    self.connection = None
                    self.logger.info("MySQL数据库连接已断开")
        except Exception as e:
            self.logger.error(f"断开数据库连接时出错: {e}")
    
    def _ensure_connection(self) -> bool:
        """确保数据库连接可用"""
        current_time = time.time()
        
        # 检查是否需要ping
        if current_time - self.last_ping_time > self.ping_interval:
            try:
                if self.connection and self.connection.open:
                    self.connection.ping(reconnect=True)
                    self.last_ping_time = current_time
            except Exception as e:
                self.logger.warning(f"数据库ping失败，尝试重连: {e}")
                return self.connect()
        
        # 检查连接状态
        if not self.connection or not self.connection.open:
            return self.connect()
        
        return True
    
    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> Optional[List[Dict[str, Any]]]:
        """执行查询语句"""
        if not self._ensure_connection():
            return None
        
        try:
            with self.connection_lock:
                with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                    return result
        except Exception as e:
            self.logger.error(f"执行查询失败: {e}, SQL: {sql}")
            return None
    
    def execute_insert(self, sql: str, params: Optional[Tuple] = None) -> bool:
        """执行插入语句"""
        if not self._ensure_connection():
            return False
        
        try:
            with self.connection_lock:
                with self.connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    if not self.config.get('autocommit', True):
                        self.connection.commit()
                    return True
        except Exception as e:
            self.logger.error(f"执行插入失败: {e}, SQL: {sql}")
            if not self.config.get('autocommit', True):
                try:
                    self.connection.rollback()
                except:
                    pass
            return False
    
    def execute_batch_insert(self, sql: str, params_list: List[Tuple]) -> bool:
        """执行批量插入"""
        if not self._ensure_connection():
            return False
        
        if not params_list:
            return True
        
        try:
            with self.connection_lock:
                with self.connection.cursor() as cursor:
                    cursor.executemany(sql, params_list)
                    if not self.config.get('autocommit', True):
                        self.connection.commit()
                    self.logger.debug(f"批量插入成功，影响行数: {len(params_list)}")
                    return True
        except Exception as e:
            self.logger.error(f"批量插入失败: {e}, SQL: {sql}")
            if not self.config.get('autocommit', True):
                try:
                    self.connection.rollback()
                except:
                    pass
            return False
    
    def save_option_trade(self, trade_data: Dict[str, Any]) -> bool:
        """保存期权交易数据"""
        sql = """
        INSERT INTO option_trades (
            trade_time, stock_code, stock_name, stock_price, option_code, 
            option_type, strike_price, expiry_date, volume, turnover, 
            premium, trade_direction, bid_price, ask_price, last_price,
            change_rate, implied_volatility, delta_value, gamma_value,
            theta_value, vega_value, open_interest, time_to_expiry,
            moneyness, data_source
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        """
        
        # 处理NULL值，确保空字符串不会导致日期字段错误
        expiry_date = trade_data.get('expiry_date')
        if expiry_date == '' or expiry_date is None:
            expiry_date = None
            
        params = (
            trade_data.get('trade_time', datetime.now()),
            trade_data.get('stock_code', ''),
            trade_data.get('stock_name', ''),
            trade_data.get('stock_price'),
            trade_data.get('option_code', ''),
            trade_data.get('option_type', ''),
            trade_data.get('strike_price'),
            expiry_date,
            trade_data.get('volume', 0),
            trade_data.get('turnover', 0),
            trade_data.get('premium'),
            trade_data.get('trade_direction', ''),
            trade_data.get('bid_price'),
            trade_data.get('ask_price'),
            trade_data.get('last_price'),
            trade_data.get('change_rate'),
            trade_data.get('implied_volatility'),
            trade_data.get('delta_value'),
            trade_data.get('gamma_value'),
            trade_data.get('theta_value'),
            trade_data.get('vega_value'),
            trade_data.get('open_interest'),
            trade_data.get('time_to_expiry'),
            trade_data.get('moneyness', ''),
            trade_data.get('data_source', 'futu')
        )
        
        return self.execute_insert(sql, params)
    
    def save_stock_price(self, price_data: Dict[str, Any]) -> bool:
        """保存股价数据"""
        sql = """
        INSERT INTO stock_prices_history (
            stock_code, stock_name, price, change_amount, change_rate,
            volume, turnover, high_price, low_price, open_price,
            prev_close, market_cap, pe_ratio, record_time, data_source
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            price = VALUES(price),
            change_amount = VALUES(change_amount),
            change_rate = VALUES(change_rate),
            volume = VALUES(volume),
            turnover = VALUES(turnover),
            high_price = VALUES(high_price),
            low_price = VALUES(low_price),
            open_price = VALUES(open_price),
            prev_close = VALUES(prev_close),
            market_cap = VALUES(market_cap),
            pe_ratio = VALUES(pe_ratio)
        """
        
        params = (
            price_data.get('stock_code', ''),
            price_data.get('stock_name', ''),
            price_data.get('price', 0),
            price_data.get('change_amount'),
            price_data.get('change_rate'),
            price_data.get('volume'),
            price_data.get('turnover'),
            price_data.get('high_price'),
            price_data.get('low_price'),
            price_data.get('open_price'),
            price_data.get('prev_close'),
            price_data.get('market_cap'),
            price_data.get('pe_ratio'),
            price_data.get('record_time', datetime.now()),
            price_data.get('data_source', 'futu')
        )
        
        return self.execute_insert(sql, params)
    
    def save_push_record(self, push_data: Dict[str, Any]) -> bool:
        """保存推送记录"""
        sql = """
        INSERT INTO push_records (
            option_id, push_type, push_status, push_content,
            push_time, error_message, retry_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            push_data.get('option_id', ''),
            push_data.get('push_type', ''),
            push_data.get('push_status', ''),
            push_data.get('push_content', ''),
            push_data.get('push_time', datetime.now()),
            push_data.get('error_message', ''),
            push_data.get('retry_count', 0)
        )
        
        return self.execute_insert(sql, params)
    
    def get_recent_trades(self, stock_code: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近的交易记录"""
        where_clause = "WHERE trade_time >= %s"
        params = [datetime.now() - timedelta(hours=hours)]
        
        if stock_code:
            where_clause += " AND stock_code = %s"
            params.append(stock_code)
        
        sql = f"""
        SELECT * FROM option_trades 
        {where_clause}
        ORDER BY trade_time DESC
        LIMIT 1000
        """
        
        return self.execute_query(sql, tuple(params)) or []
    
    def get_daily_summary(self, date: str = None) -> List[Dict[str, Any]]:
        """获取每日汇总数据"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        sql = """
        SELECT * FROM daily_summary 
        WHERE summary_date = %s
        ORDER BY total_turnover DESC
        """
        
        return self.execute_query(sql, (date,)) or []
    
    def update_daily_summary(self, date: str = None) -> bool:
        """更新每日汇总统计"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        sql = """
        INSERT INTO daily_summary (
            summary_date, stock_code, stock_name, total_trades, total_volume,
            total_turnover, call_trades, put_trades, call_volume, put_volume,
            call_turnover, put_turnover, avg_premium, max_single_trade,
            active_options_count, unique_expiry_dates
        )
        SELECT 
            DATE(trade_time) as summary_date,
            stock_code,
            stock_name,
            COUNT(*) as total_trades,
            SUM(volume) as total_volume,
            SUM(turnover) as total_turnover,
            SUM(CASE WHEN option_type = 'Call' THEN 1 ELSE 0 END) as call_trades,
            SUM(CASE WHEN option_type = 'Put' THEN 1 ELSE 0 END) as put_trades,
            SUM(CASE WHEN option_type = 'Call' THEN volume ELSE 0 END) as call_volume,
            SUM(CASE WHEN option_type = 'Put' THEN volume ELSE 0 END) as put_volume,
            SUM(CASE WHEN option_type = 'Call' THEN turnover ELSE 0 END) as call_turnover,
            SUM(CASE WHEN option_type = 'Put' THEN turnover ELSE 0 END) as put_turnover,
            AVG(premium) as avg_premium,
            MAX(turnover) as max_single_trade,
            COUNT(DISTINCT option_code) as active_options_count,
            COUNT(DISTINCT expiry_date) as unique_expiry_dates
        FROM option_trades 
        WHERE DATE(trade_time) = %s
        GROUP BY DATE(trade_time), stock_code, stock_name
        ON DUPLICATE KEY UPDATE
            total_trades = VALUES(total_trades),
            total_volume = VALUES(total_volume),
            total_turnover = VALUES(total_turnover),
            call_trades = VALUES(call_trades),
            put_trades = VALUES(put_trades),
            call_volume = VALUES(call_volume),
            put_volume = VALUES(put_volume),
            call_turnover = VALUES(call_turnover),
            put_turnover = VALUES(put_turnover),
            avg_premium = VALUES(avg_premium),
            max_single_trade = VALUES(max_single_trade),
            active_options_count = VALUES(active_options_count),
            unique_expiry_dates = VALUES(unique_expiry_dates),
            updated_at = CURRENT_TIMESTAMP
        """
        
        return self.execute_insert(sql, (date,))
    
    def health_check(self) -> bool:
        """数据库健康检查"""
        try:
            result = self.execute_query("SELECT 1 as health_check")
            return result is not None and len(result) > 0
        except Exception as e:
            self.logger.error(f"数据库健康检查失败: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'host': self.config['host'],
            'port': self.config['port'],
            'database': self.config['database'],
            'user': self.config['user'],
            'connected': self.connection is not None and self.connection.open,
            'last_ping': datetime.fromtimestamp(self.last_ping_time) if self.last_ping_time > 0 else None
        }
    
    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.disconnect()
        except:
            pass
