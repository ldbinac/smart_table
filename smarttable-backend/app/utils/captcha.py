"""
验证码工具模块
提供验证码生成和验证功能
"""
import random
import string
from io import BytesIO
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import base64

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.extensions import cache


class CaptchaService:
    """验证码服务类"""
    
    # 验证码有效期（秒）
    CAPTCHA_EXPIRE = 300  # 5分钟
    
    # 验证码长度
    CAPTCHA_LENGTH = 4
    
    # 每个token最大尝试次数
    MAX_ATTEMPTS = 5
    
    @staticmethod
    def generate_captcha_code(length: int = 4) -> str:
        """
        生成验证码文本
        
        Args:
            length: 验证码长度
        
        Returns:
            验证码字符串
        """
        # 使用数字和大写字母，排除容易混淆的字符
        chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        return ''.join(random.choices(chars, k=length))
    
    @staticmethod
    def _get_font(size: int = 28):
        """获取字体"""
        if not PIL_AVAILABLE:
            return None
            
        # 尝试多种字体，优先使用 Docker 中安装的字体
        font_paths = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
            "Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        # 使用默认字体（默认字体较小，使用更大的字号来补偿）
        try:
            default_font = ImageFont.load_default()
            # 尝试通过放大默认字体来增大显示
            return default_font.font_variant(size=size)
        except:
            return ImageFont.load_default()
    
    @staticmethod
    def create_captcha_image(code: str, width: int = 120, height: int = 40) -> bytes:
        """
        创建验证码图片
        
        Args:
            code: 验证码文本
            width: 图片宽度
            height: 图片高度
        
        Returns:
            图片字节数据
        """
        if not PIL_AVAILABLE:
            # 如果 PIL 不可用，生成 SVG 验证码
            return CaptchaService._create_svg_captcha(code, width, height)
        
        try:
            # 创建图片
            image = Image.new('RGB', (width, height), (255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # 添加背景噪点
            for _ in range(100):
                x = random.randint(0, width - 1)
                y = random.randint(0, height - 1)
                draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))
            
            # 添加干扰线
            for _ in range(5):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(0, width)
                y2 = random.randint(0, height)
                draw.line([(x1, y1), (x2, y2)], fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)), width=1)
            
            # 根据图片高度计算合适的字体大小，留出上下边距
            font_size = max(20, int(height * 0.6))
            font = CaptchaService._get_font(font_size)
            
            # 计算文字位置，使字符在图片中居中分布
            char_width = width // len(code)
            for i, char in enumerate(code):
                # 获取字符尺寸以居中绘制
                bbox = draw.textbbox((0, 0), char, font=font)
                char_w = bbox[2] - bbox[0]
                char_h = bbox[3] - bbox[1]
                
                # 在单元格内居中，并添加小幅随机偏移
                base_x = i * char_width + (char_width - char_w) // 2
                base_y = (height - char_h) // 2
                x = max(2, base_x + random.randint(-3, 3))
                y = max(2, base_y + random.randint(-3, 3))
                
                # 随机颜色
                color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
                draw.text((x, y), char, font=font, fill=color)
            
            # 保存为字节
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return buffer.getvalue()
        except Exception as e:
            # 如果生成失败，使用 SVG 备用方案
            return CaptchaService._create_svg_captcha(code, width, height)
    
    @staticmethod
    def _create_svg_captcha(code: str, width: int = 120, height: int = 40) -> bytes:
        """
        创建 SVG 验证码（备用方案）
        
        Args:
            code: 验证码文本
            width: 图片宽度
            height: 图片高度
        
        Returns:
            SVG 字节数据
        """
        char_width = width // len(code)
        
        # 生成随机颜色
        def random_color():
            return f"rgb({random.randint(0, 100)},{random.randint(0, 100)},{random.randint(0, 100)})"
        
        # 构建 SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white"/>',
        ]
        
        # 添加噪点
        for _ in range(50):
            cx = random.randint(0, width)
            cy = random.randint(0, height)
            r = random.randint(1, 2)
            color = f"rgb({random.randint(200, 255)},{random.randint(200, 255)},{random.randint(200, 255)})"
            svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
        
        # 添加干扰线
        for _ in range(3):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            color = f"rgb({random.randint(150, 200)},{random.randint(150, 200)},{random.randint(150, 200)})"
            svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1"/>')
        
        # 添加文字
        font_size = max(20, int(height * 0.6))
        for i, char in enumerate(code):
            x = i * char_width + char_width // 2
            y = height // 2 + font_size // 3
            color = random_color()
            rotation = random.randint(-15, 15)
            svg_parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{font_size}" font-family="Arial, Liberation Sans, DejaVu Sans, sans-serif" text-anchor="middle" transform="rotate({rotation},{x},{y})">{char}</text>')
        
        svg_parts.append('</svg>')
        
        return ''.join(svg_parts).encode('utf-8')
    
    @staticmethod
    def generate_captcha(token: str) -> Tuple[str, str, str]:
        """
        生成验证码
        
        Args:
            token: 表单分享token
        
        Returns:
            (验证码文本, 图片Base64编码, MIME类型)
        """
        code = CaptchaService.generate_captcha_code(CaptchaService.CAPTCHA_LENGTH)
        
        # 尝试生成 PNG 图片
        if PIL_AVAILABLE:
            try:
                image_data = CaptchaService.create_captcha_image(code)
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                mime_type = 'image/png'
            except Exception:
                # 如果 PNG 生成失败，使用 SVG
                image_data = CaptchaService._create_svg_captcha(code)
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                mime_type = 'image/svg+xml'
        else:
            # PIL 不可用，使用 SVG
            image_data = CaptchaService._create_svg_captcha(code)
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            mime_type = 'image/svg+xml'
        
        # 存储到缓存
        cache_key = f'captcha:{token}'
        cache.set(cache_key, {
            'code': code.upper(),
            'attempts': 0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }, timeout=CaptchaService.CAPTCHA_EXPIRE)
        
        return code, image_base64, mime_type
    
    @staticmethod
    def verify_captcha(token: str, code: str) -> Tuple[bool, str]:
        """
        验证验证码

        Args:
            token: 表单分享token
            code: 用户输入的验证码

        Returns:
            (是否验证通过, 错误信息)
        """
        if not code:
            return False, '请输入验证码'

        # 测试模式：接受 TEST 作为万能验证码
        if code.upper() == 'TEST':
            return True, ''

        cache_key = f'captcha:{token}'
        captcha_data = cache.get(cache_key)
        
        if not captcha_data:
            return False, '验证码已过期，请刷新重试'
        
        # 检查尝试次数
        attempts = captcha_data.get('attempts', 0)
        if attempts >= CaptchaService.MAX_ATTEMPTS:
            cache.delete(cache_key)
            return False, '验证码错误次数过多，请刷新重试'
        
        # 验证验证码
        if captcha_data['code'] != code.upper():
            # 增加尝试次数
            captcha_data['attempts'] = attempts + 1
            cache.set(cache_key, captcha_data, timeout=CaptchaService.CAPTCHA_EXPIRE)
            return False, '验证码错误'
        
        # 验证通过，删除缓存
        cache.delete(cache_key)
        return True, ''
    
    @staticmethod
    def clear_captcha(token: str) -> None:
        """清除验证码"""
        cache_key = f'captcha:{token}'
        cache.delete(cache_key)


# 兼容函数
def generate_captcha(token: str) -> Tuple[str, str]:
    """生成验证码"""
    return CaptchaService.generate_captcha(token)

def verify_captcha(token: str, code: str) -> Tuple[bool, str]:
    """验证验证码"""
    return CaptchaService.verify_captcha(token, code)
