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
)
from message_sender import send_duty_notification, send_custom_message
from models import TimingTaskModel, SendLogModel
from database import get_connection
from scheduler_manager import add_job_for_task, remove_job_for_task, get_enabled_task_count_by_type
from utils import read_recent_logs, read_full_logs, get_log_file_path


def _fmt_created_at(created_at):
    """将 SQLite UTC 时间转为本地时间"""
    from datetime import datetime, timezone
    if not created_at:
        return ''
    try:
        utc_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone()
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return created_at


# ==================== 初始化数据 ====================

@eel.expose
def get_all_data():
    """前端初始化时获取全部数据"""
    bots = [dict(b) for b in get_all_bots()]
    for b in bots:
        b['created_at'] = _fmt_created_at(b.get('created_at'))
    tables = [dict(t) for t in get_all_tables()]
    for t in tables:
        t['created_at'] = _fmt_created_at(t.get('created_at'))
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
def send_duty_notification_eel(bot_ids, table_id, at_all=False, custom_text=''):
    """发送值班通知，可选拼接自定义文本"""
    return send_duty_notification(bot_ids, table_id, at_all, custom_text)


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
    conn = get_connection()
    logs = SendLogModel.get_all(conn, log_type)
    conn.close()

    return [
        {
            'id': l['id'],
            'time': _fmt_created_at(l['sent_at']),
            'sent_at': _fmt_created_at(l['sent_at']),
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




# ==================== 数据处理工作流 ====================

import json as _json
import os as _os
import base64 as _base64
import uuid as _uuid
import pandas as _pd
from node_registry import NODE_REGISTRY
from workflow_engine import execute_workflow

# 使用 config 中配置的持久化上传目录（~/.dutybot/uploads），
# 而非 __file__ 相对路径（PyInstaller 打包后 __file__ 指向临时目录，退出即清空）
from config import APP_CONFIG
_UPLOADS_DIR = APP_CONFIG['upload_dir']
_os.makedirs(_UPLOADS_DIR, exist_ok=True)

# 兼容迁移：将旧上传目录（项目根 uploads/）中的文件复制到持久化目录
_OLD_UPLOADS_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'uploads')
if _os.path.isdir(_OLD_UPLOADS_DIR) and _os.path.abspath(_OLD_UPLOADS_DIR) != _os.path.abspath(_UPLOADS_DIR):
    try:
        for _fn in _os.listdir(_OLD_UPLOADS_DIR):
            _old_path = _os.path.join(_OLD_UPLOADS_DIR, _fn)
            _new_path = _os.path.join(_UPLOADS_DIR, _fn)
            if _os.path.isfile(_old_path) and not _os.path.exists(_new_path):
                import shutil as _shutil
                _shutil.copy2(_old_path, _new_path)
    except Exception:
        pass  # 静默迁移，失败不影响启动

# 内存中暂存当前上传的 DataFrame
_current_df = None
_current_file_name = None


def _auto_convert_datetime_cols(df):
    """自动将 DataFrame 中疑似日期的文本列转为 datetime"""
    from node_registry import _parse_datetime_col
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        # 只处理文本类列（object/string/str）
        if not any(t in dtype_str for t in ('object', 'string', 'str')):
            continue
        if len(df[col].dropna()) > 0:
            sample = df[col].dropna().astype(str).head(20)
            date_count = sample.str.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}').sum()
            if date_count >= len(sample) * 0.5:
                df[col] = _parse_datetime_col(df[col])


@eel.expose
def upload_excel(file_name, file_b64, header_row=None, skip_rows=None):
    """上传 Excel 文件，返回列名列表（重名自动加序号）"""
    global _current_df, _current_file_name
    try:
        file_bytes = _base64.b64decode(file_b64)
        # 重名处理：追加序号
        base, ext = _os.path.splitext(file_name)
        final_name = file_name
        counter = 1
        while _os.path.exists(_os.path.join(_UPLOADS_DIR, final_name)):
            final_name = f"{base}({counter}){ext}"
            counter += 1
        file_path = _os.path.join(_UPLOADS_DIR, final_name)
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        header = int(header_row) if header_row is not None and int(header_row) >= 0 else 0
        skip = int(skip_rows) if skip_rows is not None and int(skip_rows) >= 0 else 0
        _current_df = _pd.read_excel(file_path, header=header, skiprows=skip)
        _current_file_name = final_name
        columns = _current_df.columns.tolist()
        # 将整数列名转为字符串
        columns = [str(c) for c in columns]
        _current_df.columns = columns
        # 自动检测日期列并转换
        _auto_convert_datetime_cols(_current_df)
        row_count = len(_current_df)
        # 保存元数据
        meta_path = file_path + '.meta.json'
        with open(meta_path, 'w') as mf:
            _json.dump({'row_count': row_count, 'header_row': header, 'skip_rows': skip}, mf)
        return {'success': True, 'columns': columns, 'row_count': row_count, 'file_name': final_name}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def execute_data_workflow(nodes):
    """执行数据处理工作流，返回结果预览"""
    global _current_df
    if _current_df is None:
        return {'success': False, 'error': '请先上传 Excel 文件'}
    try:
        result = execute_workflow(_current_df, nodes)
        _current_df = result['result_df']
        # 预览前 50 行
        preview = result['result_df'].head(50)
        for col in preview.columns:
            if _pd.api.types.is_datetime64_any_dtype(preview[col]):
                preview[col] = preview[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        preview_clean = preview.astype(object).where(preview.notna(), None)
        return {
            'success': True,
            'columns': preview_clean.columns.tolist(),
            'data': preview_clean.values.tolist(),
            'row_count': len(result['result_df']),
            'errors': result['errors'],
            'executed_count': result['executed_count'],
            'total_count': result['total_count'],
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def get_workflow_node_types():
    """获取所有可用的节点类型及参数定义"""
    types = []
    for nt, info in NODE_REGISTRY.items():
        schema = info.get('params_schema', {})
        params = []
        for name, cfg in schema.items():
            params.append({
                'name': name,
                'label': cfg.get('label', name),
                'type': cfg.get('type', 'str'),
                'required': cfg.get('required', False),
                'options': cfg.get('options', []),
            })
        types.append({'type': nt, 'params': params})
    return types


@eel.expose
def save_workflow(name, nodes):
    """保存工作流"""
    if not name or not name.strip():
        return {'success': False, 'error': '工作流名称不能为空'}
    conn = get_connection()
    wf_id = str(_uuid.uuid4())
    conn.execute(
        'INSERT INTO workflows (id, name, nodes) VALUES (?, ?, ?)',
        (wf_id, name.strip(), _json.dumps(nodes, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    return {'success': True, 'id': wf_id, 'name': name.strip()}


@eel.expose
def load_workflows():
    """获取所有已保存工作流"""
    conn = get_connection()
    rows = conn.execute('SELECT * FROM workflows ORDER BY created_at DESC').fetchall()
    conn.close()
    return [{'id': r['id'], 'name': r['name'], 'nodes': _json.loads(r['nodes']), 'created_at': _fmt_created_at(r['created_at'])} for r in rows]


@eel.expose
def delete_workflow(wf_id):
    """删除工作流"""
    conn = get_connection()
    conn.execute('DELETE FROM workflows WHERE id = ?', (str(wf_id),))
    conn.commit()
    conn.close()
    return {'success': True}


@eel.expose
def export_result_markdown():
    """将当前结果转为 Markdown 表格文本"""
    global _current_df
    if _current_df is None:
        return {'success': False, 'error': '无数据可导出'}
    try:
        df = _current_df.head(50)
        lines = []
        # 表头
        headers = '| ' + ' | '.join(str(c) for c in df.columns) + ' |'
        lines.append(headers)
        # 分隔线
        sep = '| ' + ' | '.join('---' for _ in df.columns) + ' |'
        lines.append(sep)
        # 数据行
        for _, row in df.iterrows():
            cells = []
            for v in row:
                if v is None or (isinstance(v, float) and _pd.isna(v)):
                    cells.append('')
                else:
                    cells.append(str(v).replace('|', '\\|'))
            lines.append('| ' + ' | '.join(cells) + ' |')
        return {'success': True, 'markdown': '\n'.join(lines), 'row_count': len(_current_df)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def list_uploaded_files():
    """列出 uploads 目录下所有 xlsx 文件（按修改时间排序，最新在前）"""
    files = []
    if _os.path.exists(_UPLOADS_DIR):
        items = []
        for f in _os.listdir(_UPLOADS_DIR):
            if f.endswith(('.xlsx', '.xls')) and not f.startswith('~'):
                path = _os.path.join(_UPLOADS_DIR, f)
                mtime = _os.path.getmtime(path)
                items.append((f, path, mtime))
        items.sort(key=lambda x: x[2], reverse=True)
        from datetime import datetime
        for f, path, mtime in items:
            mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            row_count = 0
            meta_path = path + '.meta.json'
            if _os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as mf:
                        meta = _json.load(mf)
                        row_count = meta.get('row_count', 0)
                except Exception:
                    pass
            files.append({'name': f, 'path': path, 'mtime': mtime_str, 'row_count': row_count})
    return files


@eel.expose
def select_uploaded_file(file_name, header_row=None, skip_rows=None):
    """选择已上传的文件，加载为当前 DataFrame"""
    global _current_df, _current_file_name
    path = _os.path.join(_UPLOADS_DIR, file_name)
    if not _os.path.exists(path):
        return {'success': False, 'error': f'文件不存在: {file_name}'}
    try:
        # 读取已有元数据获取默认值
        meta_path = path + '.meta.json'
        if header_row is None and _os.path.exists(meta_path):
            try:
                with open(meta_path, 'r') as mf:
                    meta = _json.load(mf)
                    header_row = meta.get('header_row', 0)
                    skip_rows = meta.get('skip_rows', 0)
            except Exception:
                pass
        header = int(header_row) if header_row is not None and int(header_row) >= 0 else 0
        skip = int(skip_rows) if skip_rows is not None and int(skip_rows) >= 0 else 0
        _current_df = _pd.read_excel(path, header=header, skiprows=skip)
        _current_file_name = file_name
        columns = _current_df.columns.tolist()
        columns = [str(c) for c in columns]
        _current_df.columns = columns
        _auto_convert_datetime_cols(_current_df)
        row_count = len(_current_df)
        with open(meta_path, 'w') as mf:
            _json.dump({'row_count': row_count, 'header_row': header, 'skip_rows': skip}, mf)
        return {'success': True, 'columns': columns, 'row_count': row_count, 'file_name': file_name}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def reparse_uploaded_file(file_name, header_row=0, skip_rows=0):
    """重新解析已上传文件（更新表头/跳过行设置）"""
    return select_uploaded_file(file_name, int(header_row), int(skip_rows))


@eel.expose
def delete_uploaded_file(file_name):
    """删除已上传的 Excel 文件及其元数据"""
    path = _os.path.join(_UPLOADS_DIR, file_name)
    meta_path = path + '.meta.json'
    deleted = False
    if _os.path.exists(path):
        _os.remove(path)
        deleted = True
    if _os.path.exists(meta_path):
        _os.remove(meta_path)
    if deleted:
        return {'success': True}
    return {'success': False, 'error': f'文件不存在: {file_name}'}


@eel.expose
def get_current_preview(page=1, page_size=20):
    """获取当前处理结果预览（分页）"""
    global _current_df
    if _current_df is None:
        return {'success': False, 'error': '无数据'}
    total = len(_current_df)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    preview = _current_df.iloc[start:end]
    # 将 datetime 列转为字符串，避免 JSON 序列化失败
    for col in preview.columns:
        if _pd.api.types.is_datetime64_any_dtype(preview[col]):
            preview[col] = preview[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    preview_clean = preview.astype(object).where(preview.notna(), None)
    return {
        'success': True,
        'columns': preview_clean.columns.tolist(),
        'data': preview_clean.values.tolist(),
        'row_count': total,
        'page': page,
        'total_pages': total_pages,
        'page_size': page_size,
    }


# ---- 上次选择的文件记忆 ----
_LAST_FILE_PATH = _os.path.join(_UPLOADS_DIR, '.last_data_file.json')


@eel.expose
def save_last_data_file(file_name):
    """记住用户最后选择的数据文件，下次启动时自动恢复"""
    try:
        with open(_LAST_FILE_PATH, 'w') as f:
            _json.dump({'file_name': file_name or ''}, f)
    except Exception:
        pass


@eel.expose
def get_last_data_file():
    """获取上次选择的数据文件名称"""
    try:
        if _os.path.exists(_LAST_FILE_PATH):
            with open(_LAST_FILE_PATH, 'r') as f:
                data = _json.load(f)
                name = data.get('file_name', '')
                if name and _os.path.exists(_os.path.join(_UPLOADS_DIR, name)):
                    return {'success': True, 'file_name': name}
    except Exception:
        pass
    return {'success': False, 'file_name': ''}


def register_all_exposures():
    """确保所有 @eel.expose 函数被注册（导入即注册，此函数为显式调用入口）"""


# ==================== 消息流编排 ====================

@eel.expose
def save_message_flow(name, nodes):
    """保存消息流"""
    if not name or not name.strip():
        return {'success': False, 'error': '消息流名称不能为空'}
    conn = get_connection()
    wf_id = str(_uuid.uuid4())
    conn.execute(
        'INSERT INTO message_flows (id, name, nodes) VALUES (?, ?, ?)',
        (wf_id, name.strip(), _json.dumps(nodes, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    return {'success': True, 'id': wf_id, 'name': name.strip()}


@eel.expose
def load_message_flows():
    """获取所有已保存消息流"""
    conn = get_connection()
    rows = conn.execute('SELECT * FROM message_flows ORDER BY created_at DESC').fetchall()
    conn.close()
    return [{'id': r['id'], 'name': r['name'], 'nodes': _json.loads(r['nodes']), 'created_at': _fmt_created_at(r['created_at'])} for r in rows]


@eel.expose
def delete_message_flow(flow_id):
    """删除消息流"""
    conn = get_connection()
    conn.execute('DELETE FROM message_flows WHERE id = ?', (str(flow_id),))
    conn.commit()
    conn.close()
    return {'success': True}


@eel.expose
def execute_message_flow(nodes):
    """
    执行消息流编排，串行执行节点，拼接文本后发送
    节点类型：
      - msg_text:     {type: "msg_text", params: {text: "..."}}
      - msg_data_process: {type: "msg_data_process", params: {file: "filename.xlsx", workflow_id: "uuid"}}
      - msg_send:     {type: "msg_send", params: {bot_ids: [1,2], at_all: bool}}  — 终端节点
    返回: {success, message, errors[], sent_result}
    """
    global _current_df, _current_file_name
    accumulated_text = ''
    errors = []
    sent_result = None
    saved_df = _current_df
    saved_file = _current_file_name

    try:
        for node in nodes:
            nt = node.get('type', '')
            params = node.get('params', {})

            if nt == 'msg_text':
                text = (params.get('text') or '').strip()
                if text:
                    if accumulated_text:
                        accumulated_text += '\n\n'
                    accumulated_text += text

            elif nt == 'msg_data_process':
                file_name = params.get('file', '').strip()
                workflow_id = params.get('workflow_id', '').strip()
                if not file_name:
                    errors.append({'node_type': nt, 'error': '未选择文件'})
                    continue
                if not workflow_id:
                    errors.append({'node_type': nt, 'error': '未选择数据处理工作流'})
                    continue
                # 加载工作流
                conn = get_connection()
                wf_row = conn.execute('SELECT * FROM workflows WHERE id = ?', (workflow_id,)).fetchone()
                conn.close()
                if not wf_row:
                    errors.append({'node_type': nt, 'error': f'工作流不存在: {workflow_id}'})
                    continue
                wf_nodes = _json.loads(wf_row['nodes'])
                # 加载文件
                path = _os.path.join(_UPLOADS_DIR, file_name)
                if not _os.path.exists(path):
                    errors.append({'node_type': nt, 'error': f'文件不存在: {file_name}'})
                    continue
                try:
                    df = _pd.read_excel(path)
                    result = execute_workflow(df, wf_nodes)
                    df_result = result['result_df']
                    # 导出为 Markdown
                    md_lines = []
                    headers = '| ' + ' | '.join(str(c) for c in df_result.columns) + ' |'
                    md_lines.append(headers)
                    md_lines.append('| ' + ' | '.join('---' for _ in df_result.columns) + ' |')
                    for _, row in df_result.head(50).iterrows():
                        cells = [str(v).replace('|', '\\|') if v is not None and not (_pd.isna(v) if isinstance(v, float) else False) else '' for v in row]
                        md_lines.append('| ' + ' | '.join(cells) + ' |')
                    table_md = '\n'.join(md_lines)
                    if accumulated_text:
                        accumulated_text += '\n\n'
                    accumulated_text += table_md
                    if result.get('errors'):
                        for e in result['errors']:
                            errors.append({'node_type': nt, 'error': f"{e.get('node_type','')}: {e.get('error','')}"})
                except Exception as e:
                    errors.append({'node_type': nt, 'error': str(e)})

            elif nt == 'msg_send':
                bot_ids = params.get('bot_ids', [])
                at_all = params.get('at_all', False)
                if not bot_ids:
                    errors.append({'node_type': nt, 'error': '未选择机器人'})
                    continue
                if not accumulated_text.strip():
                    errors.append({'node_type': nt, 'error': '消息内容为空，请在前置步骤中添加文本或数据处理结果'})
                    continue
                try:
                    sent_result = send_custom_message(bot_ids, accumulated_text, at_all)
                except Exception as e:
                    errors.append({'node_type': nt, 'error': f'发送失败: {e}'})
                break  # 发送后终止

    finally:
        # 恢复原始 DataFrame
        _current_df = saved_df
        _current_file_name = saved_file

    return {
        'success': len(errors) == 0,
        'message': accumulated_text,
        'errors': errors,
        'sent_result': sent_result,
    }
