# mineru_converter.py
"""
MinerU API 批量图片转 Markdown
功能：批量上传图片，识别后合并 markdown 和图片，打包成 zip 返回
"""

import os
import io
import re
import time
import shutil
import zipfile
import requests
from enum import Enum
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
from config import mineru as cfg
import temp_manager

logger = get_logger("wemath2md.converter")


class ConversionState(str, Enum):
    """MinerU API 转换状态枚举

    与 MinerU API 返回的状态值对应
    """
    DONE = "done"
    FAILED = "failed"
    PROCESSING = "processing"
    PENDING = "pending"


class MinerUConverter:
    # 可重试的异常类型
    RETRYABLE_EXCEPTIONS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    )

    def __init__(self, api_token: str | None = None):
        """初始化转换器

        Args:
            api_token: MinerU API Token，如果不提供则从配置读取
        """
        self.token = api_token or cfg.api_token
        self.base_url = cfg.base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        # 获取重试配置
        self._retry_config = cfg.retry

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logger.level),
        reraise=True
    )
    def _api_post(self, url: str, **kwargs) -> requests.Response:
        """带重试的 POST 请求"""
        return requests.post(url, headers=self.headers, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logger.level),
        reraise=True
    )
    def _api_get(self, url: str, **kwargs) -> requests.Response:
        """带重试的 GET 请求"""
        return requests.get(url, headers=self.headers, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logger.level),
        reraise=True
    )
    def _http_get(self, url: str, **kwargs) -> requests.Response:
        """带重试的普通 HTTP GET 请求（用于下载文件）"""
        return requests.get(url, **kwargs)
    
    def apply_upload_urls(self, file_names: list[str]) -> tuple[str, list[str]]:
        """步骤1: 批量申请上传链接"""
        url = f"{self.base_url}/file-urls/batch"

        # 使用带序号的 data_id 以便后续排序
        files = [
            {"name": name, "data_id": f"file_{i:04d}_{int(time.time())}"}
            for i, name in enumerate(file_names)
        ]

        data = {
            "files": files,
            "enable_formula": cfg.enable_formula,
            "enable_table": cfg.enable_table,
            "layout_model": cfg.layout_model,
            "language": cfg.language
        }

        response = self._api_post(url, json=data)

        if response.status_code == 200:
            result = response.json()
            if result["code"] == 0:
                return result["data"]["batch_id"], result["data"]["file_urls"]
            else:
                raise Exception(f"申请上传链接失败: {result}")
        else:
            raise Exception(f"API 请求失败: {response.status_code}")
    
    def _upload_single_file(self, file_path: str, upload_url: str) -> bool:
        """上传单个文件的内部方法（用于并发上传）

        Args:
            file_path: 本地文件路径
            upload_url: 上传 URL

        Returns:
            是否上传成功
        """
        try:
            with open(file_path, 'rb') as f:
                response = requests.put(upload_url, data=f)

            if response.status_code == 200:
                logger.info(f"上传成功: {os.path.basename(file_path)}")
                return True
            else:
                logger.error(f"上传失败: {os.path.basename(file_path)} - HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"上传异常 {os.path.basename(file_path)}: {e}")
            return False

    def upload_files(self, file_paths: list[str], upload_urls: list[str]) -> int:
        """步骤2: 并发上传文件

        Args:
            file_paths: 本地文件路径列表
            upload_urls: 上传 URL 列表

        Returns:
            成功上传的文件数量
        """
        logger.info(f"使用 {cfg.max_concurrent_uploads} 线程并发上传 {len(file_paths)} 个文件...")

        success_count = 0

        # 使用线程池并发上传
        with ThreadPoolExecutor(max_workers=cfg.max_concurrent_uploads) as executor:
            # 提交所有上传任务
            future_to_file = {
                executor.submit(self._upload_single_file, fp, url): fp
                for fp, url in zip(file_paths, upload_urls)
            }

            # 收集结果
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    logger.error(f"上传任务异常 {os.path.basename(file_path)}: {e}")

        logger.info(f"上传完成: 成功 {success_count}/{len(file_paths)} 个文件")
        return success_count
    
    def wait_for_result(
        self,
        batch_id: str,
        max_wait: int | None = None,
        interval: int | None = None
    ) -> list[dict[str, Any]]:
        """步骤3: 等待解析完成

        Args:
            batch_id: 批次 ID
            max_wait: 最大等待时间（秒），默认从配置读取
            interval: 轮询间隔（秒），默认从配置读取
        """
        # 使用配置值或参数值
        max_wait = max_wait or cfg.poll_max_wait
        interval = interval or cfg.poll_interval

        url = f"{self.base_url}/extract-results/batch/{batch_id}"

        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = self._api_get(url)

            if response.status_code == 200:
                result = response.json()

                if result["code"] == 0:
                    extract_result = result["data"].get("extract_result", [])

                    if not extract_result:
                        # 还没有结果
                        elapsed = int(time.time() - start_time)
                        logger.debug(f"等待解析开始... ({elapsed}s)")
                        time.sleep(interval)
                        continue

                    # 检查所有文件的状态
                    states = [item.get("state") for item in extract_result]

                    if all(s == ConversionState.DONE for s in states):
                        logger.info("全部解析完成!")
                        return extract_result
                    elif any(s == ConversionState.FAILED for s in states):
                        failed = [item["file_name"] for item in extract_result if item.get("state") == ConversionState.FAILED]
                        logger.warning(f"部分文件失败: {failed}")
                        return extract_result
                    else:
                        # 还在处理中
                        done_count = sum(1 for s in states if s == ConversionState.DONE)
                        elapsed = int(time.time() - start_time)
                        logger.debug(f"解析中: {done_count}/{len(states)} 完成 ({elapsed}s)")
                        time.sleep(interval)
                else:
                    raise Exception(f"查询失败: {result}")
            else:
                raise Exception(f"查询请求失败: {response.status_code}")

        raise Exception(f"等待超时 ({max_wait}s)")
    
    def download_and_extract_zip(self, zip_url: str, file_name: str, temp_dir: Path, index: int) -> tuple[str, int]:
        """
        下载 zip 并解压到临时目录
        返回: (md_content, images_extracted_count)

        zip 结构:
        <root>/
           ├── full.md                 ← 需要抽取的 Markdown 内容
           ├── images/                 ← 图片资源文件夹
           ├── *.json                  ← 可忽略
           ├── *_origin.pdf            ← 可忽略
        """
        try:
            response = self._http_get(zip_url, timeout=cfg.zip_download_timeout)

            if response.status_code != 200:
                return f"<!-- {file_name}: 下载失败 {response.status_code} -->", 0

            md_content = None
            images_count = 0

            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                # 打印 zip 内容用于调试
                all_files = zf.namelist()
                logger.debug(f"ZIP 包含 {len(all_files)} 个文件")

                # 找 markdown 文件
                for name in all_files:
                    # full.md 可能在根目录或一级子目录下
                    if name.endswith('full.md') or name.endswith('.md'):
                        parts = name.split('/')
                        # 优先选择 full.md
                        if name.endswith('full.md') and len(parts) <= 2:
                            md_content = zf.read(name).decode('utf-8')
                            md_content = self._rewrite_image_paths(md_content, index)
                            break
                        # 备选任何 .md 文件
                        elif md_content is None and len(parts) <= 2:
                            md_content = zf.read(name).decode('utf-8')
                            md_content = self._rewrite_image_paths(md_content, index)

                # 提取 images 文件夹中的图片（支持多种路径格式）
                for name in all_files:
                    # 跳过目录
                    if name.endswith('/'):
                        continue

                    # 检查是否是图片文件（在 images 目录下或者是图片扩展名）
                    lower_name = name.lower()
                    is_image = any(lower_name.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])
                    is_in_images = '/images/' in name or name.startswith('images/')

                    if is_image and is_in_images:
                        # 获取原始图片文件名
                        img_name = os.path.basename(name)
                        # 添加索引前缀避免冲突
                        new_img_name = f"{index:04d}_{img_name}"

                        # 保存到临时目录的 images 文件夹
                        target_path = temp_dir / "images" / new_img_name
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        with open(target_path, 'wb') as f:
                            f.write(zf.read(name))
                        images_count += 1

            if md_content is None:
                md_content = f"<!-- {file_name}: zip 中未找到 markdown 文件 -->"

            return md_content, images_count

        except Exception as e:
            return f"<!-- {file_name}: 下载/解压异常 {e} -->", 0
    
    def _rewrite_image_paths(self, md_content: str, index: int) -> str:
        """
        重写 markdown 中的图片路径
        将 images/xxx.png 改为 images/{index:04d}_xxx.png
        """
        def replace_func(match):
            # 获取原始路径
            prefix = match.group(1)  # ![ 或 ![xxx
            alt_text = match.group(2)  # alt 文本
            img_path = match.group(3)  # 图片路径

            # 只处理 images/ 开头的路径
            if img_path.startswith('images/'):
                img_name = img_path[7:]  # 去掉 'images/' 前缀
                new_path = f"images/{index:04d}_{img_name}"
                return f"![{alt_text}]({new_path})"
            return match.group(0)

        # 匹配 markdown 图片语法 ![alt](path)
        pattern = r'(!\[)([^\]]*)\]\(([^)]+)\)'
        return re.sub(pattern, replace_func, md_content)

    def convert_images(
        self,
        image_dir: str | Path,
        output_dir: str | Path | None = None,
        output_name: str | None = None
    ) -> dict[str, Any] | None:
        """
        主流程：批量转换图片并打包

        Args:
            image_dir: 输入图片目录
            output_dir: 输出目录（可选，默认与 image_dir 同级）
            output_name: 输出文件夹/md文件的名称（可选，默认 "converted"）

        Returns:
            dict: {
                'output_dir': 输出目录路径,
                'md_file': markdown 文件路径,
                'images_dir': 图片目录路径,
                'zip_file': zip 文件路径,
                'image_count': 提取的图片数量
            }
        """

        # MinerU API 支持的格式（从配置读取）
        valid_exts = set(cfg.supported_formats)
        image_dir = Path(image_dir)
        
        images = sorted([
            f for f in image_dir.iterdir()
            if f.suffix.lower() in valid_exts
        ])
        
        if not images:
            logger.warning("未找到图片文件")
            return None

        # 设置输出目录和名称
        if output_name is None:
            output_name = "converted"

        if output_dir is None:
            # 默认放在 image_dir 的同级目录
            output_dir = image_dir.parent / output_name
        else:
            output_dir = Path(output_dir) / output_name

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"找到 {len(images)} 个文件")
        logger.info(f"输出目录: {output_dir}")

        # 步骤1: 申请上传链接
        logger.info("步骤1: 申请上传链接...")
        file_names = [img.name for img in images]
        batch_id, upload_urls = self.apply_upload_urls(file_names)
        logger.info(f"batch_id: {batch_id}")

        # 步骤2: 上传文件
        logger.info("步骤2: 上传文件...")
        file_paths = [str(img) for img in images]
        success = self.upload_files(file_paths, upload_urls)
        logger.info(f"上传完成: {success}/{len(images)}")

        # 步骤3: 等待解析
        logger.info("步骤3: 等待解析完成...")
        results = self.wait_for_result(batch_id)

        # 步骤4: 下载、解压并合并
        logger.info("步骤4: 下载并解压 zip 文件...")

        # 使用临时目录上下文管理器
        with temp_manager.temporary_directory(identifier="converter", base_dir=Path.cwd()) as temp_dir:
            (temp_dir / "images").mkdir(exist_ok=True)

            # 按 data_id 排序确保顺序正确（按原始图片顺序）
            results_sorted = sorted(results, key=lambda x: x.get("data_id", ""))

            all_markdown = []
            total_images = 0

            for i, item in enumerate(results_sorted):
                file_name = item.get("file_name", f"file_{i}")
                state = item.get("state")
                zip_url = item.get("full_zip_url")

                if state == ConversionState.DONE and zip_url:
                    md_content, img_count = self.download_and_extract_zip(
                        zip_url, file_name, temp_dir, i
                    )
                    all_markdown.append(md_content)
                    total_images += img_count
                    logger.info(f"{file_name} (提取 {img_count} 张图片)")
                else:
                    err_msg = item.get("err_msg", "未知错误")
                    all_markdown.append(f"\n\n<!-- {file_name} 转换失败: {err_msg} -->\n\n")
                    logger.error(f"{file_name}: {err_msg}")

            logger.info(f"共提取 {total_images} 张图片")

            # 步骤5: 合并 markdown 并保存到输出目录
            logger.info("步骤5: 合并 Markdown 文件...")
            final_content = "\n\n---\n\n".join(all_markdown)

            # 直接保存到输出目录
            md_file = output_dir / f"{output_name}.md"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(final_content)
            logger.info(f"已生成: {md_file}")

            # 步骤6: 复制图片到输出目录（如果有图片的话）
            logger.info("步骤6: 复制图片到输出目录...")

            final_images_dir = output_dir / "images"
            temp_images_dir = temp_dir / "images"

            if temp_images_dir.exists() and any(temp_images_dir.iterdir()):
                final_images_dir.mkdir(exist_ok=True)
                for img_file in temp_images_dir.iterdir():
                    if img_file.is_file():
                        shutil.copy2(img_file, final_images_dir / img_file.name)
                logger.info(f"图片已保存到: {final_images_dir}")
            else:
                logger.info("无额外图片需要复制")

            # 步骤7: 打包成 zip（整个结果目录）
            logger.info("步骤7: 打包成 zip 文件...")

            result_root = output_dir.parent  # 例如 output/反演变换及其应用/
            zip_file = result_root.parent / f"{result_root.name}.zip"  # output/反演变换及其应用.zip

            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 遍历整个结果目录
                for root, dirs, files in os.walk(result_root):
                    for file in files:
                        # 跳过 zip 文件本身（避免套娃）
                        if file.endswith('.zip'):
                            continue
                        file_path = Path(root) / file
                        # 相对于结果目录的路径
                        arcname = file_path.relative_to(result_root)
                        zf.write(file_path, arcname)

            logger.info(f"已打包: {zip_file}")

            # 统计信息
            zip_size = zip_file.stat().st_size / 1024 / 1024  # MB
            logger.info(f"完成！Markdown: {md_file}, 图片数量: {total_images}, ZIP 文件: {zip_file} ({zip_size:.2f} MB)")

            return {
                'output_dir': str(output_dir),
                'md_file': str(md_file),
                'images_dir': str(final_images_dir),
                'zip_file': str(zip_file),
                'image_count': total_images
            }


# ============ 使用 ============
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from logger import setup_logger

    # 初始化日志
    setup_logger(level="INFO", log_file="converter.log")

    # 加载 .env 文件
    load_dotenv()

    # 从环境变量读取 API Token
    API_TOKEN = os.getenv("MINERU_API_TOKEN")

    if not API_TOKEN:
        logger.error("未找到 MINERU_API_TOKEN，请创建 .env 文件并设置 MINERU_API_TOKEN=your_token")
        exit(1)
    
    converter = MinerUConverter(api_token=API_TOKEN)
    
    # 单独使用示例（配合 downloader.py 使用更佳）
    # 输出目录会放在 image_dir 的同级目录下
    result = converter.convert_images(
        image_dir="downloaded_images",
        output_name="converted"
    )
    
    if result:
        logger.info(f"转换结果: 输出目录={result['output_dir']}, MD文件={result['md_file']}, "
                    f"图片目录={result['images_dir']}, ZIP文件={result['zip_file']}")
