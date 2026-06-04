"""
值班机器人管理平台 — 应用入口
启动 Eel 桌面窗口 + 系统托盘常驻 + 可选 Flask HTTP 服务
"""
import sys
import os
import time
import atexit
import tempfile
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

# ---- 进程级单实例锁（防止 exe 被多次启动） ----
_lock_file = None


def _acquire_single_instance_lock():
    """获取进程级单实例锁，通过 PID 文件实现。
    返回 True 表示成功获取锁，False 表示已有实例在运行。"""
    global _lock_file
    lock_dir = os.path.join(tempfile.gettempdir(), 'dutybot')
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, 'dutybot.lock')

    if os.path.exists(lock_path):
        try:
            with open(lock_path, 'r') as f:
                old_pid = int(f.read().strip())
            # 检查该 PID 的进程是否还活着
            os.kill(old_pid, 0)
            logger.warning(f"已有实例正在运行 (PID={old_pid})，拒绝重复启动")
            return False
        except (ValueError, OSError, ProcessLookupError):
            # 锁文件中的 PID 已失效，可以覆盖
            logger.info("旧的锁文件已失效，覆盖并启动新实例")

    with open(lock_path, 'w') as f:
        f.write(str(os.getpid()))
    _lock_file = lock_path

    # 注册退出时清理锁文件
    def _cleanup_lock():
        try:
            if _lock_file and os.path.exists(_lock_file):
                os.remove(_lock_file)
        except Exception:
            pass

    atexit.register(_cleanup_lock)
    return True


# ---- 全局控制标志 ----
_quit_app = False
_web_dir = ''
_eel_thread = None
_eel_thread_lock = threading.Lock()
_last_window_close_time = 0.0  # 防抖：记录上次窗口关闭的时间戳


def _run_eel():
    """启动 Eel 窗口（单次，关闭后不自动重开）"""
    global _last_window_close_time
    print(f"[dutyBot] Eel 窗口启动中... (PID={os.getpid()})")
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
        print(f"[dutyBot] Eel 窗口异常: {e}")
        logger.error(f"Eel 窗口异常: {e}")
    finally:
        _last_window_close_time = time.time()
        print(f"[dutyBot] Eel 窗口已关闭")
    if not _quit_app:
        logger.info("窗口已关闭，定时任务继续运行（托盘常驻）")


def _show_window(icon=None, item=None):
    """托盘菜单：重新显示窗口（防止重复打开）"""
    global _eel_thread
    with _eel_thread_lock:
        if _eel_thread and _eel_thread.is_alive():
            print(f"[dutyBot] 窗口已在运行，忽略重复的打开请求")
            logger.info("窗口已在运行，忽略重复的打开请求")
            return
        # 防抖：窗口刚关闭 2 秒内不允许重新打开（防止双击事件重复触发）
        if time.time() - _last_window_close_time < 2.0:
            print(f"[dutyBot] 窗口刚关闭 ({time.time() - _last_window_close_time:.1f}s)，忽略快速重复的打开请求")
            logger.info("窗口刚关闭，忽略快速重复的打开请求")
            return
        print(f"[dutyBot] 正在打开窗口...")
        _eel_thread = threading.Thread(target=_run_eel, daemon=True)
        _eel_thread.start()


def _quit_app_action(icon, item):
    """托盘退出：关闭调度器并退出"""
    global _quit_app
    _quit_app = True
    icon.stop()
    shutdown_scheduler()
    # 清理单实例锁文件
    try:
        if _lock_file and os.path.exists(_lock_file):
            os.remove(_lock_file)
    except Exception:
        pass
    logger.info("应用已退出")
    os._exit(0)


def main():
    """应用主入口"""
    global _web_dir

    # 进程级单实例锁：防止 exe 被多次启动
    if not _acquire_single_instance_lock():
        logger.error("应用已在运行中（单实例锁检测到重复启动），退出")
        sys.exit(1)

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
    with _eel_thread_lock:
        _eel_thread = threading.Thread(target=_run_eel, daemon=True)
        _eel_thread.start()

    # 托盘图标
    icon = pystray.Icon(
        'dutybot',
        Image.open(os.path.join(_web_dir, 'robot.png')),
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

