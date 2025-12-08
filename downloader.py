import requests
from bs4 import BeautifulSoup
import os
import time
import re
from pathlib import Path

class WechatImageDownloader:
    def __init__(self, output_dir="output"):
        """
        初始化下载器
        
        Args:
            output_dir: 基础输出目录，默认为 "output"
        """
        self.output_dir = Path(output_dir)
        self.article_title = None
        self.result_dir = None  # 最终结果目录（以标题命名）
        self.images_dir = None  # 图片保存目录
        
        # 伪装成浏览器，防止反爬
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def get_article_content(self, url):
        """获取网页HTML内容"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"❌ 请求文章失败: {e}")
            return None
    
    def extract_title(self, html_content):
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
            if len(title) > 50:
                title = title[:50]
        
        return title or f"article_{int(time.time())}"
    
    def setup_directories(self, title):
        """根据标题设置目录结构"""
        self.article_title = title
        
        # 创建结果目录: output/{标题}/
        self.result_dir = self.output_dir / title
        self.result_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建图片子目录: output/{标题}/downloaded_images/
        self.images_dir = self.result_dir / "downloaded_images"
        self.images_dir.mkdir(exist_ok=True)
        
        print(f"📁 结果目录: {self.result_dir}")
        return self.result_dir

    def extract_images(self, html_content):
        """从HTML中提取所有图片链接"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 公众号正文通常在 id="img-content" 或 class="rich_media_content" 中
        content = soup.find(id="img-content")
        if not content:
            content = soup.find(class_="rich_media_content")
            
        if not content:
            print("⚠️ 未找到正文内容")
            return []

        images = []
        # 微信公众号图片的真实链接通常在 data-src 中
        for img in content.find_all('img'):
            src = img.get('data-src')
            if src:
                # 过滤掉一些图标或无效图片（可选）
                images.append(src)
                
        return images

    def download_images(self, img_urls):
        """下载图片列表"""
        if self.images_dir is None:
            raise Exception("请先调用 setup_directories() 设置目录")
        
        saved_files = []
        print(f"🔍 找到 {len(img_urls)} 张图片，准备下载...")
        
        for index, url in enumerate(img_urls):
            try:
                # 获取图片格式
                fmt = "jpg" # 默认为jpg
                if "fmt=" in url:
                    fmt_match = re.search(r'fmt=([a-zA-Z]+)', url)
                    if fmt_match:
                        fmt = fmt_match.group(1)
                
                # 构造文件名：001.jpg, 002.png ...
                filename = f"{index+1:03d}.{fmt}"
                filepath = self.images_dir / filename
                
                # 下载
                img_resp = requests.get(url, headers=self.headers)
                with open(filepath, 'wb') as f:
                    f.write(img_resp.content)
                
                print(f"✅ 已下载 [{index+1}/{len(img_urls)}]: {filename}")
                saved_files.append(str(filepath))
                
                # 礼貌性延时
                time.sleep(0.5) 
                
            except Exception as e:
                print(f"❌ 下载第 {index+1} 张图片失败: {e}")
        
        return saved_files
    
    def download_from_url(self, url):
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
        print(f"🔗 正在获取文章: {url}")
        
        # 1. 获取 HTML
        html = self.get_article_content(url)
        if not html:
            return None
        
        # 2. 提取标题
        title = self.extract_title(html)
        print(f"📰 文章标题: {title}")
        
        # 3. 设置目录
        self.setup_directories(title)
        
        # 4. 提取并下载图片
        img_urls = self.extract_images(html)
        saved_files = self.download_images(img_urls)
        
        print(f"\n✅ 下载完成！共 {len(saved_files)} 张图片")
        print(f"📁 保存位置: {self.images_dir}")
        
        return {
            'title': title,
            'result_dir': str(self.result_dir),
            'images_dir': str(self.images_dir),
            'images': saved_files
        }


# --- 测试代码 ---
if __name__ == "__main__":
    # 这里换成一个真实的公众号文章链接进行测试
    test_url = "https://mp.weixin.qq.com/s/0FKXBV81FzHcd4QcHTVvHg" 
    
    if "你的测试文章链接" in test_url:
        print("⚠️ 请先替换代码底部的 test_url 为真实的公众号文章链接！")
    else:
        downloader = WechatImageDownloader(output_dir="output")
        result = downloader.download_from_url(test_url)
        
        if result:
            print(f"\n📊 下载结果:")
            print(f"   标题: {result['title']}")
            print(f"   结果目录: {result['result_dir']}")
            print(f"   图片目录: {result['images_dir']}")
            print(f"   图片数量: {len(result['images'])}")
