# config.py
"""
统一配置管理
所有硬编码的配置值都集中在这里，支持环境变量覆盖
"""

import os
from dataclasses import dataclass
from typing import Any
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


@dataclass(frozen=True)
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    wait_multiplier: float = 1.0
    wait_min: float = 2.0
    wait_max: float = 10.0


@dataclass(frozen=True)
class MinerUConfig:
    """MinerU API 配置"""
    base_url: str = "https://mineru.net/api/v4"
    api_token: str = ""

    # API 参数
    enable_formula: bool = True
    enable_table: bool = True
    layout_model: str = "doclayout_yolo"
    language: str = "ch"

    # 支持的文件格式（上传到 MinerU API 的文件类型）
    supported_formats: tuple = (".jpg", ".jpeg", ".png", ".webp", ".pdf")

    # 超时配置（秒）
    request_timeout: int = 30
    poll_max_wait: int = 300
    poll_interval: int = 3
    zip_download_timeout: int = 120

    # 并发配置
    max_concurrent_uploads: int = 5  # 最大并发上传数

    # 重试配置
    retry: RetryConfig = RetryConfig()

    def __post_init__(self):
        """从环境变量读取 API Token"""
        if not object.__getattribute__(self, 'api_token'):
            token = os.getenv('MINERU_API_TOKEN', '')
            object.__setattr__(self, 'api_token', token)


@dataclass(frozen=True)
class DownloaderConfig:
    """下载器配置"""
    # 默认输出目录
    default_output_dir: str = "output"

    # 用户代理
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # 超时配置（秒）
    request_timeout: int = 30

    # 下载间隔（秒）- 礼貌性延时
    download_delay: float = 0.5

    # 并发配置
    max_concurrent_downloads: int = 5  # 最大并发下载数

    # 标题处理
    max_title_length: int = 50

    # 支持的图片格式
    supported_formats: tuple = (".jpg", ".jpeg", ".png", ".webp", ".pdf")

    # 重试配置
    retry: RetryConfig = RetryConfig()


@dataclass(frozen=True)
class WebConfig:
    """Web 服务配置"""
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True

    # 安全配置
    secret_key: str = "dev-secret-key-change-in-production"

    # CORS 配置
    cors_enabled: bool = True
    cors_origins: str | list[str] = "*"  # "*" 允许所有来源，生产环境应限制

    # 输出目录
    output_dir: str = "output"

    # 历史记录限制
    max_history_items: int = 10

    # 任务配置
    task_poll_interval_ms: int = 2000  # 前端轮询间隔（毫秒）
    task_max_poll_attempts: int = 300   # 最多轮询次数（10分钟）

    def __post_init__(self):
        """从环境变量读取配置"""
        # 从环境变量读取 debug 配置
        debug_env = os.getenv('WEB_DEBUG', '')
        if debug_env.lower() in ('0', 'false', 'no'):
            object.__setattr__(self, 'debug', False)
        elif debug_env.lower() in ('1', 'true', 'yes'):
            object.__setattr__(self, 'debug', True)

        # 从环境变量读取端口
        port_env = os.getenv('WEB_PORT', '')
        if port_env.isdigit():
            object.__setattr__(self, 'port', int(port_env))

        # 从环境变量读取 SECRET_KEY
        secret_key_env = os.getenv('WEB_SECRET_KEY', '')
        if secret_key_env:
            object.__setattr__(self, 'secret_key', secret_key_env)

        # 从环境变量读取 CORS 配置
        cors_env = os.getenv('WEB_CORS_ENABLED', '')
        if cors_env.lower() in ('0', 'false', 'no'):
            object.__setattr__(self, 'cors_enabled', False)

        cors_origins_env = os.getenv('WEB_CORS_ORIGINS', '')
        if cors_origins_env:
            # 支持逗号分隔的多个来源
            origins = [o.strip() for o in cors_origins_env.split(',')]
            object.__setattr__(self, 'cors_origins', origins)


@dataclass(frozen=True)
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    log_dir: str = "logs"
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


# 全局配置实例
mineru = MinerUConfig()
downloader = DownloaderConfig()
web = WebConfig()
logging = LoggingConfig()


def get_mineru_token() -> str:
    """获取 MinerU API Token（便捷方法）"""
    return mineru.api_token


def validate_config() -> dict[str, Any]:
    """
    验证配置是否完整

    Returns:
        dict: {"valid": bool, "errors": list[str]}
    """
    errors = []

    # 验证 MinerU Token
    if not mineru.api_token:
        errors.append("MINERU_API_TOKEN 未设置")

    # 验证输出目录
    try:
        os.makedirs(downloader.default_output_dir, exist_ok=True)
    except Exception as e:
        errors.append(f"无法创建输出目录: {e}")

    # 验证日志目录
    try:
        os.makedirs(logging.log_dir, exist_ok=True)
    except Exception as e:
        errors.append(f"无法创建日志目录: {e}")

    return {"valid": len(errors) == 0, "errors": errors}
