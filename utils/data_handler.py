# -*- coding: utf-8 -*-
"""
数据处理模块
"""

import pandas as pd
import os
import logging
from typing import Dict
from config import DATA_CONFIG
from utils.mysql_handler import MySQLHandler


class DataHandler:
    """数据处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger('OptionMonitor.DataHandler')
        self._ensure_data_directory()
        
        # 初始化MySQL处理器
        self.mysql_handler = None
        if DATA_CONFIG.get('save_to_db', False):
            try:
                self.mysql_handler = MySQLHandler()
                if self.mysql_handler.connect():
                    self.logger.info("MySQL数据库处理器初始化成功")
                else:
                    self.logger.warning("MySQL数据库连接失败，将使用文件存储")
                    self.mysql_handler = None
            except Exception as e:
                self.logger.error(f"MySQL数据库处理器初始化失败: {e}")
                self.mysql_handler = None
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        if DATA_CONFIG['save_to_csv']:
            data_dir = os.path.dirname(DATA_CONFIG['csv_path'])
            if data_dir:
                os.makedirs(data_dir, exist_ok=True)
    
    def save_trade(self, trade_info: Dict):
        """保存交易数据"""
        if DATA_CONFIG['save_to_csv']:
            self._save_to_csv(trade_info)
        
        if DATA_CONFIG['save_to_db']:
            self._save_to_database(trade_info)
    
    def _save_to_csv(self, trade_info: Dict):
        """保存到CSV文件"""
        try:
            csv_path = DATA_CONFIG['csv_path']
            
            # 准备数据
            df_new = pd.DataFrame([trade_info])
            
            # 如果文件存在，追加数据；否则创建新文件
            if os.path.exists(csv_path):
                df_new.to_csv(csv_path, mode='a', header=False, index=False, encoding='utf-8')
            else:
                df_new.to_csv(csv_path, mode='w', header=True, index=False, encoding='utf-8')
            
            self.logger.debug(f"交易数据已保存到CSV: {trade_info['option_code']}")
            
        except Exception as e:
            self.logger.error(f"保存CSV数据失败: {e}")
    
    def _save_to_database(self, trade_info: Dict):
        """保存到数据库"""
        if not self.mysql_handler:
            self.logger.warning("MySQL处理器未初始化，跳过数据库保存")
            return False
        
        try:
            # 保存期权交易数据
            success = self.mysql_handler.save_option_trade(trade_info)
            if success:
                self.logger.debug(f"交易数据已保存到数据库: {trade_info.get('option_code', 'Unknown')}")
            else:
                self.logger.error(f"保存交易数据到数据库失败: {trade_info.get('option_code', 'Unknown')}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"保存数据库数据失败: {e}")
            return False
    
    def load_historical_data(self, days: int = 7) -> pd.DataFrame:
        """加载历史数据（优先从数据库，降级到CSV）"""
        # 优先从数据库加载
        if self.mysql_handler and DATA_CONFIG.get('save_to_db', False):
            try:
                trades_data = self.mysql_handler.get_recent_trades(hours=days * 24)
                if trades_data:
                    df = pd.DataFrame(trades_data)
                    # 转换时间戳列名以保持兼容性
                    if 'trade_time' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['trade_time'])
                    self.logger.debug(f"从数据库加载了 {len(df)} 条历史数据")
                    return df
            except Exception as e:
                self.logger.error(f"从数据库加载历史数据失败: {e}")
        
        # 降级到CSV文件
        try:
            if not DATA_CONFIG['save_to_csv'] or not os.path.exists(DATA_CONFIG['csv_path']):
                return pd.DataFrame()
            
            df = pd.read_csv(DATA_CONFIG['csv_path'], encoding='utf-8')
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 筛选最近几天的数据
            cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days)
            recent_data = df[df['timestamp'] >= cutoff_date]
            
            self.logger.debug(f"从CSV文件加载了 {len(recent_data)} 条历史数据")
            return recent_data
            
        except Exception as e:
            self.logger.error(f"加载历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            df = self.load_historical_data()
            
            if df.empty:
                return {'total_trades': 0}
            
            stats = {
                'total_trades': len(df),
                'unique_stocks': df['stock_code'].nunique(),
                'unique_options': df['option_code'].nunique(),
                'total_volume': df['volume'].sum(),
                'total_turnover': df['turnover'].sum(),
                'avg_trade_size': df['volume'].mean(),
                'latest_trade_time': df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {'error': str(e)}