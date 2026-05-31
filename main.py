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
from PIL import Image

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


def _run_eel():
    """启动 Eel 窗口（单次，关闭后不自动重开）"""
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


def _show_window(icon=None, item=None):
    """托盘菜单：重新显示窗口"""
    threading.Thread(target=_run_eel, daemon=True).start()


def _quit_app_action(icon, item):
    """托盘退出：关闭调度器并退出"""
    global _quit_app
    _quit_app = True
    icon.stop()
    shutdown_scheduler()
    logger.info("应用已退出")
    os._exit(0)


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

    # 首次启动 Eel 窗口
    threading.Thread(target=_run_eel, daemon=True).start()

    # 托盘图标
    icon = pystray.Icon(
        'dutybot',
        Image.open(os.path.join(_web_dir, 'message.png')),
        '值班机器人',
        menu=pystray.Menu(
            pystray.MenuItem('显示窗口', _show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('退出应用', _quit_app_action),
        ),
    )

    icon.run()


if __name__ == '__main__':
    main()

