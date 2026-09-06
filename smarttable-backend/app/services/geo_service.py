"""
地理位置数据服务

为「地理位置」字段提供行政区划与国家和地区数据。

数据来源为项目内置的固定 JSON 文件（app/data/geo/），与 SeaTable 公开数据源
（https://cloud.seatable.cn/media/geo-data/）的结构保持一致：

- cn-location.json        中国省 / 市 / 区三级树
- cn-region-location.json 国家和地区（中文，按大洲分组）
- en-region-location.json 国家和地区（英文，按大洲分组）

JSON 体积较大（省市区约 80KB），因此采用「懒加载 + 模块级缓存」策略：
首次访问时读盘解析，后续请求直接命中内存；文件 mtime 变化时自动重新加载。
"""
import json
import os
import threading
from typing import Any, Dict, List, Optional

import requests
from flask import current_app


class GeoService:
    """地理位置数据服务"""

    # 数据文件所在目录（app/data/geo）
    GEO_DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'geo'
    )

    CHINA_LOCATION_FILE = os.path.join(GEO_DATA_DIR, 'cn-location.json')

    # 中国行政区划：中文 / 英文两份数据
    CHINA_LOCATION_FILES = {
        'zh': os.path.join(GEO_DATA_DIR, 'cn-location.json'),
        'en': os.path.join(GEO_DATA_DIR, 'en-location.json'),
    }

    REGION_LOCATION_FILES = {
        'zh': os.path.join(GEO_DATA_DIR, 'cn-region-location.json'),
        'en': os.path.join(GEO_DATA_DIR, 'en-region-location.json'),
    }

    # 支持的语言
    SUPPORTED_LANGS = ('zh', 'en')

    # 层级裁剪参数
    LEVEL_PROVINCE = 'province'
    LEVEL_CITY = 'city'
    LEVEL_DISTRICT = 'district'

    # 模块级缓存：{key: {'mtime': float, 'data': Any}}
    _cache: Dict[str, Dict[str, Any]] = {}
    _cache_lock = threading.Lock()

    # ==================== 内部工具 ====================

    @staticmethod
    def _log_error(message: str) -> None:
        """输出错误日志（应用上下文不可用时降级为静默）。"""
        try:
            if current_app:
                current_app.logger.error(f'[GeoService] {message}')
        except Exception:
            pass

    @classmethod
    def _load_json(cls, file_path: str) -> Optional[Any]:
        """读取并解析 JSON 文件，失败时返回 None。"""
        if not os.path.exists(file_path):
            cls._log_error(f'地理数据文件不存在: {file_path}')
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        except (OSError, ValueError) as exc:
            cls._log_error(f'读取地理数据文件失败 {file_path}: {exc}')
            return None

    @classmethod
    def _get_cached(cls, key: str, file_path: str) -> Optional[Any]:
        """带 mtime 失效校验的内存缓存读取。"""
        if not os.path.exists(file_path):
            return None

        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            mtime = 0

        with cls._cache_lock:
            entry = cls._cache.get(key)
            if entry and entry.get('mtime') == mtime:
                return entry.get('data')

        data = cls._load_json(file_path)
        if data is None:
            return None

        with cls._cache_lock:
            cls._cache[key] = {'mtime': mtime, 'data': data}
        return data

    @classmethod
    def resolve_lang(cls, raw: Optional[str] = None, request=None) -> str:
        """
        解析地理数据语言。

        优先级：显式传入的 lang > 请求头 Accept-Language > 默认 zh。

        Args:
            raw: 显式语言参数，支持 'zh' / 'en' / 'zh-CN' / 'en-US' 等
            request: Flask request，用于读取 Accept-Language

        Returns:
            'zh' 或 'en'
        """
        value = (raw or '').strip().lower()
        if value in cls.SUPPORTED_LANGS:
            return value
        # 兼容带区域后缀的形式（zh-CN / en-US / en-GB ...）
        if value:
            return 'en' if value.startswith('en') else 'zh'

        if request is not None:
            header = ''
            try:
                header = (request.headers.get('Accept-Language') or '').strip().lower()
            except Exception:
                header = ''
            if header:
                return 'en' if header.startswith('en') else 'zh'

        return 'zh'

    @staticmethod
    def _children_of(node: Optional[Dict]) -> List[Dict]:
        """取子节点列表，兼容缺失 children 的情况。"""
        if not isinstance(node, dict):
            return []
        children = node.get('children')
        return children if isinstance(children, list) else []

    # ==================== 对外接口 ====================

    @classmethod
    def get_china_locations(
        cls, level: Optional[str] = None, lang: str = 'zh'
    ) -> List[Dict[str, Any]]:
        """
        获取中国行政区划数据（省 / 市 / 区）。

        Args:
            level: 层级裁剪，province 仅省份 / city 省市 / district 或 None 为省市区三级
            lang: 语言，zh（中文）或 en（英文）

        Returns:
            [{'name': '广东省', 'alphabetic': 'guangdongsheng', 'children': [...]}, ...]
        """
        file_path = cls.CHINA_LOCATION_FILES.get(lang) or cls.CHINA_LOCATION_FILES['zh']
        raw = cls._get_cached(f'cn-location-{lang}', file_path)
        if not isinstance(raw, dict):
            return []

        provinces: List[Dict[str, Any]] = []
        for province in cls._children_of(raw):
            province_name = province.get('name')
            if not province_name:
                continue

            province_item: Dict[str, Any] = {'name': province_name}
            if province.get('alphabetic'):
                province_item['alphabetic'] = province['alphabetic']

            if level == cls.LEVEL_PROVINCE:
                provinces.append(province_item)
                continue

            cities: List[Dict[str, Any]] = []
            for city in cls._children_of(province):
                city_name = city.get('name')
                if not city_name:
                    continue

                city_item: Dict[str, Any] = {'name': city_name}
                if level in (None, '', cls.LEVEL_DISTRICT):
                    city_item['children'] = [
                        {'name': district.get('name')}
                        for district in cls._children_of(city)
                        if district.get('name')
                    ]

                cities.append(city_item)

            province_item['children'] = cities
            provinces.append(province_item)

        return provinces

    @classmethod
    def get_regions(cls, lang: str = 'zh') -> List[Dict[str, Any]]:
        """
        获取国家和地区数据（按大洲分组）。

        Args:
            lang: 语言，zh（中文）或 en（英文）

        Returns:
            [{'name': '亚洲', 'items': ['中国', '日本', ...]}, ...]
            归一化成数组以保证大洲顺序稳定（JSON 对象 key 顺序不可靠）。
        """
        file_path = cls.REGION_LOCATION_FILES.get(lang) or cls.REGION_LOCATION_FILES['zh']
        raw = cls._get_cached(f'region-{lang}', file_path)
        if not isinstance(raw, dict):
            return []

        continents: List[Dict[str, Any]] = []
        for continent_name, items in raw.items():
            if not isinstance(items, list):
                continue
            continents.append({
                'name': continent_name,
                'items': [item for item in items if isinstance(item, str) and item],
            })
        return continents

    @classmethod
    def get_map_config(cls) -> Dict[str, Any]:
        """
        获取地图服务配置（下发给前端）。

        Returns:
            {'provider': 'tianditu', 'apiBase': ..., 'key': ..., 'enabled': bool}
        """
        key = ''
        api_base = 'https://api.tianditu.gov.cn'
        try:
            if current_app:
                key = (current_app.config.get('TIANDITU_KEY') or '').strip()
                api_base = current_app.config.get('TIANDITU_API_BASE') or api_base
        except Exception:
            pass

        return {
            'provider': 'tianditu',
            'apiBase': api_base.rstrip('/'),
            'key': key,
            'enabled': bool(key),
        }

    # ==================== IP 定位 ====================

    @staticmethod
    def _client_ip(request) -> str:
        """从请求中提取客户端真实 IP（兼容常见反代头）。"""
        xff = request.headers.get('X-Forwarded-For')
        if xff:
            return xff.split(',')[0].strip()
        xri = request.headers.get('X-Real-IP')
        if xri:
            return xri.strip()
        return request.remote_addr or ''

    @classmethod
    def _parse_tdt_location(cls, data: Any) -> Optional[tuple]:
        """
        兼容解析天地图 IP 定位返回的坐标。

        可能的数据形态：
        - {'result': {'location': {'lng': x, 'lat': y}, 'address': '...'}}
        - {'result': {'lonlat': 'x,y', 'address': '...'}}
        - {'lng': x, 'lat': y, 'address': '...'}
        返回 (lng, lat, address) 或 None。
        """
        if not isinstance(data, dict):
            return None

        result = data.get('result') or {}
        loc = result.get('location') or {}
        if isinstance(loc, dict) and 'lat' in loc and 'lng' in loc:
            return (float(loc['lng']), float(loc['lat']), result.get('address') or '')

        lonlat = result.get('lonlat')
        if isinstance(lonlat, str) and ',' in lonlat:
            try:
                x, y = lonlat.split(',')
                return (float(x.strip()), float(y.strip()), result.get('address') or '')
            except ValueError:
                pass

        if 'lng' in data and 'lat' in data:
            return (float(data['lng']), float(data['lat']), data.get('address') or '')

        return None

    @classmethod
    def ip_locate(cls, request) -> Dict[str, Any]:
        """
        基于客户端 IP 调用天地图 IP 定位服务，返回近似坐标。

        失败（未配置 Key / IP 缺失 / 网络异常 / 解析失败）时返回 {'enabled': False}，
        由前端回退到浏览器定位或默认中心点。
        """
        key = ''
        api_base = 'https://api.tianditu.gov.cn'
        try:
            if current_app:
                key = (current_app.config.get('TIANDITU_KEY') or '').strip()
                api_base = current_app.config.get('TIANDITU_API_BASE') or api_base
        except Exception:
            pass

        if not key:
            return {'enabled': False}

        ip = cls._client_ip(request)
        if not ip:
            return {'enabled': False}

        url = f"{api_base.rstrip('/')}/ip/location?tk={key}&ip={ip}"
        try:
            resp = requests.get(url, timeout=5, headers={'User-Agent': 'SmartTable'})
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            cls._log_error(f'天地图 IP 定位请求失败: {exc}')
            return {'enabled': False}

        parsed = cls._parse_tdt_location(data)
        if not parsed:
            return {'enabled': False}

        return {
            'enabled': True,
            'lng': parsed[0],
            'lat': parsed[1],
            'address': parsed[2],
            'source': 'ip',
        }
