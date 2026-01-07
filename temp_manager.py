# temp_manager.py
"""
临时目录管理模块
提供临时目录的创建、清理和生命周期管理
"""

import os
import time
import shutil
import atexit
import contextlib
from pathlib import Path
from typing import Generator
from logger import get_logger

logger = get_logger("wemath2md.temp")

# 临时目录前缀
TEMP_PREFIX = "_temp_"

# 存储所有创建的临时目录
_temp_dirs: set[Path] = set()


def get_temp_dir_path(identifier: str = "") -> Path:
    """
    生成临时目录路径

    Args:
        identifier: 可选的标识符，用于区分不同的临时目录

    Returns:
        临时目录路径
    """
    timestamp = int(time.time())
    if identifier:
        return Path(f"{TEMP_PREFIX}{identifier}_{timestamp}")
    return Path(f"{TEMP_PREFIX}{timestamp}")


def register_temp_dir(temp_dir: Path) -> None:
    """
    注册临时目录，用于程序退出时清理

    Args:
        temp_dir: 临时目录路径
    """
    _temp_dirs.add(temp_dir)
    logger.debug(f"注册临时目录: {temp_dir}")


def unregister_temp_dir(temp_dir: Path) -> None:
    """
    注销临时目录，已清理的目录不再需要跟踪

    Args:
        temp_dir: 临时目录路径
    """
    _temp_dirs.discard(temp_dir)
    logger.debug(f"注销临时目录: {temp_dir}")


def cleanup_temp_dir(temp_dir: Path) -> None:
    """
    清理指定的临时目录

    Args:
        temp_dir: 要清理的临时目录路径
    """
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"已清理临时目录: {temp_dir}")
    except Exception as e:
        logger.warning(f"清理临时目录失败 {temp_dir}: {e}")


def cleanup_all_temp_dirs() -> None:
    """
    清理所有已注册的临时目录
    在程序退出时由 atexit 调用
    """
    if not _temp_dirs:
        return

    logger.info(f"程序退出，清理 {len(_temp_dirs)} 个临时目录...")
    for temp_dir in list(_temp_dirs):
        cleanup_temp_dir(temp_dir)
        unregister_temp_dir(temp_dir)


def cleanup_old_temp_dirs(base_dir: Path, max_age_hours: int = 24) -> int:
    """
    清理旧的临时目录（启动时调用）

    Args:
        base_dir: 基础目录
        max_age_hours: 最大保留时间（小时），超过此时间的临时目录将被清理

    Returns:
        清理的目录数量
    """
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    cleaned_count = 0

    try:
        for item in base_dir.iterdir():
            if item.name.startswith(TEMP_PREFIX) and item.is_dir():
                # 检查目录的修改时间
                dir_age = current_time - item.stat().st_mtime
                if dir_age > max_age_seconds:
                    try:
                        shutil.rmtree(item)
                        logger.info(f"清理旧临时目录: {item.name} ({dir_age / 3600:.1f} 小时前)")
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"清理旧临时目录失败 {item.name}: {e}")
    except Exception as e:
        logger.error(f"扫描旧临时目录失败: {e}")

    return cleaned_count


@contextlib.contextmanager
def temporary_directory(
    identifier: str = "",
    base_dir: Path | None = None,
    cleanup_on_exit: bool = True
) -> Generator[Path, None, None]:
    """
    临时目录上下文管理器

    Args:
        identifier: 可选的标识符
        base_dir: 基础目录（默认为当前工作目录）
        cleanup_on_exit: 退出时是否自动清理

    Yields:
        临时目录路径

    Example:
        with temporary_directory("test") as temp_dir:
            # 使用 temp_dir
            (temp_dir / "file.txt").write_text("hello")
        # 退出时自动清理
    """
    base = base_dir or Path.cwd()
    temp_dir = base / get_temp_dir_path(identifier)

    try:
        # 创建目录
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"创建临时目录: {temp_dir}")

        if cleanup_on_exit:
            register_temp_dir(temp_dir)

        yield temp_dir

    finally:
        if cleanup_on_exit:
            cleanup_temp_dir(temp_dir)
            unregister_temp_dir(temp_dir)


# 注册程序退出时的清理函数
atexit.register(cleanup_all_temp_dirs)


def initialize_cleanup(base_dir: Path | None = None, max_age_hours: int = 24) -> None:
    """
    初始化临时目录管理（程序启动时调用）

    Args:
        base_dir: 基础目录（默认为当前工作目录）
        max_age_hours: 旧临时目录的最大保留时间（小时）
    """
    base = base_dir or Path.cwd()
    cleaned = cleanup_old_temp_dirs(base, max_age_hours)
    if cleaned > 0:
        logger.info(f"启动时清理了 {cleaned} 个旧临时目录")
