# tests/test_temp_manager.py
"""
临时目录管理模块单元测试
测试 temp_manager.py 中的临时目录创建、清理和生命周期管理功能
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 导入被测试的模块
import temp_manager


class TestTempDirPathGeneration:
    """临时目录路径生成测试"""

    def test_get_temp_dir_path_default(self):
        """测试默认临时目录路径生成"""
        temp_path = temp_manager.get_temp_dir_path()
        assert temp_path.name.startswith(temp_manager.TEMP_PREFIX)
        # 名称应该是 _temp_<timestamp>
        parts = temp_path.name.split("_")
        # split("_") 会是 ['', 'temp', '<timestamp>']
        assert len(parts) == 3
        assert parts[0] == ""
        assert parts[1] == "temp"
        assert parts[2].isdigit()

    def test_get_temp_dir_path_with_identifier(self):
        """测试带标识符的临时目录路径生成"""
        temp_path = temp_manager.get_temp_dir_path(identifier="test")
        assert temp_path.name.startswith(temp_manager.TEMP_PREFIX)
        # 名称应该是 _temp_test_<timestamp>
        parts = temp_path.name.split("_")
        # split("_") 会是 ['', 'temp', 'test', '<timestamp>']
        assert len(parts) == 4
        assert parts[0] == ""
        assert parts[1] == "temp"
        assert parts[2] == "test"
        assert parts[3].isdigit()


class TestTempDirRegistration:
    """临时目录注册测试"""

    def test_register_temp_dir(self):
        """测试注册临时目录"""
        temp_manager._temp_dirs.clear()
        test_path = Path("_temp_test")

        temp_manager.register_temp_dir(test_path)
        assert test_path in temp_manager._temp_dirs

    def test_unregister_temp_dir(self):
        """测试注销临时目录"""
        temp_manager._temp_dirs.clear()
        test_path = Path("_temp_test")

        temp_manager.register_temp_dir(test_path)
        assert test_path in temp_manager._temp_dirs

        temp_manager.unregister_temp_dir(test_path)
        assert test_path not in temp_manager._temp_dirs

    def test_unregister_nonexistent_dir(self):
        """测试注销不存在的目录（不应报错）"""
        temp_manager._temp_dirs.clear()
        test_path = Path("_temp_nonexistent")

        # 不应该抛出异常
        temp_manager.unregister_temp_dir(test_path)
        assert test_path not in temp_manager._temp_dirs


class TestTempDirCleanup:
    """临时目录清理测试"""

    def test_cleanup_temp_dir_exists(self, tmp_path):
        """测试清理存在的临时目录"""
        # 创建临时目录
        temp_dir = tmp_path / "_temp_test_cleanup"
        temp_dir.mkdir()
        (temp_dir / "file.txt").write_text("test")

        # 确认目录存在
        assert temp_dir.exists()

        # 清理
        temp_manager.cleanup_temp_dir(temp_dir)

        # 确认目录已删除
        assert not temp_dir.exists()

    def test_cleanup_temp_dir_not_exists(self, tmp_path):
        """测试清理不存在的临时目录（不应报错）"""
        temp_dir = tmp_path / "_temp_nonexistent"

        # 不应该抛出异常
        temp_manager.cleanup_temp_dir(temp_dir)

    def test_cleanup_temp_dir_with_files(self, tmp_path):
        """测试清理包含文件的临时目录"""
        # 创建包含多个文件的临时目录
        temp_dir = tmp_path / "_temp_test_files"
        temp_dir.mkdir()
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        # 清理
        temp_manager.cleanup_temp_dir(temp_dir)

        # 确认目录已完全删除
        assert not temp_dir.exists()


class TestCleanupOldTempDirs:
    """旧临时目录清理测试"""

    def test_cleanup_old_temp_dirs_age_threshold(self, tmp_path):
        """测试按时间阈值清理旧临时目录"""
        # 创建一个旧目录（修改时间设为 25 小时前）
        old_dir = tmp_path / "_temp_old"
        old_dir.mkdir()
        old_time = time.time() - (25 * 3600)
        os.utime(old_dir, (old_time, old_time))

        # 创建一个新目录（修改时间为现在）
        new_dir = tmp_path / "_temp_new"
        new_dir.mkdir()

        # 清理超过 24 小时的目录
        cleaned = temp_manager.cleanup_old_temp_dirs(tmp_path, max_age_hours=24)

        # 验证：旧目录应被清理，新目录应保留
        assert cleaned == 1
        assert not old_dir.exists()
        assert new_dir.exists()

        # 清理
        shutil.rmtree(new_dir)

    def test_cleanup_old_temp_dirs_no_match(self, tmp_path):
        """测试没有旧目录需要清理"""
        # 创建新目录
        new_dir = tmp_path / "_temp_new"
        new_dir.mkdir()

        # 清理
        cleaned = temp_manager.cleanup_old_temp_dirs(tmp_path, max_age_hours=24)

        # 验证：没有目录被清理
        assert cleaned == 0
        assert new_dir.exists()

        # 清理
        shutil.rmtree(new_dir)

    def test_cleanup_old_temp_dirs_non_temp_dirs(self, tmp_path):
        """测试不清理非临时目录"""
        # 创建一个不以 _temp_ 开头的目录
        other_dir = tmp_path / "other_directory"
        other_dir.mkdir()
        old_time = time.time() - (25 * 3600)
        os.utime(other_dir, (old_time, old_time))

        # 清理
        cleaned = temp_manager.cleanup_old_temp_dirs(tmp_path, max_age_hours=24)

        # 验证：非临时目录不应被清理
        assert cleaned == 0
        assert other_dir.exists()

        # 清理
        shutil.rmtree(other_dir)


class TestTemporaryDirectoryContextManager:
    """临时目录上下文管理器测试"""

    def test_context_manager_creates_directory(self, tmp_path):
        """测试上下文管理器创建目录"""
        with temp_manager.temporary_directory(
            identifier="test_cm",
            base_dir=tmp_path,
            cleanup_on_exit=False  # 不自动清理，以便验证
        ) as temp_dir:
            assert temp_dir.exists()
            assert temp_dir.name.startswith(temp_manager.TEMP_PREFIX)
            assert "test_cm" in temp_dir.name

        # 手动清理
        shutil.rmtree(temp_dir)

    def test_context_manager_cleans_up_on_exit(self, tmp_path):
        """测试上下文管理器退出时自动清理"""
        with temp_manager.temporary_directory(
            identifier="test_cleanup",
            base_dir=tmp_path,
            cleanup_on_exit=True
        ) as temp_dir:
            temp_path = temp_dir
            assert temp_path.exists()

        # 退出后目录应被清理
        assert not temp_path.exists()

    def test_context_manager_no_cleanup(self, tmp_path):
        """测试上下文管理器不自动清理"""
        with temp_manager.temporary_directory(
            identifier="test_no_cleanup",
            base_dir=tmp_path,
            cleanup_on_exit=False
        ) as temp_dir:
            temp_path = temp_dir
            assert temp_path.exists()

        # 退出后目录应保留
        assert temp_path.exists()

        # 手动清理
        shutil.rmtree(temp_path)

    def test_context_manager_with_files(self, tmp_path):
        """测试上下文管理器中的文件操作"""
        with temp_manager.temporary_directory(
            identifier="test_files",
            base_dir=tmp_path
        ) as temp_dir:
            # 创建文件
            test_file = temp_dir / "test.txt"
            test_file.write_text("hello, world!")

            assert test_file.exists()
            assert test_file.read_text() == "hello, world!"

        # 目录应被清理
        assert not temp_dir.exists()

    def test_context_manager_exception_handling(self, tmp_path):
        """测试上下文管理器在异常时也能清理"""
        try:
            with temp_manager.temporary_directory(
                identifier="test_exception",
                base_dir=tmp_path
            ) as temp_dir:
                temp_path = temp_dir
                # 创建文件
                (temp_dir / "test.txt").write_text("test")
                # 抛出异常
                raise ValueError("Test exception")
        except ValueError:
            pass

        # 即使发生异常，目录也应被清理
        assert not temp_path.exists()


class TestCleanupAllTempDirs:
    """清理所有临时目录测试"""

    def test_cleanup_all_temp_dirs(self, tmp_path):
        """测试清理所有已注册的临时目录"""
        # 清空已注册的目录集合
        temp_manager._temp_dirs.clear()

        # 创建多个临时目录
        temp1 = tmp_path / "_temp_1"
        temp2 = tmp_path / "_temp_2"
        temp3 = tmp_path / "_temp_3"

        for d in [temp1, temp2, temp3]:
            d.mkdir()
            temp_manager.register_temp_dir(d)

        # 验证已注册
        assert len(temp_manager._temp_dirs) == 3

        # 清理所有
        temp_manager.cleanup_all_temp_dirs()

        # 验证所有目录被清理且注销
        assert not temp1.exists()
        assert not temp2.exists()
        assert not temp3.exists()
        assert len(temp_manager._temp_dirs) == 0


class TestInitializeCleanup:
    """初始化清理测试"""

    def test_initialize_cleanup(self, tmp_path):
        """测试初始化清理功能"""
        # 创建一个旧目录
        old_dir = tmp_path / "_temp_old_init"
        old_dir.mkdir()
        old_time = time.time() - (25 * 3600)
        os.utime(old_dir, (old_time, old_time))

        # 创建一个新目录
        new_dir = tmp_path / "_temp_new_init"
        new_dir.mkdir()

        # 初始化清理
        temp_manager.initialize_cleanup(base_dir=tmp_path, max_age_hours=24)

        # 验证：旧目录应被清理，新目录应保留
        assert not old_dir.exists()
        assert new_dir.exists()

        # 清理
        shutil.rmtree(new_dir)
