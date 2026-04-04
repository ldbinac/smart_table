"""
验证器单元测试
"""
import pytest
from app.utils.validators import (
    validate_email,
    validate_password,
    validate_uuid,
    validate_url,
    validate_phone,
    validate_hex_color,
    validate_date_string,
    validate_length,
    validate_number,
    validate_field_name,
    sanitize_string,
    ValidationError
)


class TestValidateEmail:
    """邮箱验证测试"""
    
    def test_valid_email(self):
        valid_emails = [
            'test@example.com',
            'user.name@domain.org',
            'user123@test.co.uk',
            'a+b@c.com',
        ]
        for email in valid_emails:
            ok, err = validate_email(email)
            assert ok is True, f"{email} 应该是有效的"
            assert err is None
    
    def test_invalid_email(self):
        invalid_emails = [
            '',
            'plaintext',
            '@missing-local.com',
            'missing-at@com',
            'spaces in@domain.com',
        ]
        for email in invalid_emails:
            ok, err = validate_email(email)
            assert ok is False, f"{email} 应该无效"
            assert err is not None
    
    def test_none_email(self):
        ok, err = validate_email(None)
        assert ok is False
        assert err is not None


class TestValidatePassword:
    """密码强度验证测试"""
    
    def test_strong_password(self):
        ok, err = validate_password('Test1234!')
        assert ok is True
    
    def test_weak_too_short(self):
        ok, err = validate_password('Ab1!', min_length=8)
        assert ok is False
        assert '长度' in err
    
    def test_missing_uppercase(self):
        ok, err = validate_password('test1234!')
        assert ok is False
        assert '大写字母' in err
    
    def test_missing_lowercase(self):
        ok, err = validate_password('TEST1234!')
        assert ok is False
        assert '小写字母' in err
    
    def test_missing_digit(self):
        ok, err = validate_password('TestTest!')
        assert ok is False
        assert '数字' in err
    
    def test_none_password(self):
        ok, err = validate_password(None)
        assert ok is False


class TestValidateUUID:
    """UUID 格式验证测试"""
    
    def test_valid_uuid_v4(self):
        import uuid
        u = str(uuid.uuid4())
        ok, err = validate_uuid(u)
        assert ok is True
    
    def test_invalid_uuid(self):
        invalid = ['not-a-uuid', '', '12345', 'abc-def']
        for u in invalid:
            ok, err = validate_uuid(u)
            assert ok is False
    
    def test_none_uuid(self):
        ok, err = validate_uuid(None)
        assert ok is False


class TestValidateUrl:
    """URL 格式验证测试"""
    
    def test_valid_urls(self):
        urls = [
            'https://example.com',
            'http://localhost:3000',
            'https://www.test.org/path?query=1#hash',
        ]
        for url in urls:
            ok, err = validate_url(url)
            assert ok is True, f"{url}"
    
    def test_invalid_urls(self):
        urls = ['', 'ftp://bad-scheme.com', 'not-a-url', '  ']
        for url in urls:
            ok, err = validate_url(url)
            assert ok is False


class TestValidatePhone:
    """手机号验证测试"""
    
    def test_valid_phones(self):
        phones = ['13812345678', '15098765432', '19912345678']
        for phone in phones:
            ok, err = validate_phone(phone)
            assert ok is True, f"{phone}"
    
    def test_invalid_phones(self):
        phones = ['', '12345', '1381234567', '12345678901234']
        for phone in phones:
            ok, err = validate_phone(phone)
            assert ok is False


class TestValidateHexColor:
    """十六进制颜色验证测试"""
    
    def test_valid_colors(self):
        colors = ['#FF5733', '#fff', '#ABCDEF', '#123']
        for c in colors:
            ok, err = validate_hex_color(c)
            assert ok is True, f"{c}"
    
    def test_invalid_colors(self):
        colors = ['', 'FF5733', 'GGG', '#GGG', '#12']
        for c in colors:
            ok, err = validate_hex_color(c)
            assert ok is False


class TestValidateDateString:
    """日期字符串验证测试"""
    
    def test_valid_dates(self):
        ok, err = validate_date_string('2025-06-15')
        assert ok is True
        
        ok, err = validate_date_string('2025/06/15', '%Y/%m/%d')
        assert ok is True
    
    def test_invalid_dates(self):
        ok, err = validate_date_string('not-a-date')
        assert ok is False
        
        ok, err = validate_date_string('2025-13-01')
        assert ok is False
    
    def test_none_date(self):
        ok, err = validate_date_string(None)
        assert ok is False


class TestValidateLength:
    """字符串长度验证测试"""
    
    def test_within_range(self):
        ok, err = validate_length('hello', min_length=1, max_length=10)
        assert ok is True
    
    def test_too_short(self):
        ok, err = validate_length('hi', min_length=5)
        assert ok is False
        assert '至少' in err
    
    def test_too_long(self):
        ok, err = validate_length('hello world', max_length=5)
        assert ok is False
        assert '不能超过' in err
    
    def test_none_value(self):
        ok, err = validate_length(None)
        assert ok is False


class TestValidateNumber:
    """数值范围验证测试"""
    
    def test_valid_int(self):
        ok, err = validate_number(42, min_value=0, max_value=100)
        assert ok is True
    
    def test_valid_float(self):
        ok, err = validate_number(3.14, min_value=0, max_value=10)
        assert ok is True
    
    def test_below_min(self):
        ok, err = validate_number(-1, min_value=0)
        assert ok is False
    
    def test_above_max(self):
        ok, err = validate_number(101, max_value=100)
        assert ok is False
    
    def test_non_numeric_string(self):
        ok, err = validate_number('abc')
        assert ok is False
        assert '必须是' in err
    
    def test_none_value(self):
        ok, err = validate_number(None)
        assert ok is False


class TestValidateFieldName:
    """字段名称验证测试"""
    
    def test_valid_names(self):
        names = ['姓名', 'age', 'field_1', 'Price', '创建时间']
        for name in names:
            ok, err = validate_field_name(name)
            assert ok is True, f"'{name}' 应该有效"
    
    def test_empty_name(self):
        ok, err = validate_field_name('')
        assert ok is False
    
    def test_too_long_name(self):
        name = 'a' * 101
        ok, err = validate_field_name(name)
        assert ok is False
    
    def test_name_with_html_chars(self):
        for char in ['<', '>', '"', "'"]:
            ok, err = validate_field_name(f'test{char}field')
            assert ok is False, f"包含 '{char}' 应无效"


class TestSanitizeString:
    """字符串清理测试"""
    
    def test_remove_html_tags(self):
        result = sanitize_string('<script>alert("xss")</script>hello')
        assert '<script>' not in result
        assert 'alert' not in result
        assert 'hello' in result
    
    def test_truncate_long_string(self):
        long = 'a' * 300
        result = sanitize_string(long, max_length=255)
        assert len(result) <= 255
    
    def test_strip_whitespace(self):
        result = sanitize_string('  hello world  ')
        assert result == 'hello world'
    
    def test_none_input(self):
        assert sanitize_string(None) == ''
        assert sanitize_string('') == ''


class TestValidationError:
    """ValidationError 异常类测试"""
    
    def test_is_exception(self):
        assert issubclass(ValidationError, Exception)
    
    def test_raise_and_catch(self):
        with pytest.raises(ValidationError):
            raise ValidationError("test error")
    
    def test_message_preserved(self):
        try:
            raise ValidationError("custom message")
        except ValidationError as e:
            assert str(e) == "custom message"
