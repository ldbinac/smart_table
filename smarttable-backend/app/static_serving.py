"""
前端静态文件托管模块
用于在 PyInstaller 打包后的单文件可执行程序中托管 Vue 前端资源

功能：
- 自动检测 PyInstaller 打包环境或开发环境
- 提供 Vue SPA 的路由回退支持（history 模式）
- 正确设置 MIME 类型以优化浏览器缓存
- 支持前端资源的热重载（开发环境）
"""

import os
import sys


def get_dist_path():
    """
    获取前端构建产物的目录路径
    
    优先级：
    1. PyInstaller 打包后的临时目录 (sys._MEIPASS)
    2. 开发环境：backend 目录的上级 dist（smart-table/dist）
    
    Returns:
        str: dist 目录的绝对路径，如果不存在则返回 None
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境：相对于 backend 目录
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    dist_path = os.path.join(base_path, 'dist')

    # 如果开发环境的 dist 不存在，尝试项目根目录下的 smart-table/dist
    if not os.path.exists(dist_path) and not getattr(sys, 'frozen', False):
        alternative_path = os.path.join(base_path, '..', 'smart-table', 'dist')
        if os.path.exists(alternative_path):
            dist_path = os.path.abspath(alternative_path)

    if os.path.exists(dist_path):
        return os.path.abspath(dist_path)
    
    return None


def configure_static_serving(app):
    """
    配置 Flask 应用以托管前端静态文件
    
    此函数会注册一个 catch-all 路由，用于：
    - 提供前端构建产物（HTML/CSS/JS/图片等）
    - 处理 Vue Router 的 history 模式回退到 index.html
    - 将 API 请求 (/api/*) 和上传请求 (/uploads/*) 转发给后端路由处理
    
    Args:
        app: Flask 应用实例
        
    Returns:
        bool: 是否成功配置（如果 dist 目录不存在则返回 False）
    """
    from flask import send_from_directory, abort

    dist_path = get_dist_path()
    
    if not dist_path:
        print('[Static Serving] ⚠️ Warning: Frontend dist directory not found!')
        print('[Static Serving]   Please run "npm run build" in smart-table/ first.')
        
        # 注册一个友好的 404 页面
        @app.route('/')
        @app.route('/<path:path>')
        def frontend_not_built():
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>SmartTable - Frontend Not Built</title>
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex; justify-content: center; align-items: center;
                        min-height: 100vh; margin: 0; background: #f5f5f5;
                        color: #333;
                    }
                    .container { 
                        max-width: 600px; padding: 40px; background: white;
                        border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    h1 { color: #e74c3c; margin-bottom: 20px; }
                    code { 
                        background: #f4f4f4; padding: 2px 6px; border-radius: 3px;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⚠️ Frontend Not Built</h1>
                    <p>The frontend application has not been built yet.</p>
                    <p>To fix this, run the following command:</p>
                    <pre><code>cd smart-table && npm install && npm run build</code></pre>
                    <p>Then restart the server.</p>
                </div>
            </body>
            </html>
            ''', 503
        
        return False

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """处理所有非 API 请求，返回前端静态资源"""
        
        # API 请求由其他路由处理，不拦截
        if path.startswith('api/') or path.startswith('uploads'):
            return None  # 让 Flask 继续匹配其他路由

        # 尝试查找请求的静态文件
        file_path = os.path.join(dist_path, path)
        if path and os.path.isfile(file_path):
            mimetype = _get_mimetype(path)
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            return send_from_directory(directory, filename, mimetype=mimetype)

        # Vue Router history 模式：对于所有未匹配的路由，回退到 index.html
        index_html = os.path.join(dist_path, 'index.html')
        if os.path.isfile(index_html):
            response = send_from_directory(dist_path, 'index.html', mimetype='text/html')
            
            # 添加安全头（防止点击劫持等攻击）
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            
            return response

        # 都找不到则返回 404
        abort(404)

    print(f'[Static Serving] ✓ Frontend dist path: {dist_path}')
    print(f'[Static Serving] ✓ Static file serving configured')
    return True


def _get_mimetype(filepath):
    """
    根据文件扩展名获取 MIME 类型
    
    Args:
        filepath: 文件路径
        
    Returns:
        str: MIME 类型字符串
    """
    ext = os.path.splitext(filepath)[1].lower()
    
    mime_types = {
        # HTML
        '.html': 'text/html',
        '.htm': 'text/html',
        
        # CSS
        '.css': 'text/css',
        
        # JavaScript
        '.js': 'application/javascript',
        '.mjs': 'application/javascript',
        '.cjs': 'application/javascript',
        
        # JSON
        '.json': 'application/json',
        '.map': 'application/json',
        
        # 图片
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.bmp': 'image/bmp',
        
        # 字体
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.otf': 'font/otf',
        '.eot': 'application/vnd.ms-fontobject',
        
        # 音频/视频
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        
        # 文档
        '.pdf': 'application/pdf',
        '.xml': 'application/xml',
        
        # 其他常见类型
        '.txt': 'text/plain',
        '.wasm': 'application/wasm',
    }
    
    return mime_types.get(ext, 'application/octet-stream')


def is_dist_available():
    """
    检查前端构建产物是否可用
    
    Returns:
        bool: 如果 dist 目录存在且包含 index.html 则返回 True
    """
    dist_path = get_dist_path()
    if not dist_path:
        return False
    
    index_html = os.path.join(dist_path, 'index.html')
    return os.path.isfile(index_html)
