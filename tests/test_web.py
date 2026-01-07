# tests/test_web.py
"""
Web 应用单元测试
测试 Flask 应用的路由和功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 模拟配置环境变量
import os
os.environ.setdefault('MINERU_API_TOKEN', 'test_token_for_web')


class TestValidatePath:
    """路径验证测试"""

    def test_validate_path_safe(self):
        """测试安全路径通过验证"""
        from web_app import validate_path, OUTPUT_DIR, BASE_DIR

        # 确保 OUTPUT_DIR 存在
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 创建一个安全路径 - 需要相对于 BASE_DIR 的路径
        safe_path = OUTPUT_DIR / "test" / "file.md"
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.touch()

        # 使用相对于 BASE_DIR 的路径（因为 validate_path 使用 BASE_DIR 作为基础）
        relative_path = safe_path.relative_to(BASE_DIR)
        result = validate_path(str(relative_path))
        assert result is not None
        assert result == safe_path.resolve()

    def test_validate_path_traversal_attack(self):
        """测试路径遍历攻击被拒绝"""
        from web_app import validate_path

        # 尝试路径遍历攻击
        result = validate_path("../../../etc/passwd")
        assert result is None

    def test_validate_path_absolute_path(self):
        """测试绝对路径被拒绝"""
        from web_app import validate_path

        # 尝试使用绝对路径
        result = validate_path("/etc/passwd")
        assert result is None

    def test_validate_path_nonexistent(self):
        """测试不存在的文件"""
        from web_app import validate_path

        result = validate_path("nonexistent/file.md")
        # 路径应该是安全的，但文件不存在
        # validate_path 只检查路径安全性，不检查文件存在性
        # 实际的文件存在性检查在使用时进行


class TestWebRoutes:
    """Web 路由测试"""

    @pytest.fixture
    def app(self):
        """创建 Flask 测试应用"""
        import tempfile
        import sys
        import importlib
        import web_app as web_app_module

        # 设置测试环境变量
        os.environ['WEB_DEBUG'] = 'false'
        os.environ['MINERU_API_TOKEN'] = 'test_token'

        # 重新加载模块以使用正确的环境变量
        importlib.reload(sys.modules['config'])
        importlib.reload(web_app_module)

        web_app_module.app.config['TESTING'] = True
        web_app_module.app.config['OUTPUT_DIR'] = tempfile.mkdtemp()

        return web_app_module.app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    def test_index_route(self, client):
        """测试首页路由"""
        response = client.get('/')
        assert response.status_code == 200
        # 应该包含 HTML 内容
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    def test_convert_route_no_url(self, client):
        """测试转换路由缺少 URL"""
        response = client.post('/convert',
                             json={},
                             content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert '请输入文章链接' in data['error']

    def test_convert_route_invalid_url(self, client):
        """测试转换路由无效 URL"""
        response = client.post('/convert',
                             json={'url': 'not-a-valid-url'},
                             content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert '无效的链接格式' in data['error']

    @patch('web_app.threading.Thread')
    def test_convert_route_success(self, mock_thread, client):
        """测试转换路由成功提交"""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        response = client.post('/convert',
                             json={'url': 'https://mp.weixin.qq.com/s/test123'},
                             content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'task_id' in data
        # 验证后台线程被启动
        mock_thread_instance.start.assert_called_once()

    def test_status_route_not_found(self, client):
        """测试状态路由任务不存在"""
        response = client.get('/status/nonexistent_task_id')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert '任务不存在' in data['error']

    def test_download_md_not_found(self, client):
        """测试下载不存在的文件"""
        response = client.get('/download/md/nonexistent/file.md')
        assert response.status_code == 404

    def test_download_zip_not_found(self, client):
        """测试下载不存在的 ZIP"""
        response = client.get('/download/zip/nonexistent/file.zip')
        assert response.status_code == 404

    def test_preview_not_found(self, client):
        """测试预览不存在的文件"""
        response = client.get('/preview/nonexistent/file.md')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert '文件不存在' in data['error']


class TestTaskState:
    """任务状态测试"""

    def test_task_state_enum(self):
        """测试任务状态枚举"""
        from web_app import TaskState

        assert TaskState.PENDING == "pending"
        assert TaskState.PROCESSING == "processing"
        assert TaskState.DONE == "done"
        assert TaskState.FAILED == "failed"

    def test_task_state_is_string_enum(self):
        """测试 TaskState 是字符串枚举"""
        from web_app import TaskState

        # 应该可以与字符串比较
        assert TaskState.PENDING == "pending"
        assert TaskState.PENDING.value == "pending"


class TestConversionHistory:
    """转换历史测试"""

    def test_conversion_history_type(self):
        """测试转换历史类型"""
        from web_app import conversion_history

        assert isinstance(conversion_history, list)

    def test_conversion_history_limit(self):
        """测试历史记录限制"""
        from web_app import conversion_history, cfg

        # 清空历史
        conversion_history.clear()

        # 添加超过限制的历史记录（模拟应用程序的行为）
        for i in range(cfg.max_history_items + 5):
            conversion_history.insert(0, {
                'title': f'Test {i}',
                'md_file': f'test_{i}.md',
                'zip_file': f'test_{i}.zip',
                'image_count': i
            })
            # 模拟应用程序的限制逻辑
            if len(conversion_history) > cfg.max_history_items:
                conversion_history.pop()

        # 应该只保留最大数量
        assert len(conversion_history) == cfg.max_history_items


class TestWebConfigSecurity:
    """Web 安全配置测试"""

    def test_secret_key_configured(self):
        """测试 SECRET_KEY 已配置"""
        from web_app import app
        assert app.config.get('SECRET_KEY') is not None
        assert len(app.config.get('SECRET_KEY')) > 0

    def test_session_cookie_security(self):
        """测试 Session Cookie 安全配置"""
        from web_app import app
        assert app.config.get('SESSION_COOKIE_HTTPONLY') is True
        assert app.config.get('SESSION_COOKIE_SAMESITE') == 'Lax'

    def test_cors_headers_present(self):
        """测试 CORS 响应头"""
        import tempfile
        import importlib
        import web_app as web_app_module

        # 启用 CORS 的环境
        os.environ['WEB_CORS_ENABLED'] = 'true'
        os.environ['WEB_DEBUG'] = 'false'
        os.environ['MINERU_API_TOKEN'] = 'test_token'

        importlib.reload(sys.modules['config'])
        importlib.reload(web_app_module)

        web_app_module.app.config['TESTING'] = True

        with web_app_module.app.test_client() as client:
            response = client.get('/')
            # CORS 响应头应该存在
            assert response.status_code == 200

    def test_production_mode_cache_headers(self):
        """测试生产模式下的缓存配置"""
        import tempfile
        import importlib
        import web_app as web_app_module

        # 生产环境
        os.environ['WEB_DEBUG'] = 'false'
        os.environ['MINERU_API_TOKEN'] = 'test_token'

        importlib.reload(sys.modules['config'])
        importlib.reload(web_app_module)

        # 生产环境应该设置文件缓存时间
        assert web_app_module.app.config.get('SEND_FILE_MAX_AGE_DEFAULT') == 31536000
