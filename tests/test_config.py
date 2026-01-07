# tests/test_config.py
"""
配置模块单元测试
测试 config.py 中的配置类和函数
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from config import (
    RetryConfig,
    MinerUConfig,
    DownloaderConfig,
    WebConfig,
    LoggingConfig,
    mineru,
    downloader,
    web,
    logging as logging_cfg,
    get_mineru_token,
    validate_config
)


class TestRetryConfig:
    """重试配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.wait_multiplier == 1.0
        assert config.wait_min == 2.0
        assert config.wait_max == 10.0

    def test_custom_values(self):
        """测试自定义值"""
        config = RetryConfig(
            max_attempts=5,
            wait_multiplier=2.0,
            wait_min=1.0,
            wait_max=20.0
        )
        assert config.max_attempts == 5
        assert config.wait_multiplier == 2.0


class TestMinerUConfig:
    """MinerU 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = MinerUConfig()
        assert config.base_url == "https://mineru.net/api/v4"
        assert config.enable_formula is True
        assert config.enable_table is True
        assert config.layout_model == "doclayout_yolo"
        assert config.language == "ch"
        assert config.request_timeout == 30
        assert config.poll_max_wait == 300
        assert config.poll_interval == 3
        assert config.zip_download_timeout == 120

    def test_token_from_env(self):
        """测试从环境变量读取 token"""
        with patch.dict(os.environ, {'MINERU_API_TOKEN': 'env_token_123'}):
            config = MinerUConfig()
            assert config.api_token == 'env_token_123'

    def test_token_from_param(self):
        """测试从参数传入 token"""
        config = MinerUConfig(api_token='param_token_456')
        assert config.api_token == 'param_token_456'

    def test_supported_formats(self):
        """测试支持的格式"""
        config = MinerUConfig()
        assert ".jpg" in config.supported_formats
        assert ".png" in config.supported_formats
        assert ".webp" in config.supported_formats
        assert ".pdf" in config.supported_formats
        # GIF 应该被排除
        assert ".gif" not in config.supported_formats


class TestDownloaderConfig:
    """下载器配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = DownloaderConfig()
        assert config.default_output_dir == "output"
        assert "Mozilla" in config.user_agent
        assert config.request_timeout == 30
        assert config.download_delay == 0.5
        assert config.max_title_length == 50

    def test_user_agent_format(self):
        """测试 User-Agent 格式"""
        config = DownloaderConfig()
        assert "Chrome" in config.user_agent
        assert "Safari" in config.user_agent


class TestWebConfig:
    """Web 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = WebConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.debug is True
        assert config.output_dir == "output"
        assert config.max_history_items == 10
        assert config.secret_key == "dev-secret-key-change-in-production"
        assert config.cors_enabled is True
        assert config.cors_origins == "*"

    def test_debug_from_env(self):
        """测试从环境变量读取 debug 配置"""
        with patch.dict(os.environ, {'WEB_DEBUG': 'false'}):
            config = WebConfig()
            assert config.debug is False

        with patch.dict(os.environ, {'WEB_DEBUG': 'true'}):
            config = WebConfig()
            assert config.debug is True

    def test_port_from_env(self):
        """测试从环境变量读取端口配置"""
        with patch.dict(os.environ, {'WEB_PORT': '9000'}):
            config = WebConfig()
            assert config.port == 9000

    def test_secret_key_from_env(self):
        """测试从环境变量读取 SECRET_KEY"""
        with patch.dict(os.environ, {'WEB_SECRET_KEY': 'custom-secret-key-12345'}):
            config = WebConfig()
            assert config.secret_key == 'custom-secret-key-12345'

    def test_cors_enabled_from_env(self):
        """测试从环境变量读取 CORS 启用配置"""
        with patch.dict(os.environ, {'WEB_CORS_ENABLED': 'false'}):
            config = WebConfig()
            assert config.cors_enabled is False

        with patch.dict(os.environ, {'WEB_CORS_ENABLED': 'true'}):
            config = WebConfig()
            assert config.cors_enabled is True

    def test_cors_origins_from_env_single(self):
        """测试从环境变量读取单个 CORS 来源"""
        with patch.dict(os.environ, {'WEB_CORS_ORIGINS': 'https://example.com'}):
            config = WebConfig()
            assert config.cors_origins == ['https://example.com']

    def test_cors_origins_from_env_multiple(self):
        """测试从环境变量读取多个 CORS 来源"""
        with patch.dict(os.environ, {'WEB_CORS_ORIGINS': 'https://example.com,https://www.example.com'}):
            config = WebConfig()
            assert config.cors_origins == ['https://example.com', 'https://www.example.com']


class TestLoggingConfig:
    """日志配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.log_dir == "logs"
        assert "%(asctime)s" in config.format_string
        assert config.date_format == "%Y-%m-%d %H:%M:%S"


class TestGlobalConfigInstances:
    """全局配置实例测试"""

    def test_mineru_instance(self):
        """测试 mineru 全局实例"""
        assert mineru.base_url == "https://mineru.net/api/v4"
        assert mineru.enable_formula is True

    def test_downloader_instance(self):
        """测试 downloader 全局实例"""
        assert downloader.default_output_dir == "output"
        assert downloader.request_timeout == 30

    def test_web_instance(self):
        """测试 web 全局实例"""
        assert web.host == "0.0.0.0"
        assert web.port == 8080

    def test_logging_instance(self):
        """测试 logging 全局实例"""
        assert logging_cfg.level == "INFO"


class TestConfigFunctions:
    """配置函数测试"""

    @patch('config.mineru')
    def test_get_mineru_token(self, mock_mineru):
        """测试获取 token 函数"""
        mock_mineru.api_token = 'test_func_token'
        token = get_mineru_token()
        assert token == 'test_func_token'

    @patch('config.mineru')
    @patch('config.downloader')
    @patch('config.logging')
    @patch('os.makedirs')
    def test_validate_config_success(self, mock_makedirs, mock_logging, mock_downloader, mock_mineru, tmp_path):
        """测试配置验证成功"""
        mock_mineru.api_token = 'test_token'
        mock_downloader.default_output_dir = str(tmp_path)
        mock_logging.log_dir = str(tmp_path)
        result = validate_config()
        assert result['valid'] is True
        assert len(result['errors']) == 0

    @patch('config.mineru')
    @patch('config.downloader')
    @patch('config.logging')
    @patch('os.makedirs')
    def test_validate_config_missing_token(self, mock_makedirs, mock_logging, mock_downloader, mock_mineru):
        """测试缺少 token"""
        mock_mineru.api_token = ''
        mock_downloader.default_output_dir = '/tmp/test'
        mock_logging.log_dir = '/tmp/test'
        result = validate_config()
        assert result['valid'] is False
        assert any("MINERU_API_TOKEN" in e for e in result['errors'])

    @patch('config.mineru')
    @patch('config.downloader')
    @patch('config.logging')
    @patch('os.makedirs', side_effect=OSError("Permission denied"))
    def test_validate_config_output_dir_error(self, mock_makedirs, mock_logging, mock_downloader, mock_mineru):
        """测试输出目录创建失败"""
        mock_mineru.api_token = 'test_token'
        mock_downloader.default_output_dir = '/tmp/test'
        mock_logging.log_dir = '/tmp/test'
        result = validate_config()
        assert result['valid'] is False
        assert any("输出目录" in e for e in result['errors'])
