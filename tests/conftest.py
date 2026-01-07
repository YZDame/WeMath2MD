# conftest.py
"""
pytest 配置文件
提供共享的 fixtures 和测试配置
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入状态枚举用于测试
from mineru_converter import ConversionState
from web_app import TaskState


@pytest.fixture
def temp_output_dir():
    """临时输出目录 fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_env_token():
    """模拟环境变量中的 API Token"""
    with patch.dict(os.environ, {'MINERU_API_TOKEN': 'test_token_12345'}):
        yield 'test_token_12345'


@pytest.fixture
def sample_html():
    """示例 HTML 内容（微信公众号文章）"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="测试文章标题">
        <title>测试文章标题</title>
    </head>
    <body>
        <div id="img-content" class="rich_media_content">
            <p>这是一段测试文字</p>
            <img data-src="https://mmbiz.qpic.cn/test1.jpg" />
            <img data-src="https://mmbiz.qpic.cn/test2.png" />
            <img data-src="https://mmbiz.qpic.cn/test3.webp" />
        </div>
    </body>
    </html>
    '''


@pytest.fixture
def sample_html_no_title():
    """没有标题的示例 HTML"""
    return '''
    <!DOCTYPE html>
    <html>
    <body>
        <div id="img-content">
            <img data-src="https://mmbiz.qpic.cn/test.jpg" />
        </div>
    </body>
    </html>
    '''


@pytest.fixture
def sample_html_complex_title():
    """包含特殊字符的标题"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="标题包含/特殊\\字符:哪些是\"非法\"的?">
    </head>
    <body>
        <div id="img-content">
            <p>内容</p>
        </div>
    </body>
    </html>
    '''


@pytest.fixture
def mock_mineru_response():
    """模拟 MinerU API 响应"""
    return {
        "code": 0,
        "data": {
            "batch_id": "test_batch_123",
            "file_urls": [
                "https://upload.mineru.net/file1",
                "https://upload.mineru.net/file2"
            ]
        }
    }


@pytest.fixture
def mock_mineru_result():
    """模拟 MinerU 转换结果"""
    return {
        "code": 0,
        "data": {
            "extract_result": [
                {
                    "file_name": "001.jpg",
                    "data_id": "file_0001_1234567890",
                    "state": ConversionState.DONE,
                    "full_zip_url": "https://result.mineru.net/001.zip"
                },
                {
                    "file_name": "002.jpg",
                    "data_id": "file_0002_1234567890",
                    "state": ConversionState.DONE,
                    "full_zip_url": "https://result.mineru.net/002.zip"
                }
            ]
        }
    }


@pytest.fixture
def mock_zip_content():
    """模拟 ZIP 包内容"""
    import zipfile
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 添加 markdown 文件
        md_content = """# 测试内容

这是一段测试的 **Markdown** 内容。

![图片说明](images/001_test.png)
"""
        zf.writestr('full.md', md_content)

        # 添加图片
        img_content = b'fake image data'
        zf.writestr('images/001_test.png', img_content)

    zip_buffer.seek(0)
    return zip_buffer.read()
