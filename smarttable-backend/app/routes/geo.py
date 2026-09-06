"""
地理位置路由模块

为「地理位置」字段提供行政区划 / 国家和地区数据，以及地图服务配置。
数据来自项目内置的固定 JSON 文件，经 GeoService 缓存后返回。
"""
from flask import Blueprint, request

from app.services.geo_service import GeoService
from app.utils.decorators import jwt_required
from app.utils.response import success_response, error_response

geo_bp = Blueprint('geo', __name__)
geo_bp.strict_slashes = False


@geo_bp.route('/geo/config', methods=['GET'])
@jwt_required
def get_geo_config() -> tuple:
    """
    获取地图服务配置（天地图 Key 等）
    ---
    tags:
      - Geo
    responses:
      200:
        description: 返回地图服务配置
        schema:
          type: object
          properties:
            provider:
              type: string
              example: tianditu
            apiBase:
              type: string
              example: https://api.tianditu.gov.cn
            key:
              type: string
            enabled:
              type: boolean
    """
    return success_response(data=GeoService.get_map_config(), message='fetched_successfully')


@geo_bp.route('/geo/china-locations', methods=['GET'])
@jwt_required
def get_china_locations() -> tuple:
    """
    获取中国行政区划数据（省 / 市 / 区）
    ---
    tags:
      - Geo
    parameters:
      - name: level
        in: query
        type: string
        required: false
        description: 层级裁剪，province 仅省份 / city 省市 / district 或不传为省市区三级
      - name: lang
        in: query
        type: string
        required: false
        description: 语言，zh（默认）或 en；不传时回退解析 Accept-Language 请求头
    responses:
      200:
        description: 返回省市区数据
    """
    level = (request.args.get('level') or '').strip().lower() or None
    if level not in (None, 'province', 'city', 'district'):
        return error_response('invalid_parameter', 400)

    # 语言优先级：lang 查询参数 > Accept-Language 请求头 > zh
    lang = GeoService.resolve_lang(request.args.get('lang'), request)

    return success_response(
        data=GeoService.get_china_locations(level, lang),
        message='fetched_successfully'
    )


@geo_bp.route('/geo/locate', methods=['GET'])
@jwt_required
def geo_locate() -> tuple:
    """
    基于客户端 IP 的天地图定位（近似位置）
    ---
    tags:
      - Geo
    responses:
      200:
        description: 返回客户端近似经纬度；未配置 Key 或定位失败时 enabled=false
        schema:
          type: object
          properties:
            enabled:
              type: boolean
            lng:
              type: number
            lat:
              type: number
            address:
              type: string
            source:
              type: string
    """
    return success_response(data=GeoService.ip_locate(request), message='fetched_successfully')


@geo_bp.route('/geo/regions', methods=['GET'])
@jwt_required
def get_regions() -> tuple:
    """
    获取国家和地区数据（按大洲分组）
    ---
    tags:
      - Geo
    parameters:
      - name: lang
        in: query
        type: string
        required: false
        description: 语言，zh（默认）或 en
    responses:
      200:
        description: 返回国家和地区数据
    """
    # 语言优先级：lang 查询参数 > Accept-Language 请求头 > zh
    lang = GeoService.resolve_lang(request.args.get('lang'), request)

    return success_response(data=GeoService.get_regions(lang), message='fetched_successfully')
