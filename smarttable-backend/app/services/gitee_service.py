"""
Gitee OAuth 与 Star 检查服务
处理演示环境下 Gitee 授权、state 缓存及 star 状态检测
"""
import json
import logging
import secrets
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode

import requests
from flask import current_app

logger = logging.getLogger(__name__)


def _get_redis_client():
    """动态获取 Redis 客户端，避免 Flask 重载器导致的模块级快照问题"""
    from app.extensions import redis_client
    return redis_client

# Gitee 基础 URL 与接口路径
GITEE_BASE_URL = 'https://gitee.com'
GITEE_OAUTH_AUTHORIZE_PATH = '/oauth/authorize'
GITEE_OAUTH_TOKEN_PATH = '/oauth/token'
GITEE_STARRED_API_PATH = '/api/v5/user/starred'

# 默认目标仓库
DEFAULT_REPO_OWNER = 'binac'
DEFAULT_REPO_NAME = 'smart_table'

# 常见 HTTP 状态码
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND = 404


class GiteeService:
    """Gitee OAuth 与 Star 校验服务"""

    STATE_TTL_SECONDS = 600  # state 有效期 10 分钟

    @staticmethod
    def is_demo_enabled() -> bool:
        """是否开启演示环境"""
        return bool(current_app.config.get('IS_DEMO_ENVIRONMENT', False))

    @staticmethod
    def get_repo_url() -> str:
        """获取目标仓库 URL"""
        owner = current_app.config.get('GITEE_REPO_OWNER', DEFAULT_REPO_OWNER)
        repo = current_app.config.get('GITEE_REPO_NAME', DEFAULT_REPO_NAME)
        return f'{GITEE_BASE_URL}/{owner}/{repo}'

    @staticmethod
    def generate_authorize_url(user_id: str, email: str) -> str:
        """生成 Gitee OAuth 授权 URL 并缓存 state"""
        state = secrets.token_urlsafe(32)
        cache_key = f'demo:gitee_star_state:{state}'
        payload = {'user_id': user_id, 'email': email}

        redis_client = _get_redis_client()
        if redis_client:
            try:
                redis_client.setex(cache_key, GiteeService.STATE_TTL_SECONDS, json.dumps(payload))
            except Exception as e:
                logger.error(f'缓存 Gitee OAuth state 失败: {e}')
                raise RuntimeError('授权状态缓存失败，请稍后重试')
        else:
            raise RuntimeError('Redis 不可用，无法创建授权状态')

        client_id = current_app.config.get('GITEE_CLIENT_ID', '')
        redirect_uri = current_app.config.get('GITEE_REDIRECT_URI', '')

        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state,
        }
        return f'{GITEE_BASE_URL}{GITEE_OAUTH_AUTHORIZE_PATH}?{urlencode(params)}'

    @staticmethod
    def get_state_data(state: str) -> Optional[Dict[str, str]]:
        """读取并验证 state"""
        redis_client = _get_redis_client()
        if not redis_client:
            return None
        try:
            cache_key = f'demo:gitee_star_state:{state}'
            raw = redis_client.get(cache_key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error(f'读取 Gitee OAuth state 失败: {e}')
            return None

    @staticmethod
    def clear_state(state: str) -> None:
        """清除 state 缓存"""
        redis_client = _get_redis_client()
        if redis_client:
            try:
                redis_client.delete(f'demo:gitee_star_state:{state}')
            except Exception as e:
                logger.error(f'清除 Gitee OAuth state 失败: {e}')

    @staticmethod
    def exchange_access_token(code: str) -> Tuple[Optional[str], Optional[str]]:
        """用授权码换取 access_token"""
        client_id = current_app.config.get('GITEE_CLIENT_ID', '')
        client_secret = current_app.config.get('GITEE_CLIENT_SECRET', '')
        redirect_uri = current_app.config.get('GITEE_REDIRECT_URI', '')

        try:
            resp = requests.post(
                f'{GITEE_BASE_URL}{GITEE_OAUTH_TOKEN_PATH}',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri,
                },
                timeout=30,
            )
            if resp.status_code != HTTP_OK:
                logger.warning(f'Gitee token 换取失败: status={resp.status_code}, body={resp.text}')
                return None, 'gitee_oauth_failed'
            data = resp.json()
            access_token = data.get('access_token')
            if not access_token:
                return None, 'gitee_oauth_failed'
            return access_token, None
        except requests.RequestException as e:
            logger.error(f'Gitee token 换取请求异常: {e}')
            return None, 'gitee_oauth_failed'
        except json.JSONDecodeError as e:
            logger.error(f'Gitee token 响应解析失败: {e}')
            return None, 'gitee_oauth_failed'
        except Exception as e:
            logger.error(f'Gitee token 换取发生未预期异常: {e}')
            return None, 'gitee_oauth_failed'

    @staticmethod
    def check_starred(access_token: str) -> Tuple[bool, Optional[str]]:
        """检测当前授权用户是否已 star 目标仓库"""
        owner = current_app.config.get('GITEE_REPO_OWNER', DEFAULT_REPO_OWNER)
        repo = current_app.config.get('GITEE_REPO_NAME', DEFAULT_REPO_NAME)
        strict_mode = bool(current_app.config.get('GITEE_STAR_CHECK_STRICT_MODE', False))

        try:
            resp = requests.get(
                f'{GITEE_BASE_URL}{GITEE_STARRED_API_PATH}/{owner}/{repo}',
                params={'access_token': access_token},
                timeout=30,
            )
            if resp.status_code == HTTP_NO_CONTENT:
                return True, None
            if resp.status_code == HTTP_NOT_FOUND:
                return False, 'gitee_repo_not_starred'

            logger.warning(f'Gitee star 检测失败: status={resp.status_code}, body={resp.text}')
            if strict_mode:
                return False, 'gitee_star_check_failed'
            return True, None
        except requests.RequestException as e:
            logger.error(f'Gitee star 检测请求异常: {e}')
            if strict_mode:
                return False, 'gitee_star_check_failed'
            return True, None
        except Exception as e:
            logger.error(f'Gitee star 检测发生未预期异常: {e}')
            if strict_mode:
                return False, 'gitee_star_check_failed'
            return True, None
