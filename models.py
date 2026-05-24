"""
数据访问层 — 封装所有 CRUD 操作
每个 Model 类提供静态方法，接收 conn 作为第一个参数
"""


class BotConfigModel:
    """机器人配置"""

    @staticmethod
    def get_all(conn):
        return conn.execute(
            'SELECT * FROM bot_configs ORDER BY id'
        ).fetchall()

    @staticmethod
    def get_by_id(conn, bot_id):
        return conn.execute(
            'SELECT * FROM bot_configs WHERE id = ?', (bot_id,)
        ).fetchone()

    @staticmethod
    def create(conn, name, webhook, secret=''):
        cursor = conn.execute(
            'INSERT INTO bot_configs (name, webhook, secret) VALUES (?, ?, ?)',
            (name, webhook, secret)
        )
        return cursor.lastrowid

    @staticmethod
    def delete(conn, bot_id):
        conn.execute('DELETE FROM bot_configs WHERE id = ?', (bot_id,))

    @staticmethod
    def update(conn, bot_id, name, webhook, secret=''):
        conn.execute(
            'UPDATE bot_configs SET name = ?, webhook = ?, secret = ? WHERE id = ?',
            (name, webhook, secret, bot_id)
        )


class DutyTableModel:
    """值班信息表"""

    @staticmethod
    def get_all(conn):
        return conn.execute(
            'SELECT * FROM duty_tables ORDER BY created_at DESC'
        ).fetchall()

    @staticmethod
    def get_by_id(conn, table_id):
        return conn.execute(
            'SELECT * FROM duty_tables WHERE id = ?', (table_id,)
        ).fetchone()

    @staticmethod
    def create(conn, name, file_name, record_count):
        cursor = conn.execute(
            'INSERT INTO duty_tables (name, file_name, record_count) VALUES (?, ?, ?)',
            (name, file_name, record_count)
        )
        return cursor.lastrowid

    @staticmethod
    def delete(conn, table_id):
        conn.execute('DELETE FROM duty_tables WHERE id = ?', (table_id,))

    @staticmethod
    def get_records(conn, table_id):
        return conn.execute(
            'SELECT * FROM duty_records WHERE table_id = ? ORDER BY duty_date',
            (table_id,)
        ).fetchall()

    @staticmethod
    def insert_records(conn, table_id, records):
        conn.executemany(
            'INSERT INTO duty_records (table_id, duty_date, weekday, person) VALUES (?, ?, ?, ?)',
            [(table_id, r['date'], r['weekday'], r['person']) for r in records]
        )


class TimingTaskModel:
    """定时任务配置"""

    @staticmethod
    def get_all(conn):
        return conn.execute(
            'SELECT * FROM timing_tasks ORDER BY id'
        ).fetchall()

    @staticmethod
    def get_by_type(conn, task_type):
        return conn.execute(
            'SELECT * FROM timing_tasks WHERE task_type = ? ORDER BY id',
            (task_type,)
        ).fetchall()

    @staticmethod
    def get_by_id(conn, task_id):
        return conn.execute(
            'SELECT * FROM timing_tasks WHERE id = ?', (task_id,)
        ).fetchone()

    @staticmethod
    def create(conn, data):
        cursor = conn.execute('''
            INSERT INTO timing_tasks
                (task_type, exec_time, rule, rule_value, enabled,
                 message_text, bot_ids, at_all, table_id)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
        ''', (
            data['task_type'],
            data['exec_time'],
            data['rule'],
            data['rule_value'],
            data.get('message_text', ''),
            data.get('bot_ids', ''),
            data.get('at_all', 0),
            data.get('table_id'),
        ))
        return cursor.lastrowid

    @staticmethod
    def update_enabled(conn, task_id, enabled):
        conn.execute(
            'UPDATE timing_tasks SET enabled = ? WHERE id = ?',
            (1 if enabled else 0, task_id)
        )

    @staticmethod
    def delete(conn, task_id):
        conn.execute('DELETE FROM timing_tasks WHERE id = ?', (task_id,))


class SendLogModel:
    """发送日志"""

    @staticmethod
    def get_all(conn, log_type=None, limit=200):
        if log_type:
            return conn.execute(
                'SELECT * FROM send_logs WHERE log_type = ? ORDER BY sent_at DESC LIMIT ?',
                (log_type, limit)
            ).fetchall()
        return conn.execute(
            'SELECT * FROM send_logs ORDER BY sent_at DESC LIMIT ?',
            (limit,)
        ).fetchall()

    @staticmethod
    def create(conn, data):
        conn.execute('''
            INSERT INTO send_logs
                (log_type, bot_names, message_summary, table_name, at_all, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['log_type'],
            data['bot_names'],
            data.get('message_summary', ''),
            data.get('table_name', ''),
            data.get('at_all', 0),
            data['status'],
            data.get('error_message', ''),
        ))

    @staticmethod
    def clear(conn, log_type=None):
        if log_type:
            conn.execute('DELETE FROM send_logs WHERE log_type = ?', (log_type,))
        else:
            conn.execute('DELETE FROM send_logs')
