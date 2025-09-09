-- 港股期权监控系统数据库初始化脚本
-- 创建时间: 2024-01-14
-- 描述: 创建历史数据存储表结构

USE stock_options_db;

-- 设置时区
SET time_zone = '+08:00';

-- 1. 股票基础信息表
CREATE TABLE IF NOT EXISTS stock_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL UNIQUE COMMENT '股票代码 如HK.00700',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票名称',
    market VARCHAR(10) NOT NULL DEFAULT 'HK' COMMENT '市场',
    sector VARCHAR(50) COMMENT '行业分类',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_market (market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票基础信息表';

-- 2. 期权交易历史表（主表）
CREATE TABLE IF NOT EXISTS option_trades (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_time DATETIME NOT NULL COMMENT '交易时间',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票名称',
    stock_price DECIMAL(10,3) COMMENT '股票当前价格',
    option_code VARCHAR(50) NOT NULL COMMENT '期权代码',
    option_type VARCHAR(10) NOT NULL COMMENT '期权类型 Call/Put',
    strike_price DECIMAL(10,3) COMMENT '执行价格',
    expiry_date DATE COMMENT '到期日期',
    volume BIGINT NOT NULL DEFAULT 0 COMMENT '成交量',
    turnover DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '成交额(港币)',
    premium DECIMAL(8,4) COMMENT '权利金',
    trade_direction VARCHAR(10) COMMENT '交易方向 买入/卖出',
    bid_price DECIMAL(8,4) COMMENT '买入价',
    ask_price DECIMAL(8,4) COMMENT '卖出价',
    last_price DECIMAL(8,4) COMMENT '最新价',
    change_rate DECIMAL(8,4) COMMENT '涨跌幅',
    implied_volatility DECIMAL(8,4) COMMENT '隐含波动率',
    delta_value DECIMAL(8,4) COMMENT 'Delta值',
    gamma_value DECIMAL(8,4) COMMENT 'Gamma值',
    theta_value DECIMAL(8,4) COMMENT 'Theta值',
    vega_value DECIMAL(8,4) COMMENT 'Vega值',
    open_interest BIGINT COMMENT '持仓量',
    time_to_expiry INT COMMENT '距离到期天数',
    moneyness VARCHAR(10) COMMENT '价值状态 ITM/ATM/OTM',
    data_source VARCHAR(20) DEFAULT 'futu' COMMENT '数据来源',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_trade_time (trade_time),
    INDEX idx_stock_code (stock_code),
    INDEX idx_option_code (option_code),
    INDEX idx_option_type (option_type),
    INDEX idx_volume (volume),
    INDEX idx_turnover (turnover),
    INDEX idx_expiry_date (expiry_date),
    INDEX idx_stock_trade_time (stock_code, trade_time),
    INDEX idx_composite (stock_code, option_type, trade_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='期权交易历史表';

-- 3. 股价历史表
CREATE TABLE IF NOT EXISTS stock_prices_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票名称',
    price DECIMAL(10,3) NOT NULL COMMENT '股价',
    change_amount DECIMAL(10,3) COMMENT '涨跌金额',
    change_rate DECIMAL(8,4) COMMENT '涨跌幅',
    volume BIGINT COMMENT '成交量',
    turnover DECIMAL(15,2) COMMENT '成交额',
    high_price DECIMAL(10,3) COMMENT '最高价',
    low_price DECIMAL(10,3) COMMENT '最低价',
    open_price DECIMAL(10,3) COMMENT '开盘价',
    prev_close DECIMAL(10,3) COMMENT '前收盘价',
    market_cap DECIMAL(20,2) COMMENT '市值',
    pe_ratio DECIMAL(8,2) COMMENT '市盈率',
    record_time DATETIME NOT NULL COMMENT '记录时间',
    data_source VARCHAR(20) DEFAULT 'futu' COMMENT '数据来源',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_stock_code (stock_code),
    INDEX idx_record_time (record_time),
    INDEX idx_stock_time (stock_code, record_time),
    UNIQUE KEY uk_stock_time (stock_code, record_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股价历史表';

-- 4. 推送记录历史表
CREATE TABLE IF NOT EXISTS push_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    option_id VARCHAR(100) NOT NULL COMMENT '期权记录ID',
    push_type VARCHAR(20) NOT NULL COMMENT '推送类型 wework/email/mac',
    push_status VARCHAR(20) NOT NULL COMMENT '推送状态 success/failed',
    push_content TEXT COMMENT '推送内容',
    push_time DATETIME NOT NULL COMMENT '推送时间',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_option_id (option_id),
    INDEX idx_push_type (push_type),
    INDEX idx_push_time (push_time),
    INDEX idx_push_status (push_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推送记录历史表';

-- 5. 每日汇总统计表
CREATE TABLE IF NOT EXISTS daily_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    summary_date DATE NOT NULL COMMENT '汇总日期',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票名称',
    total_trades INT DEFAULT 0 COMMENT '总交易笔数',
    total_volume BIGINT DEFAULT 0 COMMENT '总成交量',
    total_turnover DECIMAL(20,2) DEFAULT 0 COMMENT '总成交额',
    call_trades INT DEFAULT 0 COMMENT 'Call期权交易数',
    put_trades INT DEFAULT 0 COMMENT 'Put期权交易数',
    call_volume BIGINT DEFAULT 0 COMMENT 'Call期权成交量',
    put_volume BIGINT DEFAULT 0 COMMENT 'Put期权成交量',
    call_turnover DECIMAL(20,2) DEFAULT 0 COMMENT 'Call期权成交额',
    put_turnover DECIMAL(20,2) DEFAULT 0 COMMENT 'Put期权成交额',
    avg_premium DECIMAL(8,4) COMMENT '平均权利金',
    max_single_trade DECIMAL(15,2) COMMENT '最大单笔交易额',
    active_options_count INT DEFAULT 0 COMMENT '活跃期权数量',
    unique_expiry_dates INT DEFAULT 0 COMMENT '涉及到期日数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_date_stock (summary_date, stock_code),
    INDEX idx_summary_date (summary_date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_total_turnover (total_turnover)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日汇总统计表';

-- 6. 系统运行日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    log_level VARCHAR(10) NOT NULL COMMENT '日志级别 INFO/ERROR/WARNING',
    module_name VARCHAR(50) NOT NULL COMMENT '模块名称',
    function_name VARCHAR(100) COMMENT '函数名称',
    message TEXT NOT NULL COMMENT '日志消息',
    error_details TEXT COMMENT '错误详情',
    execution_time DECIMAL(10,4) COMMENT '执行时间(秒)',
    log_time DATETIME NOT NULL COMMENT '日志时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_log_level (log_level),
    INDEX idx_module_name (module_name),
    INDEX idx_log_time (log_time),
    INDEX idx_level_time (log_level, log_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统运行日志表';

-- 插入监控的股票基础信息
INSERT INTO stock_info (stock_code, stock_name, market, sector) VALUES
('HK.00700', '腾讯控股', 'HK', '科技'),
('HK.09988', '阿里巴巴-SW', 'HK', '科技'),
('HK.03690', '美团-W', 'HK', '科技'),
('HK.01810', '小米集团-W', 'HK', '科技'),
('HK.09618', '京东集团-SW', 'HK', '科技'),
('HK.02318', '中国平安', 'HK', '金融'),
('HK.00388', '香港交易所', 'HK', '金融'),
('HK.00981', '中芯国际', 'HK', '科技')
ON DUPLICATE KEY UPDATE 
    stock_name = VALUES(stock_name),
    sector = VALUES(sector),
    updated_at = CURRENT_TIMESTAMP;

-- 创建数据库用户权限（如果不存在）
-- 注意：这些命令在容器初始化时会自动执行
FLUSH PRIVILEGES;
