"""日志工具模块"""

import logging
import sys
from pathlib import Path

from rich.logging import RichHandler


def setup_logger(
    name: str = "animal_id",
    level: str = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    """初始化日志系统"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 控制台输出 (Rich)
    console_handler = RichHandler(rich_tracebacks=True, show_time=False)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
        )
        logger.addHandler(file_handler)

    return logger
