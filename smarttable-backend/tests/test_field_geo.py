"""
字段服务中「地理位置」相关逻辑的单元测试

覆盖：
- 地理位置 → 文本 的格式化（_to_text）
- 文本 ↔ 地理位置 互转（_convert_value_for_type）
- 值是否可被目标类型承载的预检（_value_fits_type）
- 默认值校验（validate_default_value）
- 字段类型信息（get_field_type_info）
"""
import pytest

from app.services.field_service import FieldService
from app.models.field import FieldType


class TestToText:
    """_to_text：地理位置对象格式化拼接"""

    def test_province_city_district(self):
        assert FieldService._to_text({"province": "广东", "city": "深圳", "district": "南山"}) == "广东 / 深圳 / 南山"

    def test_with_detail(self):
        assert (
            FieldService._to_text({"province": "广东", "city": "深圳", "district": "南山", "detail": "科技园1号"})
            == "广东 / 深圳 / 南山 / 科技园1号"
        )

    def test_country_region(self):
        assert FieldService._to_text({"country": "中国", "region": "亚洲"}) == "亚洲 / 中国"

    def test_lng_lat(self):
        assert FieldService._to_text({"lng": 116.4, "lat": 39.9}) == "116.4, 39.9"

    def test_address_fallback(self):
        assert FieldService._to_text({"address": "某处地址"}) == "某处地址"


class TestConvertValueForType:
    """_convert_value_for_type：文本 ↔ 地理位置 互转"""

    def test_text_to_geo_wraps_as_address(self):
        # 文本转地理位置：文本承载为 address 兜底
        assert FieldService._convert_value_for_type("广东省深圳市", "single_line_text", "geolocation") == {
            "address": "广东省深圳市"
        }

    def test_geo_object_to_geo_kept(self):
        val = {"province": "广东", "city": "深圳"}
        assert FieldService._convert_value_for_type(val, "geolocation", "geolocation") == val

    def test_geo_to_text(self):
        # 地理位置对象转文本：按层级拼接
        assert FieldService._convert_value_for_type({"province": "广东", "city": "深圳"}, "geolocation", "single_line_text") == "广东 / 深圳"

    def test_geo_to_text_via_format_helper(self):
        # 经纬度对象转文本
        assert FieldService._convert_value_for_type({"lng": 116.4, "lat": 39.9}, "geolocation", "single_line_text") == "116.4, 39.9"


class TestValueFitsType:
    """_value_fits_type：目标类型承载预检"""

    def test_dict_fits(self):
        assert FieldService._value_fits_type({"province": "广东"}, "geolocation") is True

    def test_none_fits(self):
        assert FieldService._value_fits_type(None, "geolocation") is True

    def test_string_does_not_fit(self):
        # 地理位置必须是对象，字符串不可承载
        assert FieldService._value_fits_type("广东", "geolocation") is False

    def test_list_does_not_fit(self):
        assert FieldService._value_fits_type(["广东"], "geolocation") is False


class TestValidateDefaultValue:
    """validate_default_value：地理位置默认值校验（需应用上下文以使用 i18n）"""

    def test_none_is_valid(self, app):
        with app.app_context():
            ok, err = FieldService.validate_default_value(FieldType.GEOLOCATION.value, {}, None)
        assert ok is True
        assert err is None

    def test_object_is_valid(self, app):
        with app.app_context():
            ok, err = FieldService.validate_default_value(
                FieldType.GEOLOCATION.value, {}, {"province": "广东", "city": "深圳"}
            )
        assert ok is True

    def test_non_object_rejected(self, app):
        with app.app_context():
            ok, err = FieldService.validate_default_value(FieldType.GEOLOCATION.value, {}, "广东省")
        assert ok is False
        assert err  # 返回非空错误信息

    def test_empty_string_rejected(self, app):
        # 空字符串不是对象，应拒绝
        with app.app_context():
            ok, err = FieldService.validate_default_value(FieldType.GEOLOCATION.value, {}, "")
        assert ok is False


class TestFieldTypeInfo:
    """get_field_type_info：类型元信息"""

    def test_geolocation_info_present(self, app):
        with app.app_context():
            info = FieldService.get_field_type_info(FieldType.GEOLOCATION.value)
        assert isinstance(info, dict)
        assert "name" in info
        assert info.get("icon") == "map-pin"
