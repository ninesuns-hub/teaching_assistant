import logging
import sys
from agent_core.config.settings import settings

def setup_logger() -> logging.Logger:
    # 配置根日志器，确保所有模块的日志都能被捕获
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # 清除现有的 handlers 防止重复
    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = logging.Formatter(settings.LOG_FORMAT)

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出
    file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger
