"""
值班机器人管理平台 — 全局配置
"""
import os
import sys

# 判断是否为 PyInstaller 打包环境
IS_FROZEN = getattr(sys, 'frozen', False)
BASE_DIR = sys._MEIPASS if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))

# 用户数据目录（确保可写）
USER_DATA_DIR = os.path.join(os.path.expanduser('~'), '.dutybot')

APP_CONFIG = {
    # 数据库路径
    'db_path': os.path.join(USER_DATA_DIR, 'dutybot.db'),

    # 日志目录
    'log_dir': os.path.join(USER_DATA_DIR, 'logs'),

    # 上传文件缓存目录
    'upload_dir': os.path.join(USER_DATA_DIR, 'uploads'),

    # 定时任务
    'scheduler_max_workers': 3,

    # 企微消息限制（markdown 最大 4096 字符）
    'max_message_length': 4096,

    # Webhook 请求超时（秒）
    'webhook_timeout': 10,
}

# 确保必要目录存在
for dir_path in [USER_DATA_DIR, APP_CONFIG['log_dir'], APP_CONFIG['upload_dir']]:
    os.makedirs(dir_path, exist_ok=True)
