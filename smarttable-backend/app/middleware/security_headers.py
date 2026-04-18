"""
安全响应头中间件
为所有 HTTP 响应添加安全相关的响应头
"""
from flask import current_app
from functools import wraps


def init_security_headers(app):
    """
    初始化安全响应头中间件
    
    Args:
        app: Flask 应用实例
    """
    @app.after_request
    def add_security_headers(response):
        """
        为所有响应添加安全响应头
        
        Args:
            response: Flask 响应对象
            
        Returns:
            添加了安全头的响应对象
        """
        # X-Content-Type-Options: 防止 MIME 类型嗅探
        # 告诉浏览器严格遵守 Content-Type 头，不进行嗅探
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options: 防止点击劫持
        # DENY: 完全禁止在 iframe 中嵌入
        # SAMEORIGIN: 只允许同源嵌入
        response.headers['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection: XSS 过滤器（现代浏览器已弃用，但仍建议保留）
        # 启用浏览器内置的 XSS 过滤器
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy: 控制 Referer 头的发送
        # strict-origin-when-cross-origin: 同源发送完整 Referer，跨域只发送源
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions-Policy: 控制浏览器功能访问
        # 禁用不需要的浏览器功能
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=()'
        )
        
        # Cache-Control: 控制缓存行为
        # 对于 API 响应，禁用缓存以保护敏感数据
        if response.content_type and 'application/json' in response.content_type:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        # Content-Security-Policy: 内容安全策略
        # 仅在生产环境配置完整的 CSP
        if not app.debug:
            # 生产环境的 CSP 配置
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob: https:",
                "font-src 'self' data:",
                "connect-src 'self' ws: wss:",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
            ]
            response.headers['Content-Security-Policy'] = '; '.join(csp_directives)
            
            # Strict-Transport-Security (HSTS): 强制使用 HTTPS
            # 仅在生产环境且使用 HTTPS 时启用
            # max-age=31536000: 1 年
            # includeSubDomains: 包含所有子域名
            # preload: 允许加入浏览器预加载列表
            if app.config.get('FORCE_HTTPS', False):
                response.headers['Strict-Transport-Security'] = (
                    'max-age=31536000; includeSubDomains; preload'
                )
        
        return response
    
    return app


def get_csp_header(nonce=None, report_uri=None):
    """
    生成 Content-Security-Policy 头
    
    Args:
        nonce: 可选的 nonce 值，用于内联脚本
        report_uri: 可选的违规报告 URI
        
    Returns:
        CSP 头字符串
    """
    script_src = "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
    if nonce:
        script_src += f" 'nonce-{nonce}'"
    
    directives = [
        "default-src 'self'",
        script_src,
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https:",
        "font-src 'self' data:",
        "connect-src 'self' ws: wss:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    
    if report_uri:
        directives.append(f"report-uri {report_uri}")
    
    return '; '.join(directives)
