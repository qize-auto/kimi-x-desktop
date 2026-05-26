"""
Kimi-X Desktop — 统一日志系统
================================
- 按日期分文件: logs/kimi-x-YYYY-MM-DD.log
- 同时输出到文件(DEBUG)和控制台(INFO)
- 异常自动记录完整 traceback
- 所有模块通过 get_logger(name) 获取命名 logger
"""
import logging
import sys
import traceback
from pathlib import Path
from datetime import datetime
from functools import wraps


class AppLogger:
    """应用级日志管理器"""

    _instance = None

    def __new__(cls, log_dir: Path | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: Path | None = None):
        if self._initialized:
            return
        self._initialized = True

        if log_dir is None:
            log_dir = Path(__file__).parent / "logs"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 按日期命名日志文件
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"kimi-x-{date_str}.log"

        # 根 logger
        self.logger = logging.getLogger("kimi_x")
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if self.logger.handlers:
            return

        # 文件 handler — 记录 DEBUG 及以上
        fh = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)

        # 控制台 handler — 只记录 INFO 及以上
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)

        # 统一格式
        fmt = "[%(asctime)s] [%(levelname)-7s] [%(name)-20s] %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt=datefmt)
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        self.logger.info("=" * 60)
        self.logger.info("Kimi-X Desktop 日志系统启动")
        self.logger.info(f"日志文件: {log_file}")
        self.logger.info("=" * 60)

    def get_logger(self, name: str) -> logging.Logger:
        """获取命名 logger"""
        return logging.getLogger(f"kimi_x.{name}")


# 全局单例
app_logger = AppLogger()


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger"""
    return app_logger.get_logger(name)


def log_exception(logger: logging.Logger, msg: str = ""):
    """记录异常及完整 traceback"""
    exc_type, exc_value, exc_tb = sys.exc_info()
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.error(f"{msg}\n{tb_str}" if msg else tb_str)


def log_call(logger: logging.Logger):
    """装饰器：记录函数调用和异常"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"→ {func.__qualname__}()")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"← {func.__qualname__}() OK")
                return result
            except Exception as e:
                log_exception(logger, f"{func.__qualname__}() failed: {e}")
                raise
        return wrapper
    return decorator
