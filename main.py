"""
值班机器人管理平台 — 应用入口
启动 Eel 桌面窗口 + 可选 Flask HTTP 服务
"""
import sys
import os
import threading
import eel

# 确保项目根目录在 sys.path 中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import APP_CONFIG
from database import init_database
from scheduler_manager import init_scheduler, shutdown_scheduler
from eel_bridge import register_all_exposures  # noqa: F401 — 导入即注册 @eel.expose
from utils import setup_logging


def start_flask():
    """在独立线程中启动 Flask（可选）"""
    if not APP_CONFIG.get('enable_flask'):
        return

    from flask_routes import create_flask_app
    app = create_flask_app()
    app.run(
        host=APP_CONFIG.get('flask_host', '127.0.0.1'),
        port=APP_CONFIG.get('flask_port', 5000),
        debug=False,
    )


def main():
    """应用主入口"""
    # 1. 配置日志
    logger = setup_logging()
    logger.info("值班机器人管理平台启动中...")

    # 2. 初始化数据库
    init_database()
    logger.info("数据库初始化完成")

    # 3. 注册所有 Eel 暴露函数（导入 eel_bridge 即自动注册）
    register_all_exposures()
    logger.info("Eel 桥接函数已注册")

    # 4. 初始化定时任务调度器
    init_scheduler()
    logger.info("定时任务调度器已就绪")

    # 5. 启动 Flask（可选，独立线程）
    if APP_CONFIG.get('enable_flask'):
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        logger.info(f"Flask HTTP 服务已启动: http://{APP_CONFIG['flask_host']}:{APP_CONFIG['flask_port']}")

    # 6. 启动 Eel 桌面窗口
    web_dir = os.path.join(BASE_DIR, 'web')
    eel.init(web_dir)

    try:
        eel.start(
            'console.html',
            mode='chrome',              # 使用系统 Chrome/Chromium
            size=(1280, 800),
            port=0,                     # 随机端口
            cmdline_args=[
                '--disable-http-cache',
            ],
        )
    finally:
        shutdown_scheduler()
        logger.info("应用已退出")


if __name__ == '__main__':
    main()
