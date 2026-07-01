"""
Gitee OAuth 与 Star 检查服务
处理演示环境下 Gitee 授权、state 缓存及 star 状态检测
"""
import json
import logging
import secrets
from typing import Any, Dict, Optional, Tuple

import requests
from flask import current_app

from app.extensions import redis_client

logger = logging.getLogger(__name__)


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
        owner = current_app.config.get('GITEE_REPO_OWNER', 'binac')
        repo = current_app.config.get('GITEE_REPO_NAME', 'smart_table')
        return f'https://gitee.com/{owner}/{repo}'

    @staticmethod
    def generate_authorize_url(user_id: str, email: str) -> str:
        """生成 Gitee OAuth 授权 URL 并缓存 state"""
        state = secrets.token_urlsafe(32)
        cache_key = f'demo:gitee_star_state:{state}'
        payload = {'user_id': str(user_id), 'email': email}

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

        params = [
            'response_type=code',
            f'client_id={client_id}',
            f'redirect_uri={redirect_uri}',
            f'state={state}',
        ]
        return f'https://gitee.com/oauth/authorize?{"&".join(params)}'

    @staticmethod
    def get_state_data(state: str) -> Optional[Dict[str, str]]:
        """读取并验证 state"""
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
                'https://gitee.com/oauth/token',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning(f'Gitee token 换取失败: status={resp.status_code}, body={resp.text}')
                return None, 'gitee_oauth_failed'
            data = resp.json()
            access_token = data.get('access_token')
            if not access_token:
                return None, 'gitee_oauth_failed'
            return access_token, None
        except Exception as e:
            logger.error(f'Gitee token 换取异常: {e}')
            return None, 'gitee_oauth_failed'

    @staticmethod
    def check_starred(access_token: str) -> Tuple[bool, Optional[str]]:
        """检测当前授权用户是否已 star 目标仓库"""
        owner = current_app.config.get('GITEE_REPO_OWNER', 'binac')
        repo = current_app.config.get('GITEE_REPO_NAME', 'smart_table')
        strict_mode = bool(current_app.config.get('GITEE_STAR_CHECK_STRICT_MODE', False))

        try:
            resp = requests.get(
                f'https://gitee.com/api/v5/user/starred/{owner}/{repo}',
                params={'access_token': access_token},
                timeout=30,
            )
            if resp.status_code == 204:
                return True, None
            if resp.status_code == 404:
                return False, 'gitee_repo_not_starred'

            logger.warning(f'Gitee star 检测失败: status={resp.status_code}, body={resp.text}')
            if strict_mode:
                return False, 'gitee_star_check_failed'
            return True, None
        except Exception as e:
            logger.error(f'Gitee star 检测异常: {e}')
            if strict_mode:
                return False, 'gitee_star_check_failed'
            return True, None
