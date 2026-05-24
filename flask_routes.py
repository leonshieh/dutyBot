"""
Flask HTTP 路由 — 可选模块
提供 REST API，可用于 Webhook 回调、健康检查、外部集成等
默认不启动，通过 config.APP_CONFIG['enable_flask'] 控制
"""
from flask import Flask, request, jsonify
from bot_manager import get_all_bots, add_bot, delete_bot
from duty_table_manager import get_all_tables, get_table_records
from message_sender import send_duty_notification, send_custom_message


def create_flask_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__)

    # ---- 健康检查 ----
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'service': 'dutybot'})

    # ---- 机器人配置 API ----
    @app.route('/api/bots', methods=['GET'])
    def api_get_bots():
        return jsonify(get_all_bots())

    @app.route('/api/bots', methods=['POST'])
    def api_add_bot():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        result = add_bot(
            data.get('name', ''),
            data.get('webhook', ''),
            data.get('secret', ''),
        )
        code = 201 if result.get('success') else 400
        return jsonify(result), code

    @app.route('/api/bots/<int:bot_id>', methods=['DELETE'])
    def api_delete_bot(bot_id):
        return jsonify(delete_bot(bot_id))

    # ---- 值班表 API ----
    @app.route('/api/duty-tables', methods=['GET'])
    def api_get_tables():
        return jsonify(get_all_tables())

    @app.route('/api/duty-tables/<int:table_id>/records', methods=['GET'])
    def api_get_records(table_id):
        return jsonify(get_table_records(table_id))

    # ---- 发送消息 API ----
    @app.route('/api/send/duty', methods=['POST'])
    def api_send_duty():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        result = send_duty_notification(
            data.get('bot_ids', []),
            data.get('table_id'),
            data.get('at_all', False),
        )
        return jsonify(result)

    @app.route('/api/send/custom', methods=['POST'])
    def api_send_custom():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        result = send_custom_message(
            data.get('bot_ids', []),
            data.get('message', ''),
            data.get('at_all', False),
        )
        return jsonify(result)

    return app
