# tests/test_downloader.py
"""
下载器单元测试
测试 WechatImageDownloader 类的核心方法
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from downloader import WechatImageDownloader


class TestWechatImageDownloader:
    """下载器测试类"""

    def test_init_default_output_dir(self):
        """测试默认初始化"""
        downloader = WechatImageDownloader()
        assert downloader.output_dir.name == "output"
        assert downloader.article_title is None
        assert downloader.result_dir is None
        assert downloader.images_dir is None
        assert "User-Agent" in downloader.headers

    def test_init_custom_output_dir(self, temp_output_dir):
        """测试自定义输出目录"""
        downloader = WechatImageDownloader(output_dir=temp_output_dir)
        assert str(downloader.output_dir) == temp_output_dir

    def test_extract_title_with_og_title(self, sample_html):
        """测试从 og:title 提取标题"""
        downloader = WechatImageDownloader()
        title = downloader.extract_title(sample_html)
        assert title == "测试文章标题"

    def test_extract_title_no_title(self, sample_html_no_title):
        """测试没有标题时使用默认标题"""
        downloader = WechatImageDownloader()
        title = downloader.extract_title(sample_html_no_title)
        assert title.startswith("article_")

    def test_extract_title_special_characters(self, sample_html_complex_title):
        """测试标题中的特殊字符被清理"""
        downloader = WechatImageDownloader()
        title = downloader.extract_title(sample_html_complex_title)
        # 不应包含非法字符
        assert "/" not in title
        assert "\\" not in title
        assert ":" not in title
        assert '"' not in title
        # 应该有下划线替换
        assert "_" in title

    def test_extract_title_too_long(self):
        """测试过长标题被截断"""
        long_title = "a" * 100
        html = f'<html><head><title>{long_title}</title></head></html>'
        downloader = WechatImageDownloader()
        title = downloader.extract_title(html)
        assert len(title) <= 50

    def test_setup_directories(self, temp_output_dir):
        """测试目录设置"""
        downloader = WechatImageDownloader(output_dir=temp_output_dir)
        result_dir = downloader.setup_directories("测试标题")

        assert downloader.article_title == "测试标题"
        assert downloader.result_dir == downloader.output_dir / "测试标题"
        assert downloader.images_dir == downloader.result_dir / "downloaded_images"
        assert result_dir.exists()
        assert downloader.images_dir.exists()

    def test_extract_images_from_html(self, sample_html):
        """测试从 HTML 提取图片链接"""
        downloader = WechatImageDownloader()
        images = downloader.extract_images(sample_html)

        assert len(images) == 3
        assert "https://mmbiz.qpic.cn/test1.jpg" in images
        assert "https://mmbiz.qpic.cn/test2.png" in images
        assert "https://mmbiz.qpic.cn/test3.webp" in images

    def test_extract_images_no_content(self):
        """测试没有内容时返回空列表"""
        html = '<html><body></body></html>'
        downloader = WechatImageDownloader()
        images = downloader.extract_images(html)
        assert images == []

    def test_extract_images_no_data_src(self):
        """测试没有 data-src 属性的图片"""
        html = '<html><body><div id="img-content"><img src="test.jpg" /></div></body></html>'
        downloader = WechatImageDownloader()
        images = downloader.extract_images(html)
        assert images == []

    @patch('downloader.requests.get')
    def test_get_article_content_success(self, mock_get):
        """测试成功获取文章内容"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>测试内容</body></html>"
        mock_get.return_value = mock_response

        downloader = WechatImageDownloader()
        content = downloader.get_article_content("https://example.com")

        assert content == "<html><body>测试内容</body></html>"
        mock_get.assert_called_once()

    @patch('downloader.requests.get')
    def test_get_article_content_failure(self, mock_get):
        """测试获取文章内容失败"""
        mock_get.side_effect = Exception("网络错误")

        downloader = WechatImageDownloader()
        content = downloader.get_article_content("https://example.com")

        assert content is None

    @patch('downloader.time.sleep')
    @patch.object(WechatImageDownloader, '_http_get')
    @patch('builtins.open', new_callable=MagicMock)
    def test_download_images(self, mock_open, mock_http_get, mock_sleep, temp_output_dir):
        """测试图片下载"""
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake image data'
        mock_http_get.return_value = mock_response

        # Mock 文件写入
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # 设置目录
        downloader = WechatImageDownloader(output_dir=temp_output_dir)
        downloader.setup_directories("test")

        # 下载图片
        urls = ["https://example.com/image1.jpg", "https://example.com/image2.png"]
        result = downloader.download_images(urls)

        assert len(result) == 2
        assert mock_http_get.call_count == 2
        assert mock_sleep.call_count == 2


class TestDownloaderIntegration:
    """集成测试（需要 mock 外部依赖）"""

    @patch.object(WechatImageDownloader, '_http_get')
    @patch.object(WechatImageDownloader, 'download_images')
    def test_download_from_url_flow(self, mock_download, mock_get, sample_html, temp_output_dir):
        """测试完整下载流程"""
        # Mock HTML 获取
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_get.return_value = mock_response

        # Mock 图片下载
        mock_download.return_value = ["/path/to/image1.jpg", "/path/to/image2.jpg"]

        downloader = WechatImageDownloader(output_dir=temp_output_dir)
        result = downloader.download_from_url("https://example.com/article")

        assert result is not None
        assert result['title'] == "测试文章标题"
        assert 'result_dir' in result
        assert 'images_dir' in result
        assert result['images'] == ["/path/to/image1.jpg", "/path/to/image2.jpg"]

    @patch.object(WechatImageDownloader, '_http_get')
    def test_download_from_url_failure(self, mock_get, temp_output_dir):
        """测试下载流程失败"""
        mock_get.return_value = None

        downloader = WechatImageDownloader(output_dir=temp_output_dir)
        result = downloader.download_from_url("https://example.com/article")

        assert result is None
