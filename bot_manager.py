"""
机器人配置管理模块
"""
from database import get_connection
from models import BotConfigModel


def get_all_bots():
    """获取所有机器人配置"""
    conn = get_connection()
    bots = BotConfigModel.get_all(conn)
    conn.close()
    return [dict(b) for b in bots]


def add_bot(name, webhook, secret=''):
    """添加机器人配置"""
    if not name or not name.strip():
        return {'success': False, 'error': '机器人名称不能为空'}
    if not webhook or not webhook.strip():
        return {'success': False, 'error': 'Webhook 地址不能为空'}

    conn = get_connection()
    bot_id = BotConfigModel.create(conn, name.strip(), webhook.strip(), secret.strip())
    conn.commit()
    conn.close()
    return {'success': True, 'id': bot_id, 'name': name.strip()}


def delete_bot(bot_id):
    """删除机器人配置"""
    conn = get_connection()
    BotConfigModel.delete(conn, int(bot_id))
    conn.commit()
    conn.close()
    return {'success': True}


def update_bot(bot_id, name, webhook, secret=''):
    """修改机器人配置"""
    if not name or not name.strip():
        return {'success': False, 'error': '机器人名称不能为空'}
    if not webhook or not webhook.strip():
        return {'success': False, 'error': 'Webhook 地址不能为空'}

    conn = get_connection()
    existing = BotConfigModel.get_by_id(conn, int(bot_id))
    if not existing:
        conn.close()
        return {'success': False, 'error': '机器人不存在'}

    BotConfigModel.update(conn, int(bot_id), name.strip(), webhook.strip(), secret.strip())
    conn.commit()
    conn.close()
    return {'success': True, 'id': int(bot_id), 'name': name.strip()}
