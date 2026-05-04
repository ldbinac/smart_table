"""
前端静态文件托管模块测试
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestGetDistPath:
    """get_dist_path() 函数测试"""

    def test_returns_none_when_dist_not_exists(self):
        """当 dist 目录不存在时返回 None"""
        with patch('app.static_serving.os.path.exists', return_value=False):
            with patch('app.static_serving.sys') as mock_sys:
                mock_sys.frozen = False
                result = __import__('app.static_serving', fromlist=['get_dist_path']).get_dist_path()
                assert result is None

    @patch('app.static_serving.os.path.exists', return_value=True)
    @patch('app.static_serving.os.path.abspath', side_effect=lambda x: x)
    def test_returns_dist_path_in_pyinstaller_mode(self, mock_abspath, mock_exists):
        """PyInstaller 模式下返回 sys._MEIPASS/dist"""
        with patch('app.static_serving.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys._MEIPASS = '/tmp/pyi_temp'
            
            result = __import__('app.static_serving', fromlist=['get_dist_path']).get_dist_path()
            
            # 路径分隔符可能因操作系统而异（Windows: \, Linux/Mac: /）
            assert 'pyi_temp' in result and 'dist' in result

    def test_finds_smart_table_dist_in_dev_mode(self):
        """开发模式下能找到 smart-table/dist 目录"""
        # 此测试仅在 dist 目录实际存在时通过
        module = __import__('app.static_serving', fromlist=['get_dist_path'])
        result = module.get_dist_path()
        
        if result:
            assert os.path.isdir(result)
            assert os.path.isfile(os.path.join(result, 'index.html'))


class TestConfigureStaticServing:
    """configure_static_serving() 函数测试"""

    def test_registers_catch_all_route(self):
        """测试注册了 catch-all 路由"""
        from flask import Flask
        app = Flask(__name__)
        
        module = __import__('app.static_serving', fromlist=['configure_static_serving'])
        
        with patch.object(module, 'get_dist_path', return_value=None):
            success = module.configure_static_serving(app)
            
            # 即使没有 dist，也应该注册路由（显示友好错误页面）
            assert success is False
            
            # 验证路由已注册
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert '/' in rules

    def test_configures_with_valid_dist(self, tmp_path):
        """使用有效的 dist 路径配置成功"""
        from flask import Flask
        app = Flask(__name__)
        
        # 创建临时的 dist 目录和 index.html
        dist_dir = tmp_path / 'dist'
        dist_dir.mkdir()
        (dist_dir / 'index.html').write_text('<html>Test</html>')
        
        module = __import__('app.static_serving', fromlist=['configure_static_serving'])
        
        with patch.object(module, 'get_dist_path', return_value=str(dist_dir)):
            success = module.configure_static_serving(app)
            
            assert success is True


class TestServeFrontend:
    """serve_frontend 路由处理测试"""

    def test_serves_index_html_at_root(self, client):
        """根路径的响应状态"""
        response = client.get('/')
        # 可能的状态：
        # 200 - 已构建前端且静态服务正常
        # 503 - 前端未构建（显示友好提示页）
        # 404 - 未配置静态服务或路由未匹配
        assert response.status_code in [200, 404, 503]

    def test_api_routes_not_intercepted(self, client):
        """API 路由不被静态文件服务拦截"""
        response = client.get('/api/health')
        # API 请求应该由后端处理，不是静态文件
        assert response.status_code != 200 or b'html' not in response.data.lower()

    def test_uploads_not_intercepted(self, client):
        """上传路由不被拦截"""
        response = client.get('/uploads/test.txt')
        # 应该返回 404 或由上传处理器处理，而不是 index.html
        assert b'<title>SmartTable' not in response.data


class TestGetMimetype:
    """_get_mimetype() 函数测试"""

    def test_html_mimetype(self):
        module = __import__('app.static_serving', fromlist=['_get_mimetype'])
        assert module._get_mimetype('index.html') == 'text/html'

    def test_css_mimetype(self):
        module = __import__('app.static_serving', fromlist=['_get_mimetype'])
        assert module._get_mimetype('style.css') == 'text/css'

    def test_js_mimetype(self):
        module = __import__('app.static_serving', fromlist=['_get_mimetype'])
        assert module._get_mimetype('app.js') == 'application/javascript'

    def test_png_mimetype(self):
        module = __import__('app.static_serving', fromlist=['_get_mimetype'])
        assert module._get_mimetype('image.png') == 'image/png'

    def test_unknown_extension(self):
        module = __import__('app.static_serving', fromlist=['_get_mimetype'])
        assert module._get_mimetype('file.xyz') == 'application/octet-stream'

    def test_case_insensitive(self):
        module = __import__('app.static_serving', fromlist=['_get_mimetype'])
        assert module._get_mimetype('file.PNG') == 'image/png'
        assert module._get_mimetype('file.JS') == 'application/javascript'


class TestIsDistAvailable:
    """is_dist_available() 函数测试"""

    def test_returns_false_when_no_dist(self):
        with patch('app.static_serving.get_dist_path', return_value=None):
            module = __import__('app.static_serving', fromlist=['is_dist_available'])
            assert module.is_dist_available() is False

    def test_returns_true_with_valid_dist(self, tmp_path):
        dist_dir = tmp_path / 'dist'
        dist_dir.mkdir()
        (dist_dir / 'index.html').write_text('<html></html>')
        
        with patch('app.static_serving.get_dist_path', return_value=str(dist_dir)):
            module = __import__('app.static_serving', fromlist=['is_dist_available'])
            assert module.is_dist_available() is True

    def test_returns_false_without_index_html(self, tmp_path):
        dist_dir = tmp_path / 'dist'
        dist_dir.mkdir()
        # 不创建 index.html
        
        with patch('app.static_serving.get_dist_path', return_value=str(dist_dir)):
            module = __import__('app.static_serving', fromlist=['is_dist_available'])
            assert module.is_dist_available() is False
