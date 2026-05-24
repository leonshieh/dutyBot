"""
Eel 桥接层 — 所有暴露给前端 JS 的 Python 函数
使用 @eel.expose 装饰器标记，前端通过 eel.func_name()() 调用
"""
import eel
from bot_manager import get_all_bots, add_bot, delete_bot, update_bot
from duty_table_manager import (
    get_all_tables,
    get_table_records,
    save_duty_table,
    delete_duty_table,
    parse_xlsx_from_bytes,
)
from message_sender import send_duty_notification, send_custom_message
from models import TimingTaskModel, SendLogModel
from database import get_connection
from scheduler_manager import add_job_for_task, remove_job_for_task, get_enabled_task_count_by_type
from utils import read_recent_logs, read_full_logs, get_log_file_path


# ==================== 初始化数据 ====================

@eel.expose
def get_all_data():
    """前端初始化时获取全部数据"""
    bots = get_all_bots()
    tables = get_all_tables()
    duty_tasks = _get_tasks_for_frontend('duty')
    custom_tasks = _get_tasks_for_frontend('custom')
    duty_logs = _get_logs_for_frontend('duty')
    custom_logs = _get_logs_for_frontend('custom')

    return {
        'bots': bots,
        'duty_tables': tables,
        'duty_tasks': duty_tasks,
        'custom_tasks': custom_tasks,
        'duty_logs': duty_logs,
        'custom_logs': custom_logs,
    }


# ==================== 机器人配置 ====================

@eel.expose
def create_bot(name, webhook, secret=''):
    """添加机器人"""
    return add_bot(name, webhook, secret)


@eel.expose
def remove_bot(bot_id):
    """删除机器人"""
    return delete_bot(bot_id)


@eel.expose
def update_bot_eel(bot_id, name, webhook, secret=''):
    """修改机器人"""
    return update_bot(bot_id, name, webhook, secret)


# ==================== 值班表管理 ====================

@eel.expose
def get_duty_tables():
    """获取所有值班表"""
    return get_all_tables()


@eel.expose
def get_duty_records(table_id):
    """获取值班表记录"""
    return get_table_records(table_id)


@eel.expose
def save_duty_table_from_frontend(file_name, records):
    """前端上传值班表：接收已解析的记录并保存"""
    return save_duty_table(file_name, records)


@eel.expose
def remove_duty_table(table_id):
    """删除值班表"""
    return delete_duty_table(table_id)


# ==================== 消息发送 ====================

@eel.expose
def send_duty_notification_eel(bot_ids, table_id, at_all=False):
    """发送值班通知"""
    return send_duty_notification(bot_ids, table_id, at_all)


@eel.expose
def send_custom_message_eel(bot_ids, message_text, at_all=False):
    """发送自定义消息"""
    return send_custom_message(bot_ids, message_text, at_all)


# ==================== 定时任务管理 ====================

@eel.expose
def add_timing_task(task_data):
    """添加定时任务并注册到调度器"""
    conn = get_connection()
    task_id = TimingTaskModel.create(conn, task_data)
    conn.commit()

    # 获取完整 task 信息
    task = conn.execute(
        'SELECT * FROM timing_tasks WHERE id = ?', (task_id,)
    ).fetchone()
    conn.close()

    if task and task['enabled']:
        add_job_for_task(task)

    return {'success': True, 'id': task_id}


@eel.expose
def remove_timing_task(task_id):
    """删除定时任务"""
    conn = get_connection()
    TimingTaskModel.delete(conn, int(task_id))
    conn.commit()
    conn.close()

    remove_job_for_task(int(task_id))
    return {'success': True}


@eel.expose
def toggle_timing_task(task_id, enabled):
    """启停定时任务"""
    conn = get_connection()
    TimingTaskModel.update_enabled(conn, int(task_id), enabled)
    conn.commit()

    task = conn.execute(
        'SELECT * FROM timing_tasks WHERE id = ?', (int(task_id),)
    ).fetchone()
    conn.close()

    if enabled:
        add_job_for_task(task)
    else:
        remove_job_for_task(int(task_id))

    return {'success': True}


# ==================== 调度状态 ====================

@eel.expose
def get_scheduler_status():
    """获取各类型定时任务的启用数量"""
    return {
        'duty_enabled': get_enabled_task_count_by_type('duty'),
        'custom_enabled': get_enabled_task_count_by_type('custom'),
    }


# ==================== 日志管理 ====================

@eel.expose
def get_send_logs(log_type=None):
    """获取发送日志（时间已转为本地时区）"""
    return _get_logs_for_frontend(log_type)


@eel.expose
def clear_send_logs(log_type=None):
    """清空发送日志"""
    conn = get_connection()
    SendLogModel.clear(conn, log_type)
    conn.commit()
    conn.close()
    return {'success': True}


# ==================== 辅助函数 ====================

def _get_tasks_for_frontend(task_type):
    """获取定时任务（转为前端格式，含扩展字段）"""
    conn = get_connection()
    tasks = TimingTaskModel.get_by_type(conn, task_type)
    conn.close()
    return [
        {
            'id': t['id'],
            'time': t['exec_time'],
            'rule': t['rule'],
            'ruleValue': t['rule_value'],
            'enabled': bool(t['enabled']),
            'bot_ids': t['bot_ids'] or '',
            'botIds': t['bot_ids'] or '',
            'message_text': t['message_text'] or '',
            'messageText': t['message_text'] or '',
            'table_id': t['table_id'],
            'tableId': t['table_id'],
            'at_all': bool(t['at_all']),
            'atAll': bool(t['at_all']),
        }
        for t in tasks
    ]


def _get_logs_for_frontend(log_type):
    """获取日志（转为前端格式，时间转为本地时区）"""
    from datetime import datetime, timezone, timedelta
    conn = get_connection()
    logs = SendLogModel.get_all(conn, log_type)
    conn.close()

    def _fmt_time(sent_at):
        """将 UTC 时间字符串转为本地时间显示"""
        if not sent_at:
            return ''
        try:
            # SQLite CURRENT_TIMESTAMP 格式: '2026-05-24 10:30:00'
            utc_dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            local_dt = utc_dt.astimezone()
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return sent_at

    return [
        {
            'id': l['id'],
            'time': _fmt_time(l['sent_at']),
            'sent_at': _fmt_time(l['sent_at']),
            'bot': l['bot_names'],
            'table': l['table_name'],
            'summary': l['message_summary'],
            'atAll': bool(l['at_all']),
            'status': l['status'],
        }
        for l in logs
    ]


# ==================== 调试日志 ====================

@eel.expose
def get_debug_logs(lines=200):
    """获取最近 N 行运行日志"""
    return read_recent_logs(lines)


@eel.expose
def get_full_logs():
    """获取完整运行日志"""
    return read_full_logs()


@eel.expose
def get_log_path():
    """获取日志文件路径"""
    return get_log_file_path()


def register_all_exposures():
    """确保所有 @eel.expose 函数被注册（导入即注册，此函数为显式调用入口）"""
    pass
