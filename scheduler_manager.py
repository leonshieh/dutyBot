"""
定时任务调度模块 — 基于 APScheduler
实现 cron 定时触发值班通知和自定义消息发送
"""
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import get_connection
from models import TimingTaskModel
from message_sender import send_duty_notification, send_custom_message

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(
    job_defaults={'misfire_grace_time': 300},  # 错过 5 分钟内仍执行
)

# 存储 job_id → task_id 的映射
_job_task_map = {}


def _execute_duty_task(task):
    """执行值班通知定时任务（由调度器回调）"""
    try:
        bot_ids = [int(x.strip()) for x in str(task['bot_ids']).split(',') if x.strip()]
        table_id = str(task['table_id']) if task['table_id'] else ''
        at_all = bool(task['at_all'])
        if not bot_ids or not table_id:
            logger.warning(f"[定时-值班通知] task_id={task['id']} 配置不完整，跳过")
            return
        if table_id.startswith('upload:'):
            # 已上传文件：使用公共函数构建今日+下次值班 Markdown
            from config import APP_CONFIG
            from message_sender import build_duty_markdown_from_excel, _send_to_bots
            file_name = table_id.replace('upload:', '')
            path = os.path.join(APP_CONFIG['upload_dir'], file_name)
            if not os.path.exists(path):
                logger.error(f"[定时-值班通知] 文件不存在: {path}")
                return
            message = build_duty_markdown_from_excel(path)
            if message is None:
                logger.error(f"[定时-值班通知] 无法解析文件: {path}")
                return
            # 拼接自定义文本
            custom = (task['message_text'] or '').strip()
            if custom:
                message += '\n\n---\n\n' + custom
            result = _send_to_bots(bot_ids=bot_ids, title='值班信息通知', message=message, at_all=at_all, log_type='duty')
        else:
            result = send_duty_notification(bot_ids, int(table_id), at_all, (task['message_text'] or ''))
        logger.info(f"[定时-值班通知] task_id={task['id']} -> {result}")
    except Exception as e:
        logger.error(f"[定时-值班通知] task_id={task['id']} 执行异常: {e}")


def _execute_custom_task(task):
    """执行自定义消息定时任务（由调度器回调）"""
    try:
        bot_ids = [int(x.strip()) for x in str(task['bot_ids']).split(',') if x.strip()]
        message = task['message_text']
        at_all = bool(task['at_all'])
        if bot_ids and message:
            result = send_custom_message(bot_ids, message, at_all)
            logger.info(f"[定时-自定义消息] task_id={task['id']} -> {result}")
        else:
            logger.warning(f"[定时-自定义消息] task_id={task['id']} 配置不完整，跳过")
    except Exception as e:
        logger.error(f"[定时-自定义消息] task_id={task['id']} 执行异常: {e}")


def _build_cron_trigger(rule_value, exec_time):
    """根据规则值构建 APScheduler CronTrigger"""
    parts = exec_time.split(':')
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0

    if rule_value == 'daily':
        return CronTrigger(hour=hour, minute=minute)
    elif rule_value == 'weekday':
        return CronTrigger(hour=hour, minute=minute, day_of_week='mon-fri')
    elif rule_value.startswith('weekly_'):
        # 格式: weekly_1,2,3（前端数字：0=周日, 1=周一, ..., 6=周六）
        # APScheduler 数字映射不同：0=周一, 1=周二, ..., 6=周日
        # 转换为文本名称避免歧义
        days_str = rule_value.replace('weekly_', '')
        aps_names = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        converted = []
        for d in days_str.split(','):
            d = d.strip()
            if d:
                # 前端值 → APScheduler 索引: (fe_val + 6) % 7
                aps_idx = (int(d) + 6) % 7
                converted.append(aps_names[aps_idx])
        return CronTrigger(hour=hour, minute=minute, day_of_week=','.join(converted))
    else:
        # 默认每天
        return CronTrigger(hour=hour, minute=minute)


def add_job_for_task(task):
    """为单个任务注册调度 Job"""
    task_id = task['id']
    job_id = f"task_{task_id}"

    # 移除已存在的同名 Job
    if job_id in _job_task_map:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass

    trigger = _build_cron_trigger(task['rule_value'], task['exec_time'])

    if task['task_type'] == 'duty':
        scheduler.add_job(
            _execute_duty_task,
            trigger=trigger,
            args=[task],
            id=job_id,
            replace_existing=True,
            max_instances=1,
        )
    else:
        scheduler.add_job(
            _execute_custom_task,
            trigger=trigger,
            args=[task],
            id=job_id,
            replace_existing=True,
            max_instances=1,
        )

    _job_task_map[job_id] = task_id
    logger.info(f"已注册定时任务: job_id={job_id}, time={task['exec_time']}, rule={task['rule_value']}")


def remove_job_for_task(task_id):
    """移除某个任务的调度 Job"""
    job_id = f"task_{task_id}"
    if job_id in _job_task_map:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        del _job_task_map[job_id]
        logger.info(f"已移除定时任务: job_id={job_id}")


def reload_all_jobs():
    """从数据库加载所有启用的任务并注册到调度器"""
    # 清除所有旧 Job
    for job_id in list(_job_task_map.keys()):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
    _job_task_map.clear()

    # 从数据库加载
    conn = get_connection()
    tasks = TimingTaskModel.get_all(conn)
    conn.close()

    for task in tasks:
        if task['enabled']:
            add_job_for_task(task)

    logger.info(f"调度器已加载 {len(_job_task_map)} 个定时任务")


def get_active_job_count():
    """获取当前活跃的调度 Job 数量"""
    return len(_job_task_map)


def get_enabled_task_count_by_type(task_type=None):
    """从数据库查询已启用的任务数量"""
    conn = get_connection()
    if task_type:
        count = conn.execute(
            'SELECT COUNT(*) FROM timing_tasks WHERE enabled = 1 AND task_type = ?',
            (task_type,)
        ).fetchone()[0]
    else:
        count = conn.execute(
            'SELECT COUNT(*) FROM timing_tasks WHERE enabled = 1'
        ).fetchone()[0]
    conn.close()
    return count


def init_scheduler():
    """初始化并启动调度器（应用启动时调用）"""
    reload_all_jobs()
    if not scheduler.running:
        scheduler.start()
    logger.info("定时任务调度器已启动")


def shutdown_scheduler():
    """关闭调度器（应用退出时调用）"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("定时任务调度器已关闭")
