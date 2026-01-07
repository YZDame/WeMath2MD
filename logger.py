"""
日志配置模块
提供统一的日志配置，支持控制台和文件输出
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logger(
    name: str = "wemath2md",
    level: str = "INFO",
    log_file: str | Path | None = None,
    log_dir: str | Path = "logs",
    format_string: str | None = None,
) -> logging.Logger:
    """
    配置并返回一个 logger 实例

    Args:
        name: logger 名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件名（如果指定，则写入文件）
        log_dir: 日志文件目录（当 log_file 指定时有效）
        format_string: 自定义日志格式

    Returns:
        配置好的 logger 实例
    """
    # 获取或创建 logger
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 设置日志级别
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 默认格式
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler（如果指定）
    if log_file:
        log_path = Path(log_dir) / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "wemath2md") -> logging.Logger:
    """
    获取已配置的 logger 实例

    Args:
        name: logger 名称

    Returns:
        logger 实例
    """
    return logging.getLogger(name)


# 默认 logger 实例
default_logger = setup_logger()


# 便捷函数
def debug(msg: str, *args, **kwargs) -> None:
    """记录 DEBUG 级别日志"""
    default_logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    """记录 INFO 级别日志"""
    default_logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    """记录 WARNING 级别日志"""
    default_logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    """记录 ERROR 级别日志"""
    default_logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    """记录 CRITICAL 级别日志"""
    default_logger.critical(msg, *args, **kwargs)
