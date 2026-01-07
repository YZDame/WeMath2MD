import requests
from bs4 import BeautifulSoup
import os
import time
import re
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from logger import get_logger
from config import downloader as cfg

logger = get_logger("wemath2md.downloader")


class WechatImageDownloader:
    # 可重试的异常类型
    RETRYABLE_EXCEPTIONS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    )

    def __init__(self, output_dir: str | None = None):
        """
        初始化下载器

        Args:
            output_dir: 基础输出目录，默认从配置读取
        """
        self.output_dir = Path(output_dir or cfg.default_output_dir)
        self.article_title: str | None = None
        self.result_dir: Path | None = None  # 最终结果目录（以标题命名）
        self.images_dir: Path | None = None  # 图片保存目录

        # 伪装成浏览器，防止反爬
        self.headers = {"User-Agent": cfg.user_agent}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logger.level),
        reraise=True
    )
    def _http_get(self, url: str, **kwargs) -> requests.Response:
        """带重试的 HTTP GET 请求"""
        return requests.get(url, headers=self.headers, **kwargs)

    def get_article_content(self, url: str) -> str | None:
        """获取网页HTML内容"""
        try:
            response = self._http_get(url, timeout=cfg.request_timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"请求文章失败: {e}")
            return None
    
    def extract_title(self, html_content: str) -> str:
        """从HTML中提取文章标题"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试多种方式获取标题
        title = None
        
        # 方式1: 微信公众号特定标签
        title_tag = soup.find(id="activity-name")
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # 方式2: og:title meta 标签
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
        
        # 方式3: 标准 title 标签
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        # 清理标题中的非法字符（用于文件名）
        if title:
            # 移除或替换文件名非法字符
            title = re.sub(r'[\\/*?:"<>|]', '_', title)
            # 移除多余空格
            title = re.sub(r'\s+', ' ', title).strip()
            # 限制长度（避免文件名过长）
            if len(title) > cfg.max_title_length:
                title = title[:cfg.max_title_length]

        return title or f"article_{int(time.time())}"
    
    def setup_directories(self, title: str) -> Path:
        """根据标题设置目录结构"""
        self.article_title = title

        # 创建结果目录: output/{标题}/
        self.result_dir = self.output_dir / title
        self.result_dir.mkdir(parents=True, exist_ok=True)

        # 创建图片子目录: output/{标题}/downloaded_images/
        self.images_dir = self.result_dir / "downloaded_images"
        self.images_dir.mkdir(exist_ok=True)

        logger.info(f"结果目录: {self.result_dir}")
        return self.result_dir

    def extract_images(self, html_content: str) -> list[str]:
        """从HTML中提取所有图片链接"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 公众号正文通常在 id="img-content" 或 class="rich_media_content" 中
        content = soup.find(id="img-content")
        if not content:
            content = soup.find(class_="rich_media_content")
            
        if not content:
            logger.warning("未找到正文内容")
            return []

        images = []
        # 微信公众号图片的真实链接通常在 data-src 中
        for img in content.find_all('img'):
            src = img.get('data-src')
            if src:
                # 过滤掉一些图标或无效图片（可选）
                images.append(src)

        return images

    def _download_single_image(self, index: int, url: str) -> str | None:
        """下载单张图片的内部方法（用于并发下载）

        Args:
            index: 图片索引
            url: 图片 URL

        Returns:
            保存的文件路径，失败返回 None
        """
        try:
            # 获取图片格式
            fmt = "jpg"  # 默认为jpg
            if "fmt=" in url:
                fmt_match = re.search(r'fmt=([a-zA-Z]+)', url)
                if fmt_match:
                    fmt = fmt_match.group(1)

            # 构造文件名：001.jpg, 002.png ...
            filename = f"{index+1:03d}.{fmt}"
            filepath = self.images_dir / filename

            # 下载（带重试）
            img_resp = self._http_get(url, timeout=cfg.request_timeout)
            with open(filepath, 'wb') as f:
                f.write(img_resp.content)

            logger.info(f"已下载 [{index+1}]: {filename}")
            return str(filepath)

        except Exception as e:
            logger.error(f"下载第 {index+1} 张图片失败: {e}")
            return None

    def download_images(self, img_urls: list[str]) -> list[str]:
        """并发下载图片列表

        Args:
            img_urls: 图片 URL 列表

        Returns:
            下载成功的文件路径列表
        """
        if self.images_dir is None:
            raise Exception("请先调用 setup_directories() 设置目录")

        logger.info(f"找到 {len(img_urls)} 张图片，使用 {cfg.max_concurrent_downloads} 线程并发下载...")

        saved_files = []

        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=cfg.max_concurrent_downloads) as executor:
            # 提交所有下载任务
            future_to_index = {
                executor.submit(self._download_single_image, i, url): i
                for i, url in enumerate(img_urls)
            }

            # 收集结果
            completed = 0
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                completed += 1
                try:
                    result = future.result()
                    if result:
                        saved_files.append(result)
                except Exception as e:
                    logger.error(f"下载任务 {index+1} 异常: {e}")

                # 礼貌性延时（在并发时可以减少延时）
                time.sleep(cfg.download_delay / cfg.max_concurrent_downloads)

        # 按原始顺序排序
        saved_files.sort(key=lambda x: int(Path(x).stem.split('_')[0]) if '_' in Path(x).stem else int(Path(x).stem))

        logger.info(f"下载完成: 成功 {len(saved_files)}/{len(img_urls)} 张")
        return saved_files
    
    def download_from_url(self, url: str) -> dict[str, str | list[str]] | None:
        """
        一站式下载：从 URL 获取文章，提取标题，下载图片

        Returns:
            dict: {
                'title': 文章标题,
                'result_dir': 结果目录路径,
                'images_dir': 图片目录路径,
                'images': 下载的图片文件列表
            }
        """
        logger.info(f"正在获取文章: {url}")

        # 1. 获取 HTML
        html = self.get_article_content(url)
        if not html:
            return None

        # 2. 提取标题
        title = self.extract_title(html)
        logger.info(f"文章标题: {title}")

        # 3. 设置目录
        self.setup_directories(title)

        # 4. 提取并下载图片
        img_urls = self.extract_images(html)
        saved_files = self.download_images(img_urls)

        logger.info(f"下载完成！共 {len(saved_files)} 张图片")
        logger.info(f"保存位置: {self.images_dir}")

        return {
            'title': title,
            'result_dir': str(self.result_dir),
            'images_dir': str(self.images_dir),
            'images': saved_files
        }


# --- 测试代码 ---
if __name__ == "__main__":
    from logger import setup_logger

    # 初始化日志
    setup_logger(level="INFO", log_file="downloader.log")

    # 这里换成一个真实的公众号文章链接进行测试
    test_url = "https://mp.weixin.qq.com/s/0FKXBV81FzHcd4QcHTVvHg"

    if "你的测试文章链接" in test_url:
        logger.warning("请先替换代码底部的 test_url 为真实的公众号文章链接！")
    else:
        downloader = WechatImageDownloader(output_dir="output")
        result = downloader.download_from_url(test_url)

        if result:
            logger.info(f"下载结果: 标题={result['title']}, 结果目录={result['result_dir']}, "
                        f"图片目录={result['images_dir']}, 图片数量={len(result['images'])}")
