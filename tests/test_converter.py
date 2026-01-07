# tests/test_converter.py
"""
转换器单元测试
测试 MinerUConverter 类的核心方法
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import zipfile
import io

from mineru_converter import MinerUConverter, ConversionState


class TestMinerUConverter:
    """转换器测试类"""

    def test_init_with_token(self):
        """测试使用提供的 token 初始化"""
        converter = MinerUConverter(api_token="test_token")
        assert converter.token == "test_token"
        assert converter.base_url == "https://mineru.net/api/v4"
        assert "Authorization" in converter.headers

    @patch('mineru_converter.cfg')
    def test_init_without_token(self, mock_cfg):
        """测试从配置读取 token"""
        mock_cfg.api_token = "config_token"
        mock_cfg.base_url = "https://test.api"

        converter = MinerUConverter()
        assert converter.token == "config_token"
        assert converter.base_url == "https://test.api"

    @patch('mineru_converter.cfg')
    def test_init_config_values(self, mock_cfg):
        """测试配置值被正确读取"""
        mock_cfg.api_token = "test_token"
        mock_cfg.base_url = "https://custom.api"
        mock_cfg.retry = Mock()

        converter = MinerUConverter()
        assert converter.base_url == "https://custom.api"
        assert converter._retry_config == mock_cfg.retry

    @patch.object(MinerUConverter, '_api_post')
    def test_apply_upload_urls_success(self, mock_post, mock_mineru_response):
        """测试申请上传链接成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_mineru_response
        mock_post.return_value = mock_response

        converter = MinerUConverter(api_token="test_token")
        batch_id, urls = converter.apply_upload_urls(["001.jpg", "002.jpg"])

        assert batch_id == "test_batch_123"
        assert len(urls) == 2
        assert urls[0] == "https://upload.mineru.net/file1"

    @patch.object(MinerUConverter, '_api_post')
    def test_apply_upload_urls_api_error(self, mock_post):
        """测试 API 返回错误"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": -1, "message": "API Error"}
        mock_post.return_value = mock_response

        converter = MinerUConverter(api_token="test_token")

        with pytest.raises(Exception, match="申请上传链接失败"):
            converter.apply_upload_urls(["001.jpg"])

    @patch.object(MinerUConverter, '_api_post')
    def test_apply_upload_urls_http_error(self, mock_post):
        """测试 HTTP 错误"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        converter = MinerUConverter(api_token="test_token")

        with pytest.raises(Exception, match="API 请求失败"):
            converter.apply_upload_urls(["001.jpg"])

    @patch.object(MinerUConverter, '_api_get')
    def test_wait_for_result_success(self, mock_get, mock_mineru_result):
        """测试等待转换成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_mineru_result
        mock_get.return_value = mock_response

        converter = MinerUConverter(api_token="test_token")
        result = converter.wait_for_result("test_batch")

        assert len(result) == 2
        assert result[0]['state'] == ConversionState.DONE
        assert result[1]['state'] == ConversionState.DONE

    @patch.object(MinerUConverter, '_api_get')
    def test_wait_for_result_partial_failure(self, mock_get):
        """测试部分文件转换失败"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "extract_result": [
                    {
                        "file_name": "001.jpg",
                        "state": ConversionState.DONE,
                        "full_zip_url": "https://result.zip"
                    },
                    {
                        "file_name": "002.jpg",
                        "state": ConversionState.FAILED,
                        "err_msg": "OCR failed"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        converter = MinerUConverter(api_token="test_token")
        result = converter.wait_for_result("test_batch")

        assert len(result) == 2
        assert result[0]['state'] == ConversionState.DONE
        assert result[1]['state'] == ConversionState.FAILED

    @patch.object(MinerUConverter, '_http_get')
    @patch('mineru_converter.zipfile.ZipFile')
    def test_download_and_extract_zip_success(self, mock_zipfile, mock_get, mock_zip_content):
        """测试下载并解压 ZIP 成功"""
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_zip_content
        mock_get.return_value = mock_response

        # Mock ZIP 文件
        mock_zip = MagicMock()
        mock_zip.__enter__ = Mock(return_value=mock_zip)
        mock_zip.__exit__ = Mock(return_value=False)
        mock_zip.namelist.return_value = ['full.md', 'images/001_test.png']

        # Mock 读取 markdown
        mock_zip.read.return_value = b"# Test\n\n![img](images/001_test.png)"
        mock_zipfile.return_value = mock_zip

        # Mock 文件写入
        with patch('builtins.open', MagicMock()):
            converter = MinerUConverter(api_token="test_token")
            from pathlib import Path
            md, count = converter.download_and_extract_zip(
                "https://test.zip",
                "test.jpg",
                Path("/tmp/test"),
                0
            )

        assert md is not None
        assert "images/0000_001_test.png" in md

    def test_rewrite_image_paths(self):
        """测试图片路径重写"""
        converter = MinerUConverter(api_token="test_token")

        md_content = """
# 测试

![图片1](images/001.png)

![图片2](images/002.jpg)

[普通链接](https://example.com)
"""

        result = converter._rewrite_image_paths(md_content, 3)

        assert "images/0003_001.png" in result
        assert "images/0003_002.jpg" in result
        assert "[普通链接](https://example.com)" in result

    def test_rewrite_image_paths_non_images(self):
        """测试不处理非 images 路径"""
        converter = MinerUConverter(api_token="test_token")

        md_content = """
![外部图片](https://example.com/image.png)

![本地图片](other/path/image.jpg)
"""

        result = converter._rewrite_image_paths(md_content, 1)

        # 外部链接不应被修改
        assert "![外部图片](https://example.com/image.png)" in result
        assert "![本地图片](other/path/image.jpg)" in result


class TestConverterValidation:
    """验证测试"""

    def test_empty_file_list(self, temp_output_dir):
        """测试空文件列表"""
        from pathlib import Path

        converter = MinerUConverter(api_token="test_token")
        result = converter.convert_images(
            temp_output_dir,
            output_name="test"
        )

        # 应该返回 None 或警告
        assert result is None

    def test_invalid_image_dir(self):
        """测试不存在的图片目录"""
        converter = MinerUConverter(api_token="test_token")

        with pytest.raises(Exception):
            converter.convert_images("/nonexistent/path")
