"""
SQLite 数据库连接管理与初始化
使用 sqlite3 内置模块，无额外依赖
"""
import sqlite3
import os
from config import APP_CONFIG

DB_PATH = APP_CONFIG['db_path']


def get_connection():
    """获取数据库连接，自动创建目录"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """创建所有表（如不存在），并插入默认数据（如首次初始化）"""
    conn = get_connection()
    cursor = conn.cursor()

    # ---- 机器人配置表 ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            webhook TEXT NOT NULL,
            secret TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- 值班信息表元数据 ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duty_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_name TEXT NOT NULL,
            record_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- 值班记录明细 ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duty_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            duty_date TEXT NOT NULL,
            weekday TEXT NOT NULL,
            person TEXT NOT NULL,
            FOREIGN KEY (table_id) REFERENCES duty_tables(id) ON DELETE CASCADE
        )
    ''')

    # ---- 定时任务配置表 ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timing_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL CHECK(task_type IN ('duty', 'custom')),
            exec_time TEXT NOT NULL,
            rule TEXT NOT NULL,
            rule_value TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            message_text TEXT DEFAULT '',
            bot_ids TEXT DEFAULT '',
            at_all INTEGER DEFAULT 0,
            table_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- 发送日志表 ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS send_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_type TEXT NOT NULL CHECK(log_type IN ('duty', 'custom')),
            bot_names TEXT NOT NULL,
            message_summary TEXT DEFAULT '',
            table_name TEXT DEFAULT '',
            at_all INTEGER DEFAULT 0,
            status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
            error_message TEXT DEFAULT '',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # ---- 首次初始化：插入默认机器人 ----
    existing = cursor.execute('SELECT COUNT(*) FROM bot_configs').fetchone()[0]
    if existing == 0:
        default_bots = [
            ('技术值班机器人', 'https://oapi.dingtalk.com/robot/send?access_token=tech', 'SEC****a1b2'),
            ('运维通知机器人', 'https://oapi.dingtalk.com/robot/send?access_token=ops', 'SEC****c3d4'),
            ('通知广播机器人', 'https://oapi.dingtalk.com/robot/send?access_token=bc', ''),
        ]
        cursor.executemany(
            'INSERT INTO bot_configs (name, webhook, secret) VALUES (?, ?, ?)',
            default_bots
        )
        conn.commit()

    conn.close()
