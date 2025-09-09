# 数据库设置说明

## 概述

本项目已成功集成MySQL数据库用于历史数据存储，支持以下功能：
- 期权交易历史记录
- 股价历史数据
- 推送记录管理
- 系统日志存储
- 每日统计汇总

## 快速开始

### 1. 启动MySQL容器

```bash
# 启动MySQL容器
python3 manage_db.py start

# 检查容器状态
python3 manage_db.py status

# 测试数据库连接
python3 manage_db.py test
```

### 2. 数据库配置

- **端口**: 3307 (避免与系统MySQL冲突)
- **数据库**: stock_options_db
- **用户**: stock_user
- **密码**: stock_pass_2024

### 3. 环境变量

配置文件 `.env` 包含所有数据库连接参数，可根据需要修改。

## 数据库表结构

### 主要表

1. **option_trades** - 期权交易历史表
   - 存储所有期权大单交易记录
   - 包含期权类型、执行价格、成交量等详细信息

2. **stock_info** - 股票基础信息表
   - 存储监控股票的基本信息
   - 预填充了配置中的股票数据

3. **stock_prices_history** - 股价历史表
   - 存储股票价格变化历史

4. **push_records** - 推送记录表
   - 记录所有推送操作的历史

5. **daily_summary** - 每日汇总表
   - 按股票和日期汇总的交易统计

6. **system_logs** - 系统日志表
   - 存储系统运行日志

## 管理命令

### 数据库管理脚本 `manage_db.py`

```bash
# 启动MySQL容器
python3 manage_db.py start

# 停止MySQL容器  
python3 manage_db.py stop

# 重启MySQL容器
python3 manage_db.py restart

# 检查容器状态
python3 manage_db.py status

# 测试数据库连接
python3 manage_db.py test

# 运行健康检查
python3 manage_db.py health

# 显示配置信息
python3 manage_db.py info

# 查看容器日志
python3 manage_db.py logs

# 重置数据库（危险操作）
python3 manage_db.py reset
```

## 应用集成

### 数据存储

应用现在会自动将期权交易数据保存到数据库：

1. **BigOptionsProcessor** - 处理大单期权数据并保存到数据库
2. **DataHandler** - 提供统一的数据保存接口
3. **MySQLHandler** - 底层数据库操作封装

### 配置选项

在 `config.py` 中：

```python
# 启用数据库存储
DATA_CONFIG = {
    'save_to_db': True,  # 启用数据库存储
    'save_to_csv': True,  # 同时保持CSV备份
}

# 数据库连接配置
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'database': 'stock_options_db',
    'user': 'stock_user',
    'password': 'stock_pass_2024',
    # ... 其他配置
}
```

## 健康监控

系统包含完整的数据库健康检查机制：

- 自动连接检测和重连
- 定期健康检查
- 连接池管理
- 错误统计和报告

## 故障排除

### 常见问题

1. **端口冲突**
   - 默认使用3307端口避免与系统MySQL冲突
   - 如需修改端口，更新 `docker-compose.yml` 和 `config.py`

2. **连接失败**
   ```bash
   # 检查容器状态
   python3 manage_db.py status
   
   # 查看日志
   python3 manage_db.py logs
   
   # 重启容器
   python3 manage_db.py restart
   ```

3. **数据不一致**
   ```bash
   # 运行健康检查
   python3 manage_db.py health
   
   # 测试连接
   python3 manage_db.py test
   ```

## 数据备份

建议定期备份数据：

```bash
# 导出数据库
docker exec stock_options_mysql mysqldump -u stock_user -pstock_pass_2024 stock_options_db > backup.sql

# 恢复数据库
docker exec -i stock_options_mysql mysql -u stock_user -pstock_pass_2024 stock_options_db < backup.sql
```

## 性能优化

- 数据库配置已针对时序数据优化
- 包含适当的索引设计
- 支持连接池和连接复用
- 自动清理和归档机制

## 下一步

现在数据库已就绪，你可以：

1. 启动期权监控程序：`python3 option_monitor.py`
2. 启动Web面板：`python3 web_dashboard.py`
3. 查看历史数据和统计报表
4. 根据需要调整监控参数和过滤条件

所有历史数据将自动保存到数据库中，支持长期分析和趋势研究。
