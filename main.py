# main.py
"""
微信公众号文章图片转 Markdown 工具
整合 downloader 和 mineru_converter，一站式处理

使用方式:
    1. 命令行: wemath2md https://mp.weixin.qq.com/s/xxx
    2. 交互式: wemath2md (然后输入链接)
    3. 批量处理: wemath2md -f urls.txt
    4. 详细输出: wemath2md -v https://mp.weixin.qq.com/s/xxx
    5. 静默模式: wemath2md -q https://mp.weixin.qq.com/s/xxx
    6. 预览模式: wemath2md --dry-run -f urls.txt

命令行参数:
    url             文章链接（可选）
    -o, --output    输出目录（默认: output）
    -v, --verbose   详细输出模式（DEBUG 级别）
    -q, --quiet     静默模式（只输出错误）
    -f, --file      从文件读取 URL 批量处理
    --no-progress   不显示进度条
    --dry-run       预览模式（只验证 URL）
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from tqdm import tqdm
from logger import setup_logger, get_logger
from config import downloader as cfg, get_mineru_token, validate_config
from conversion_service import convert_wechat_article
import temp_manager

# 加载 .env 文件
load_dotenv()

# 初始化日志
logger = get_logger("wemath2md")


def process_wechat_article(
    url: str,
    api_token: str,
    output_dir: str = "output",
    show_progress: bool = True,
    quiet: bool = False
) -> dict[str, Any] | None:
    """
    一站式处理微信公众号文章

    Args:
        url: 微信公众号文章链接
        api_token: MinerU API Token
        output_dir: 输出基础目录
        show_progress: 是否显示进度条
        quiet: 是否静默模式（只输出错误信息）

    Returns:
        dict: 包含所有输出路径的结果

    输出目录结构:
        output/
        └── {文章标题}/
            ├── downloaded_images/     ← 原始下载的图片
            │   ├── 001.jpg
            │   ├── 002.png
            │   └── ...
            ├── converted/             ← MinerU 转换结果
            │   ├── converted.md       ← 合并后的 Markdown
            │   └── images/            ← 从识别结果提取的图片
            │       ├── 0000_xxx.png
            │       └── ...
            └── {文章标题}.zip          ← 打包的完整结果
    """

    if not quiet:
        logger.info("=" * 60)
        logger.info("微信公众号文章 → Markdown 转换工具")
        logger.info("=" * 60)

    progress_state = {"last_percent": 0}
    with tqdm(total=2, desc="总进度", disable=not show_progress or quiet, unit="阶段") as pbar:
        def on_progress(message: str, percent: int) -> None:
            pbar.set_description(message)
            if progress_state["last_percent"] < 50 <= percent:
                pbar.update(1)
            if progress_state["last_percent"] < 100 <= percent:
                pbar.update(1)
                pbar.set_description("完成!")
            progress_state["last_percent"] = percent

        final_result = convert_wechat_article(
            url=url,
            api_token=api_token,
            output_dir=output_dir,
            progress_callback=on_progress
        )

    if not final_result:
        logger.error("处理失败")
        return None

    if not quiet:
        logger.info("全部完成！")
        logger.info(
            f"最终结果: 文章标题={final_result['title']}, 结果目录={final_result['result_dir']}, "
            f"原始图片={final_result['original_image_count']}张, Markdown={final_result['md_file']}, "
            f"提取图片={final_result['extracted_image_count']}张, ZIP={final_result['zip_file']}"
        )

    return final_result


# ============ 命令行入口 ============
def main() -> None:
    """命令行入口函数"""

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        prog='wemath2md',
        description='🚀 微信公众号数学文章转 Markdown 工具',
        epilog='示例: wemath2md https://mp.weixin.qq.com/s/xxxxx'
    )
    parser.add_argument(
        'url',
        nargs='?',  # 可选参数
        help='微信公众号文章链接'
    )
    parser.add_argument(
        '-o', '--output',
        default=cfg.default_output_dir,
        help=f'输出目录 (默认: {cfg.default_output_dir})'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='不显示进度条'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出模式（显示 DEBUG 级别日志）'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='静默模式（只输出错误信息）'
    )
    parser.add_argument(
        '-f', '--file',
        type=str,
        help='从文件读取多个 URL 进行批量处理（每行一个 URL）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式（只验证 URL，不实际处理）'
    )

    args = parser.parse_args()

    # 处理日志级别
    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    elif args.quiet:
        log_level = "ERROR"

    # 初始化日志系统
    setup_logger(level=log_level, log_file="wemath2md.log")

    # 初始化临时目录清理（清理超过 24 小时的旧临时目录）
    temp_manager.initialize_cleanup(base_dir=Path.cwd(), max_age_hours=24)

    # 从配置读取 API Token（仅在实际转换时需要）
    API_TOKEN = get_mineru_token()

    # 收集所有 URL
    urls = []

    # 从文件读取
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith('http'):
                        urls.append(line)
            if not urls:
                logger.error(f"文件 '{args.file}' 中未找到有效的 URL")
                sys.exit(1)
            logger.info(f"从文件读取了 {len(urls)} 个 URL")
        except FileNotFoundError:
            logger.error(f"文件不存在: {args.file}")
            sys.exit(1)

    # 从命令行参数
    if args.url:
        urls.append(args.url)

    # 如果没有 URL，进入交互模式
    if not urls:
        logger.info("微信公众号文章 → Markdown 转换工具")
        url = input("请输入微信公众号文章链接: ").strip()

        if not url:
            logger.error("未输入链接")
            sys.exit(1)
        urls.append(url)

    # 验证所有 URL
    valid_urls = []
    for url in urls:
        if url.startswith('http'):
            valid_urls.append(url)
        else:
            logger.warning(f"跳过无效的链接: {url}")

    if not valid_urls:
        logger.error("没有有效的 URL 可处理")
        sys.exit(1)

    # 预览模式
    if args.dry_run:
        logger.info(f"预览模式：将处理 {len(valid_urls)} 个 URL")
        for i, url in enumerate(valid_urls, 1):
            logger.info(f"  {i}. {url}")
        sys.exit(0)

    if not API_TOKEN:
        logger.error("未找到 MINERU_API_TOKEN，请创建 .env 文件并设置 MINERU_API_TOKEN=your_token")
        sys.exit(1)

    # 验证配置
    config_check = validate_config()
    if not config_check['valid']:
        for error in config_check['errors']:
            logger.error(error)
        sys.exit(1)

    # 批量处理
    success_count = 0
    failure_count = 0

    for i, url in enumerate(valid_urls, 1):
        if len(valid_urls) > 1 and not args.quiet:
            logger.info(f"\n{'='*60}")
            logger.info(f"处理第 {i}/{len(valid_urls)} 个文章")
            logger.info(f"{'='*60}\n")

        result = process_wechat_article(
            url=url,
            api_token=API_TOKEN,
            output_dir=args.output,
            show_progress=not args.no_progress,
            quiet=args.quiet
        )

        if result:
            success_count += 1
        else:
            failure_count += 1

    # 批量处理总结
    if len(valid_urls) > 1 and not args.quiet:
        logger.info(f"\n{'='*60}")
        logger.info(f"批量处理完成！")
        logger.info(f"成功: {success_count}, 失败: {failure_count}")
        logger.info(f"{'='*60}")

    sys.exit(0 if failure_count == 0 else 1)


if __name__ == "__main__":
    main()
