"""
地理位置数据服务与路由单元测试

覆盖：
- GeoService 行政区划（省市区）按层级裁剪
- 国家和地区（中/英）归一化结构
- 地图配置（Key / enabled）下发
- 文件缺失 / 非法入参等异常路径
- /api/geo/* 路由的正常流程与鉴权边界
"""
import pytest

from app.services.geo_service import GeoService


# ==================== GeoService 纯函数测试（无需应用上下文） ====================


class TestGetChinaLocations:
    """中国行政区划数据：层级裁剪与结构一致性"""

    def test_level_province_returns_only_names(self):
        provinces = GeoService.get_china_locations(level="province")
        assert isinstance(provinces, list)
        assert len(provinces) >= 30  # 中国省级行政区数量级
        for item in provinces:
            assert "name" in item
            # 省级裁剪不应包含 children
            assert "children" not in item

    def test_level_city_returns_province_and_city_no_district(self):
        provinces = GeoService.get_china_locations(level="city")
        assert len(provinces) >= 30
        for province in provinces:
            assert "children" in province
            cities = province["children"]
            assert len(cities) > 0
            for city in cities:
                assert "name" in city
                # city 层级不应再展开 district
                assert "children" not in city

    def test_level_district_returns_full_three_levels(self):
        provinces = GeoService.get_china_locations(level="district")
        # 选一个含市辖区的省验证三级结构
        guangdong = next((p for p in provinces if p["name"] == "广东省"), None)
        assert guangdong is not None
        shenzhen = next((c for c in guangdong["children"] if c["name"] == "深圳市"), None)
        assert shenzhen is not None
        assert len(shenzhen["children"]) > 0
        assert "name" in shenzhen["children"][0]

    def test_level_none_defaults_to_district(self):
        provinces_none = GeoService.get_china_locations(level=None)
        provinces_district = GeoService.get_china_locations(level="district")
        # 默认与 district 行为一致（都带三级）
        assert len(provinces_none) == len(provinces_district)
        assert "children" in provinces_none[0]
        assert "children" in provinces_none[0]["children"][0]

    def test_level_invalid_value_is_treated_as_default(self):
        # 非法 level 应回退为默认（三级），不抛异常
        provinces = GeoService.get_china_locations(level="unknown")
        assert isinstance(provinces, list)
        assert len(provinces) >= 30

    def test_known_province_present(self):
        names = [p["name"] for p in GeoService.get_china_locations(level="province")]
        assert "北京市" in names
        assert "广东省" in names


class TestGetRegions:
    """国家和地区数据：中英切换与结构归一化"""

    def test_zh_returns_continent_grouped_items(self):
        regions = GeoService.get_regions(lang="zh")
        assert isinstance(regions, list)
        continent_names = [r["name"] for r in regions]
        assert "亚洲" in continent_names
        for r in regions:
            assert "name" in r
            assert isinstance(r["items"], list)
            assert all(isinstance(i, str) for i in r["items"])
        # 亚洲应有内容
        asia = next(r for r in regions if r["name"] == "亚洲")
        assert len(asia["items"]) > 0

    def test_en_returns_english_continent_names(self):
        regions = GeoService.get_regions(lang="en")
        assert isinstance(regions, list)
        continent_names = [r["name"] for r in regions]
        assert "Asia" in continent_names
        assert "亚洲" not in continent_names

    def test_unsupported_lang_falls_back_to_zh(self):
        regions = GeoService.get_regions(lang="fr")
        continent_names = [r["name"] for r in regions]
        assert "亚洲" in continent_names  # 回退中文

    def test_items_are_strings(self):
        regions = GeoService.get_regions(lang="zh")
        for r in regions:
            for item in r["items"]:
                assert isinstance(item, str)


class TestGetMapConfig:
    """地图服务配置下发（无 Key / 有 Key 两种状态）"""

    def test_no_app_context_returns_disabled(self):
        # 无应用上下文时，key 为空、enabled=False，且不抛异常
        cfg = GeoService.get_map_config()
        assert cfg["provider"] == "tianditu"
        assert cfg["enabled"] is False
        assert cfg["key"] == ""

    def test_with_key_returns_enabled(self, app):
        app.config["TIANDITU_KEY"] = "test-tianditu-key"
        with app.app_context():
            cfg = GeoService.get_map_config()
        assert cfg["enabled"] is True
        assert cfg["key"] == "test-tianditu-key"
        assert cfg["apiBase"].startswith("https://")


class TestErrorPaths:
    """文件缺失等异常路径"""

    def test_missing_file_returns_empty_list(self):
        assert GeoService._load_json("/nonexistent/path/geo.json") is None

    def test_china_locations_missing_file_returns_empty(self, monkeypatch):
        monkeypatch.setattr(GeoService, "CHINA_LOCATION_FILE", "/nonexistent.json")
        # 缓存应失效，文件读取返回 None → 空列表
        assert GeoService.get_china_locations(level="district") == []

    def test_regions_missing_file_returns_empty(self, monkeypatch):
        monkeypatch.setattr(GeoService, "REGION_LOCATION_FILES", {"zh": "/nonexistent.json", "en": "/nonexistent.json"})
        assert GeoService.get_regions(lang="zh") == []


# ==================== /api/geo/* 路由测试 ====================


class TestGeoRoutes:
    """路由正常流程与鉴权边界"""

    def test_config_requires_auth(self, client):
        resp = client.get("/api/geo/config")
        assert resp.status_code == 401

    def test_china_locations_requires_auth(self, client):
        resp = client.get("/api/geo/china-locations?level=province")
        assert resp.status_code == 401

    def test_config_ok(self, client, auth_headers):
        resp = client.get("/api/geo/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["provider"] == "tianditu"
        assert "enabled" in data

    def test_china_locations_province_ok(self, client, auth_headers):
        resp = client.get("/api/geo/china-locations?level=province", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 30

    def test_china_locations_invalid_level_rejected(self, client, auth_headers):
        resp = client.get("/api/geo/china-locations?level=illegal", headers=auth_headers)
        assert resp.status_code == 400

    def test_regions_zh_ok(self, client, auth_headers):
        resp = client.get("/api/geo/regions?lang=zh", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert "亚洲" in [r["name"] for r in data]

    def test_regions_en_ok(self, client, auth_headers):
        resp = client.get("/api/geo/regions?lang=en", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "Asia" in [r["name"] for r in data]
