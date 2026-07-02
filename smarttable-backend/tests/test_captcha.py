"""
验证码模块测试
"""
import pytest
import base64
from io import BytesIO
from unittest.mock import patch

from app.utils.captcha import CaptchaService

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class TestCaptchaService:
    """验证码服务测试类"""

    def test_generate_captcha_code_length(self):
        """测试验证码长度"""
        code = CaptchaService.generate_captcha_code(4)
        assert len(code) == 4

    def test_generate_captcha_code_chars(self):
        """测试验证码字符集"""
        code = CaptchaService.generate_captcha_code(10)
        valid_chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        assert all(c in valid_chars for c in code)

    def test_create_captcha_image_returns_bytes(self):
        """测试验证码图片生成返回字节数据"""
        code = CaptchaService.generate_captcha_code(4)
        image_data = CaptchaService.create_captcha_image(code)
        assert isinstance(image_data, bytes)
        assert len(image_data) > 0

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_create_captcha_image_valid_png(self):
        """测试生成的图片是有效的 PNG"""
        code = CaptchaService.generate_captcha_code(4)
        image_data = CaptchaService.create_captcha_image(code)
        
        # 验证可以解析为图片
        image = Image.open(BytesIO(image_data))
        assert image.format == 'PNG'
        assert image.width == 120
        assert image.height == 40

    def test_create_svg_captcha_returns_bytes(self):
        """测试 SVG 备用方案返回字节数据"""
        code = CaptchaService.generate_captcha_code(4)
        svg_data = CaptchaService._create_svg_captcha(code)
        assert isinstance(svg_data, bytes)
        svg_text = svg_data.decode('utf-8')
        assert '<svg' in svg_text
        assert code[0] in svg_text

    def test_svg_captcha_font_size(self):
        """测试 SVG 验证码字体大小合理"""
        code = CaptchaService.generate_captcha_code(4)
        svg_data = CaptchaService._create_svg_captcha(code, width=120, height=40)
        svg_text = svg_data.decode('utf-8')
        # 字体大小应该至少为 20（高度的 60%）
        assert 'font-size="24"' in svg_text or 'font-size="20"' in svg_text

    def test_generate_captcha(self, app):
        """测试完整验证码生成流程"""
        with app.app_context():
            code, image_base64, mime_type = CaptchaService.generate_captcha('test-token')
        
        assert len(code) == 4
        assert isinstance(image_base64, str)
        assert mime_type == 'image/png'
        # 验证 base64 可解码
        decoded = base64.b64decode(image_base64)
        assert len(decoded) > 0

    def test_verify_captcha_correct(self, app):
        """测试验证码验证成功"""
        with app.app_context():
            code, _, _ = CaptchaService.generate_captcha('verify-token')
            result, error = CaptchaService.verify_captcha('verify-token', code)
        assert result is True
        assert error == ''

    def test_verify_captcha_wrong(self, app):
        """测试验证码验证失败"""
        with app.app_context():
            CaptchaService.generate_captcha('wrong-token')
            result, error = CaptchaService.verify_captcha('wrong-token', 'WRONG')
        assert result is False
        assert error == '验证码错误'

    def test_verify_captcha_empty(self):
        """测试空验证码"""
        result, error = CaptchaService.verify_captcha('empty-token', '')
        assert result is False
        assert error == '请输入验证码'

    def test_verify_captcha_expired(self, app):
        """测试验证码过期"""
        with app.app_context():
            result, error = CaptchaService.verify_captcha('expired-token', 'ABCD')
        assert result is False
        assert error == '验证码已过期，请刷新重试'

    def test_test_captcha_bypass(self):
        """测试万能验证码"""
        result, error = CaptchaService.verify_captcha('any-token', 'TEST')
        assert result is True
        assert error == ''

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_captcha_image_text_size(self):
        """测试验证码图片中文字占用合理区域"""
        code = CaptchaService.generate_captcha_code(4)
        image_data = CaptchaService.create_captcha_image(code, width=120, height=40)
        image = Image.open(BytesIO(image_data))
        
        # 图片尺寸应符合预期
        assert image.width == 120
        assert image.height == 40
        
        # 验证图片不是全白的（有文字和干扰内容）
        pixels = list(image.getdata())
        unique_colors = set(pixels)
        assert len(unique_colors) > 10

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_get_font_returns_font(self):
        """测试字体加载"""
        font = CaptchaService._get_font(28)
        assert font is not None
