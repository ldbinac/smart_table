"""
泛微 E10 OAuth2 HTTP 客户端。

严格按 E10 文档实现：
1. GET  /papi/sso/oauth2.0/authorize   获取 code
2. POST /papi/sso/oauth2.0/accessToken 用 code 换 access_token
3. POST /papi/sso/oauth2.0/profile     用 access_token 取用户 id
4. GET  /sp/integration/oauth2.0/logout 注销 E10 会话

E10 文档中的 curl 示例把参数放在 query string，而标准 OAuth2 通常放在
表单体。这里默认 ``auto``：先按 E10 文档用 query，若返回「缺少参数」类
错误再自动改用表单体重试；也可通过环境变量固定为 ``query`` / ``form``。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .config import E10Config

logger = logging.getLogger(__name__)

# E10 错误码 -> 稳定的内部错误原因
_REASON_BY_UPSTREAM_CODE = {
    '1002': 'client_invalid',
    '1003': 'redirect_missing',
    '1005': 'redirect_not_registered',
    '1007': 'client_secret_missing',
    '1008': 'code_missing',
    '1009': 'client_secret_unregistered',
    '1010': 'code_expired',
    '1011': 'access_token_missing',
    '1012': 'access_token_expired',
    '1014': 'process_error',
    '1015': 'access_token_error',
    '1016': 'profile_error',
    '1017': 'grant_type_missing',
    '1018': 'login_error',
    '1019': 'tgt_error',
    '1020': 'ticket_error',
    '1022': 'grant_type_invalid',
    '2019': 'authorization_error',
    '2022': 'client_not_registered',
    '80013': 'redirect_mismatch',
    '80014': 'user_not_allowed',
    '80015': 'client_invalid',
    '80021': 'upstream_timeout',
    '80022': 'login_error',
    '80023': 'app_disabled',
    '80026': 'upstream_error',
    '9090': 'client_not_registered',
}

# 这些错误表示「参数位置不对/缺少参数」，此时 code 尚未被消费，可安全重试
_RETRYABLE_PARAM_CODES = {'1002', '1003', '1007', '1008', '1011', '1017', '1022'}


class E10OAuthError(Exception):
    """E10 OAuth2 调用失败。"""

    def __init__(
        self,
        reason: str,
        message: str = '',
        *,
        stage: str = '',
        upstream_code: Optional[str] = None,
        http_status: Optional[int] = None,
    ) -> None:
        super().__init__(message or reason)
        self.reason = reason
        self.message = message
        self.stage = stage
        self.upstream_code = upstream_code
        self.http_status = http_status

    @property
    def public_reason(self) -> str:
        """返回给前端的安全错误代码（不包含 E10 原始 msg）。"""
        if self.reason.startswith('e10_'):
            return self.reason
        return f'e10_{self.reason}'

    def __str__(self) -> str:
        parts = [self.reason]
        if self.stage:
            parts.append(f'stage={self.stage}')
        if self.upstream_code:
            parts.append(f'upstream_code={self.upstream_code}')
        if self.http_status:
            parts.append(f'http={self.http_status}')
        if self.message:
            parts.append(self.message)
        return ' | '.join(parts)


@dataclass(frozen=True)
class E10AccessToken:
    access_token: str
    expires_in: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class E10Profile:
    """E10 /profile 返回结果。

    ``id`` 的含义由 E10 应用配置的「账号映射规则」决定，可能是
    loginId、email、mobile、工号、身份证号等。
    """

    id: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)


def _join_url(base: str, path: str) -> str:
    return f'{base.rstrip("/")}/{path.lstrip("/")}'


def _normalize_attributes(raw: Any) -> Dict[str, Any]:
    """
    归一化 E10 ``attributes``。

    兼容三种常见形态：
    - 字典：{"username": "张三", "job_num": "A1001"}
    - 列表：[{"name": "username", "value": "张三"}, ...]
    - 空值/其他：返回空字典
    """
    if isinstance(raw, dict):
        result: Dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                value = value.get('value', value.get('val', value))
            result[str(key)] = value
        return result

    if isinstance(raw, list):
        result = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            key = item.get('name') or item.get('key') or item.get('field') or item.get('code')
            value = item.get('value', item.get('val'))
            if key is not None and value is not None:
                result[str(key)] = value
        return result

    if isinstance(raw, str) and raw.strip().startswith(('{', '[')):
        try:
            return _normalize_attributes(json.loads(raw))
        except (TypeError, ValueError):
            return {}

    return {}


class E10Client:
    """轻量 E10 OAuth2 客户端（每个请求创建一个实例即可）。"""

    def __init__(self, cfg: E10Config) -> None:
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'SmartTable-E10-SSO/1.0',
        })

    # ------------------------------------------------------------------
    # URL 构造
    # ------------------------------------------------------------------
    def build_authorize_url(self, state: str = '', redirect_uri: str | None = None) -> str:
        params = {
            'client_id': self.cfg.client_id,
            'redirect_uri': redirect_uri or self.cfg.resolve_callback_url(),
            'response_type': 'code',
        }
        if state and self.cfg.send_state:
            params['state'] = state
        if self.cfg.scope:
            params['scope'] = self.cfg.scope
        return f'{_join_url(self.cfg.base_url, self.cfg.authorize_path)}?{urlencode(params)}'

    def build_logout_url(self, service_url: str) -> str:
        return (
            f'{_join_url(self.cfg.base_url, self.cfg.logout_path)}?'
            f'{urlencode({"service": service_url})}'
        )

    # ------------------------------------------------------------------
    # 核心调用
    # ------------------------------------------------------------------
    def exchange_code(self, code: str, redirect_uri: str | None = None) -> E10AccessToken:
        """用一次性授权码换取 access_token。"""
        if not code:
            raise E10OAuthError('code_missing', 'authorization code is empty', stage='token')

        payload = {
            'grant_type': 'authorization_code',
            'client_id': self.cfg.client_id,
            'client_secret': self.cfg.client_secret,
            'code': code,
            'redirect_uri': redirect_uri or self.cfg.resolve_callback_url(),
        }
        data = self._post(
            self.cfg.token_path,
            payload,
            self.cfg.token_param_style,
            stage='token',
        )
        access_token = data.get('access_token')
        if not access_token:
            raise E10OAuthError(
                'access_token_missing',
                'E10 token response has no access_token',
                stage='token',
            )
        expire = data.get('expire', data.get('expires_in'))
        try:
            expires_in = int(expire) if expire is not None else None
        except (TypeError, ValueError):
            expires_in = None
        return E10AccessToken(
            access_token=str(access_token),
            expires_in=expires_in,
            raw=data,
        )

    def fetch_profile(self, access_token: str) -> E10Profile:
        """用 access_token 获取当前登录人员在 E10 中的标识。"""
        if not access_token:
            raise E10OAuthError('access_token_missing', 'access token is empty', stage='profile')

        data = self._post(
            self.cfg.profile_path,
            {'access_token': access_token},
            self.cfg.profile_param_style,
            stage='profile',
        )
        user_id = data.get('id')
        if user_id is None or str(user_id).strip() == '':
            raise E10OAuthError(
                'profile_id_missing',
                'E10 profile response has no id',
                stage='profile',
            )
        attributes = _normalize_attributes(data.get('attributes'))
        # 某些 E10 版本会把自定义属性平铺在顶层，这里一并合并，保持向后兼容
        for key in (
            'username', 'userName', 'user_name', 'name',
            'job_num', 'jobNum', 'job_number',
            'mobile', 'phone', 'phone_number',
            'email', 'mail', 'avatar',
        ):
            if key in data and key not in attributes and data[key] is not None:
                attributes[key] = data[key]
        return E10Profile(
            id=str(user_id).strip(),
            attributes=attributes,
            raw=data,
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        style: str,
        *,
        stage: str,
    ) -> Dict[str, Any]:
        url = _join_url(self.cfg.base_url, path)
        styles = ['query', 'form'] if style == 'auto' else [style]
        last_error: Optional[E10OAuthError] = None

        for index, current_style in enumerate(styles):
            try:
                if current_style == 'query':
                    response = self.session.post(
                        url,
                        params=payload,
                        timeout=self.cfg.timeout,
                        verify=self._verify(),
                    )
                else:
                    response = self.session.post(
                        url,
                        data=payload,
                        timeout=self.cfg.timeout,
                        verify=self._verify(),
                    )
            except requests.Timeout as exc:
                raise E10OAuthError('timeout', str(exc), stage=stage) from exc
            except requests.RequestException as exc:
                raise E10OAuthError('network_error', str(exc), stage=stage) from exc

            data = self._decode(response, stage)
            if self._is_success(data):
                return data

            error = self._error_from_payload(data, response.status_code, stage)
            last_error = error

            # 仅在「参数位置错误」时切换 query/form；其他错误（code 失效等）
            # 不能重试，否则会掩盖真实问题。
            if (
                style == 'auto'
                and index == 0
                and error.upstream_code in _RETRYABLE_PARAM_CODES
            ):
                logger.warning(
                    '[E10] %s 接口在 %s 模式下返回参数错误 code=%s，自动切换参数位置重试',
                    stage,
                    current_style,
                    error.upstream_code,
                )
                continue
            raise error

        raise last_error or E10OAuthError('upstream_error', 'unknown E10 error', stage=stage)

    def _verify(self):
        if self.cfg.ca_bundle:
            return self.cfg.ca_bundle
        return self.cfg.verify_ssl

    @staticmethod
    def _decode(response: requests.Response, stage: str) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            try:
                data = json.loads(response.text)
            except (TypeError, ValueError) as exc:
                raise E10OAuthError(
                    'invalid_response',
                    f'HTTP {response.status_code}: {response.text[:200]}',
                    stage=stage,
                    http_status=response.status_code,
                ) from exc
        if not isinstance(data, dict):
            raise E10OAuthError(
                'invalid_response',
                f'unexpected JSON type: {type(data).__name__}',
                stage=stage,
                http_status=response.status_code,
            )
        return data

    @staticmethod
    def _is_success(data: Dict[str, Any]) -> bool:
        if data.get('error') or data.get('error_description'):
            return False
        code = data.get('code')
        status = data.get('status')
        if code not in (None, '', 0, '0', 200, '200'):
            return False
        if status not in (None, '', 0, '0', 200, '200'):
            return False
        return True

    @staticmethod
    def _error_from_payload(
        data: Dict[str, Any],
        http_status: int,
        stage: str,
    ) -> E10OAuthError:
        upstream_code = data.get('code')
        upstream_code_str = str(upstream_code).strip() if upstream_code is not None else ''
        reason = _REASON_BY_UPSTREAM_CODE.get(upstream_code_str, 'upstream_error')
        message = (
            data.get('msg')
            or data.get('message')
            or data.get('error_description')
            or f'HTTP {http_status}'
        )
        return E10OAuthError(
            reason,
            str(message),
            stage=stage,
            upstream_code=upstream_code_str or None,
            http_status=http_status,
        )
