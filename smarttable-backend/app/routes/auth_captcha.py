"""
认证验证码路由模块
提供登录和注册的验证码功能
"""
from flask import Blueprint, request
import base64

from app.utils.response import success_response, error_response
from app.utils.captcha import CaptchaService

auth_captcha_bp = Blueprint('auth_captcha', __name__)
auth_captcha_bp.strict_slashes = False


@auth_captcha_bp.route('/auth/captcha', methods=['GET'])
def get_auth_captcha() -> tuple:
    """
    获取登录/注册验证码（公开接口）
    
    Query Parameters:
        - key: 验证码标识（可选，用于区分不同场景）
    
    Returns:
        验证码图片（Base64编码）
    """
    # 获取客户端IP作为验证码key的一部分
    client_ip = request.remote_addr or 'unknown'
    key = request.args.get('key', 'default')
    token = f"auth:{key}:{client_ip}"
    
    try:
        # 生成验证码
        code, image_base64, mime_type = CaptchaService.generate_captcha(token)
        
        return success_response(
            data={
                'image': f'data:{mime_type};base64,{image_base64}',
                'expire': 300  # 5分钟有效期
            },
            message='验证码生成成功'
        )
    except Exception as e:
        return error_response(f'验证码生成失败: {str(e)}', 500)
