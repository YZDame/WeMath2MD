# main.py
"""
微信公众号文章图片转 Markdown 工具
整合 downloader 和 mineru_converter，一站式处理

使用方式:
    1. 命令行: wemath2md https://mp.weixin.qq.com/s/xxx
    2. 交互式: wemath2md (然后输入链接)
    3. Python: python main.py https://mp.weixin.qq.com/s/xxx
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from downloader import WechatImageDownloader
from mineru_converter import MinerUConverter

# 加载 .env 文件
load_dotenv()


def process_wechat_article(url, api_token, output_dir="output"):
    """
    一站式处理微信公众号文章
    
    Args:
        url: 微信公众号文章链接
        api_token: MinerU API Token
        output_dir: 输出基础目录
    
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
    
    print("=" * 60)
    print("🚀 微信公众号文章 → Markdown 转换工具")
    print("=" * 60)
    
    # ==================== 第一阶段：下载图片 ====================
    print("\n📥 【第一阶段】下载公众号图片\n")
    
    downloader = WechatImageDownloader(output_dir=output_dir)
    download_result = downloader.download_from_url(url)
    
    if not download_result:
        print("❌ 下载失败，程序终止")
        return None
    
    print(f"\n✅ 第一阶段完成！")
    print(f"   文章标题: {download_result['title']}")
    print(f"   下载图片: {len(download_result['images'])} 张")
    
    # ==================== 第二阶段：OCR 识别转换 ====================
    print("\n" + "=" * 60)
    print("\n🔄 【第二阶段】MinerU OCR 识别转换\n")
    
    converter = MinerUConverter(api_token=api_token)
    convert_result = converter.convert_images(
        image_dir=download_result['images_dir'],
        output_dir=download_result['result_dir'],
        output_name="converted"
    )
    
    if not convert_result:
        print("❌ 转换失败")
        return None
    
    # ==================== 完成 ====================
    print("\n" + "=" * 60)
    print("🎉 全部完成！")
    print("=" * 60)
    
    final_result = {
        'title': download_result['title'],
        'result_dir': download_result['result_dir'],
        'downloaded_images_dir': download_result['images_dir'],
        'converted_dir': convert_result['output_dir'],
        'md_file': convert_result['md_file'],
        'converted_images_dir': convert_result['images_dir'],
        'zip_file': convert_result['zip_file'],
        'original_image_count': len(download_result['images']),
        'extracted_image_count': convert_result['image_count']
    }
    
    print(f"\n📊 最终结果:")
    print(f"   📰 文章标题: {final_result['title']}")
    print(f"   📁 结果目录: {final_result['result_dir']}")
    print(f"   🖼️  原始图片: {final_result['original_image_count']} 张")
    print(f"   📄 Markdown: {final_result['md_file']}")
    print(f"   🖼️  提取图片: {final_result['extracted_image_count']} 张")
    print(f"   📦 ZIP 文件: {final_result['zip_file']}")
    
    return final_result


# ============ 命令行入口 ============
def main():
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
        default='output',
        help='输出目录 (默认: output)'
    )
    
    args = parser.parse_args()
    
    # 从环境变量读取 API Token
    API_TOKEN = os.getenv("MINERU_API_TOKEN")
    
    if not API_TOKEN:
        print("❌ 错误: 未找到 MINERU_API_TOKEN")
        print("   请创建 .env 文件并设置 MINERU_API_TOKEN=your_token")
        print("   或参考 .env.example 文件")
        sys.exit(1)
    
    # 获取文章链接
    url = args.url
    
    # 如果没有提供 URL，进入交互模式
    if not url:
        print("=" * 60)
        print("🚀 微信公众号文章 → Markdown 转换工具")
        print("=" * 60)
        print()
        url = input("📎 请输入微信公众号文章链接: ").strip()
        
        if not url:
            print("❌ 错误: 未输入链接")
            sys.exit(1)
    
    # 简单验证 URL
    if not url.startswith('http'):
        print(f"❌ 错误: 无效的链接 '{url}'")
        print("   链接应以 http:// 或 https:// 开头")
        sys.exit(1)
    
    # 开始处理
    result = process_wechat_article(
        url=url,
        api_token=API_TOKEN,
        output_dir=args.output
    )
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
