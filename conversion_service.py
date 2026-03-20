"""
转换服务层
统一封装下载 + OCR 转换流程，供 CLI 和 Web 复用
"""

from typing import Any, Callable
from downloader import WechatImageDownloader
from mineru_converter import MinerUConverter
from logger import get_logger

logger = get_logger("wemath2md.service")


ProgressCallback = Callable[[str, int], None]


def convert_wechat_article(
    url: str,
    api_token: str,
    output_dir: str = "output",
    progress_callback: ProgressCallback | None = None
) -> dict[str, Any] | None:
    """
    一站式处理微信公众号文章。

    Args:
        url: 微信公众号文章链接
        api_token: MinerU API Token
        output_dir: 输出基础目录
        progress_callback: 进度回调 (message, percent)

    Returns:
        dict: 包含输出路径信息；失败返回 None
    """
    if progress_callback:
        progress_callback("下载图片中...", 10)

    downloader = WechatImageDownloader(output_dir=output_dir)
    download_result = downloader.download_from_url(url)
    if not download_result:
        logger.error("下载失败，流程终止")
        return None

    if progress_callback:
        progress_callback("OCR 转换中...", 50)

    converter = MinerUConverter(api_token=api_token)
    convert_result = converter.convert_images(
        image_dir=download_result["images_dir"],
        output_dir=download_result["result_dir"],
        output_name="converted"
    )
    if not convert_result:
        logger.error("OCR 转换失败")
        return None

    if progress_callback:
        progress_callback("完成", 100)

    return {
        "title": download_result["title"],
        "result_dir": download_result["result_dir"],
        "downloaded_images_dir": download_result["images_dir"],
        "converted_dir": convert_result["output_dir"],
        "md_file": convert_result["md_file"],
        "converted_images_dir": convert_result["images_dir"],
        "zip_file": convert_result["zip_file"],
        "original_image_count": len(download_result["images"]),
        "extracted_image_count": convert_result["image_count"],
    }
