"""
值班机器人管理平台 — 应用入口
启动 Eel 桌面窗口 + 系统托盘常驻 + 可选 Flask HTTP 服务
"""
import sys
import os
import threading
import logging
import eel
import pystray
from PIL import Image, ImageDraw

# 确保项目根目录在 sys.path 中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import APP_CONFIG
from database import init_database
from scheduler_manager import init_scheduler, shutdown_scheduler
from eel_bridge import register_all_exposures  # noqa: F401
from utils import setup_logging

logger = logging.getLogger(__name__)

# 全局控制标志
_quit_app = False
_web_dir = ''


def _create_tray_image():
    """创建托盘图标（蓝色机器人头像）"""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 圆形蓝色背景
    draw.ellipse([4, 4, 60, 60], fill='#3b82f6')
    # 白色字母 B
    draw.text((20, 14), 'B', fill='white')
    return img


def _run_eel_loop():
    """循环启动 Eel：窗口关闭后自动重新打开，直到用户托盘退出"""
    global _quit_app
    while not _quit_app:
        eel.init(_web_dir)
        try:
            eel.start(
                'console.html',
                mode='chrome',
                size=(1280, 800),
                port=0,
                cmdline_args=['--disable-http-cache'],
                block=True,
            )
        except SystemExit:
            pass
        except Exception as e:
            logger.error(f"Eel 窗口异常: {e}")
        if not _quit_app:
            logger.info("窗口已关闭，定时任务继续运行（托盘常驻）")


def _quit_app_action(icon, item):
    """托盘退出：关闭调度器并退出"""
    global _quit_app
    _quit_app = True
    icon.stop()
    shutdown_scheduler()
    logger.info("应用已退出")
    os._exit(0)


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
    global _web_dir
    setup_logging()
    logger.info("值班机器人管理平台启动中...")

    init_database()
    logger.info("数据库初始化完成")

    register_all_exposures()
    logger.info("Eel 桥接函数已注册")

    init_scheduler()
    logger.info("定时任务调度器已就绪")

    _web_dir = os.path.join(BASE_DIR, 'web')

    # Flask（可选）
    if APP_CONFIG.get('enable_flask'):
        threading.Thread(target=start_flask, daemon=True).start()
        logger.info(f"Flask: http://{APP_CONFIG['flask_host']}:{APP_CONFIG['flask_port']}")

    # 首次启动 Eel 窗口（循环模式：关闭后自动重开）
    threading.Thread(target=_run_eel_loop, daemon=True).start()

    # 托盘图标
    icon = pystray.Icon(
        'dutybot',
        _create_tray_image(),
        '值班机器人',
        menu=pystray.Menu(
            pystray.MenuItem('退出应用', _quit_app_action),
        ),
    )

    icon.run()


if __name__ == '__main__':
    main()

