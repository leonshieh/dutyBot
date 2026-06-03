"""
工具函数模块
"""
import logging
import os
import pandas as pd
from config import APP_CONFIG


def df_to_markdown_list(df, max_rows=50):
    """将 DataFrame 转为 Markdown 无序列表格式，适合手机端阅读
    
    格式示例：
    - **姓名**: 张三 ｜ **部门**: 技术部 ｜ **日期**: 2026-06-03
    - **姓名**: 李四 ｜ **部门**: 产品部 ｜ **日期**: 2026-06-03
    """
    df = df.head(max_rows)
    lines = []
    columns = [str(c) for c in df.columns]
    for _, row in df.iterrows():
        parts = []
        for col in columns:
            v = row[col]
            if v is None or (isinstance(v, float) and pd.isna(v)):
                val_str = ''
            else:
                val_str = str(v).replace('|', '｜')
            parts.append(f'**{col}**: {val_str}')
        lines.append('- ' + ' ｜ '.join(parts))
    return '\n'.join(lines)


def setup_logging():
    """配置日志系统"""
    log_dir = APP_CONFIG['log_dir']
    os.makedirs(log_dir, exist_ok=True)

    log_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # 文件日志
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'dutybot.log'),
        encoding='utf-8',
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


def row_to_dict(row):
    """将 sqlite3.Row 转换为 dict"""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    """将 sqlite3.Row 列表转换为 dict 列表"""
    return [dict(r) for r in rows]


def get_log_file_path():
    """获取日志文件路径"""
    return os.path.join(APP_CONFIG['log_dir'], 'dutybot.log')


def read_recent_logs(lines=200):
    """读取最近的 N 行日志"""
    log_path = get_log_file_path()
    if not os.path.exists(log_path):
        return '暂无日志文件'

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return ''.join(recent)
    except Exception as e:
        return f'读取日志失败: {e}'


def read_full_logs():
    """读取完整日志内容"""
    log_path = get_log_file_path()
    if not os.path.exists(log_path):
        return '暂无日志文件'

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f'读取日志失败: {e}'
