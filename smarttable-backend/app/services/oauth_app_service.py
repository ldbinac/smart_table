"""
第三方应用（OAuthApp）服务

职责：
- 应用 CRUD 与密钥管理（client_secret 仅存哈希，明文仅在创建/重置时短暂返回）
- 以 Client Credentials 模式签发 JWT 访问令牌（复用 Flask-JWT-Extended）
- 令牌撤销（按 jti / 按应用），通过 ApiAppToken.revoked + Redis jti 黑名单实现即时失效
- 审计日志写入

所有令牌代表「应用自身服务账号」，不含终端用户信息。
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any

from flask import current_app
from flask_jwt_extended import create_access_token, decode_token
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, redis_client
from app.models.oauth_app import (
    OAuthApp,
    ApiAppToken,
    ApiAppAuditLog,
    generate_client_id,
    generate_client_secret,
)

# scope 白名单（写入型要求对应 write scope）
OAUTH_SCOPES = [
    'base:read',
    'table:read',
    'table:write',
    'record:read',
    'record:write',
    'field:read',
]


class OAuthAppService:
    """第三方应用服务类"""

    # ------------------------------------------------------------------ #
    # 应用 CRUD
    # ------------------------------------------------------------------ #
    @staticmethod
    def create_app(
        owner_id: str,
        app_name: str,
        allowed_bases: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        callback_url: Optional[str] = None,
        is_active: bool = True,
    ) -> Tuple[OAuthApp, str]:
        """
        创建第三方应用，返回 (应用实例, 明文 client_secret)

        明文 secret 仅在创建时返回一次，后续不可再取回。
        """
        client_id = generate_client_id()
        plain_secret = generate_client_secret()
        secret_hash = generate_password_hash(plain_secret)

        valid_scopes = OAuthAppService._normalize_scopes(scopes)

        app = OAuthApp(
            app_name=app_name,
            client_id=client_id,
            client_secret_hash=secret_hash,
            owner_id=uuid.UUID(str(owner_id)),
            callback_url=callback_url,
            allowed_bases=allowed_bases or [],
            scopes=' '.join(valid_scopes),
            is_active=is_active,
        )
        # 临时保存明文，供 to_dict(include_secret=True) 使用
        app._plain_secret = plain_secret

        db.session.add(app)
        db.session.commit()

        OAuthAppService.write_audit(str(app.id), 'app_create', f'创建应用 {app_name}', None)
        return app, plain_secret

    @staticmethod
    def update_app(
        app_id: str,
        app_name: Optional[str] = None,
        callback_url: Optional[str] = None,
        allowed_bases: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> OAuthApp:
        """更新应用配置"""
        app = OAuthAppService.get_app(app_id)
        if app is None:
            return None

        if app_name is not None:
            app.app_name = app_name
        if callback_url is not None:
            app.callback_url = callback_url
        if allowed_bases is not None:
            app.allowed_bases = [str(b) for b in allowed_bases]
        if scopes is not None:
            app.scopes = ' '.join(OAuthAppService._normalize_scopes(scopes))
        if is_active is not None:
            app.is_active = is_active

        db.session.commit()
        OAuthAppService.write_audit(str(app.id), 'app_update', f'更新应用 {app.app_name}', None)
        return app

    @staticmethod
    def get_app(app_id: str) -> Optional[OAuthApp]:
        try:
            return OAuthApp.query.get(uuid.UUID(str(app_id)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def get_app_by_client_id(client_id: str) -> Optional[OAuthApp]:
        return OAuthApp.query.filter_by(client_id=client_id).first()

    @staticmethod
    def list_apps(owner_id: Optional[str] = None) -> List[OAuthApp]:
        """列出应用；管理员可传 owner_id=None 获取全部"""
        query = OAuthApp.query
        if owner_id is not None:
            try:
                query = query.filter_by(owner_id=uuid.UUID(str(owner_id)))
            except (ValueError, TypeError):
                return []
        return query.order_by(OAuthApp.created_at.desc()).all()

    @staticmethod
    def delete_app(app_id: str) -> bool:
        """删除应用（级联删除令牌与审计日志）"""
        app = OAuthAppService.get_app(app_id)
        if app is None:
            return False
        name = app.app_name
        db.session.delete(app)
        db.session.commit()
        OAuthAppService.write_audit(str(app_id), 'app_delete', f'删除应用 {name}', None)
        return True

    @staticmethod
    def reset_secret(app_id: str) -> Optional[Tuple[OAuthApp, str]]:
        """重置 client_secret：生成新 secret，旧 secret（哈希）立即失效"""
        app = OAuthAppService.get_app(app_id)
        if app is None:
            return None

        plain_secret = generate_client_secret()
        app.client_secret_hash = generate_password_hash(plain_secret)
        app._plain_secret = plain_secret
        db.session.commit()

        OAuthAppService.write_audit(str(app.id), 'secret_reset', f'重置应用 {app.app_name} 密钥', None)
        return app, plain_secret

    # ------------------------------------------------------------------ #
    # 凭据校验
    # ------------------------------------------------------------------ #
    @staticmethod
    def verify_secret(client_id: str, client_secret: str) -> Optional[OAuthApp]:
        """校验 client_id / client_secret，成功返回应用实例"""
        app = OAuthAppService.get_app_by_client_id(client_id)
        if app is None:
            return None
        if not app.is_active:
            return None
        if not check_password_hash(app.client_secret_hash, client_secret):
            return None
        return app

    # ------------------------------------------------------------------ #
    # 令牌签发与撤销
    # ------------------------------------------------------------------ #
    @staticmethod
    def issue_token(app: OAuthApp, scopes: Optional[List[str]] = None) -> Tuple[str, ApiAppToken]:
        """
        为应用签发 JWT 访问令牌

        返回 (access_token, ApiAppToken 记录)。令牌 claim 含 client_id / app_id / scope / sub。
        """
        # 校验请求 scope 必须是应用被授予 scope 的子集
        granted = set(app.scopes.split()) if app.scopes else set()
        requested = OAuthAppService._normalize_scopes(scopes) if scopes else granted
        effective = sorted(set(requested) & granted)

        expires_seconds = int(current_app.config.get('OPEN_API_TOKEN_EXPIRES', 7200))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)

        access_token = create_access_token(
            identity=str(app.id),
            expires_delta=timedelta(seconds=expires_seconds),
            additional_claims={
                'client_id': app.client_id,
                'app_id': str(app.id),
                'scope': ' '.join(effective),
                'sub': str(app.id),
                'token_type': 'app',
            }
        )

        # 令牌由 Flask-JWT-Extended 自动生成 jti 断言，此处回读实际 jti，
        # 确保 ApiAppToken 记录的 jti 与 JWT 内嵌 jti 一致，撤销方能生效。
        jti = decode_token(access_token)['jti']
        token_record = ApiAppToken(
            jti=jti,
            app_id=app.id,
            scope=' '.join(effective),
            expires_at=expires_at,
            revoked=False,
        )
        db.session.add(token_record)
        db.session.commit()

        OAuthAppService.write_audit(str(app.id), 'token_issue', f'签发令牌 jti={jti}', None)
        return access_token, token_record

    @staticmethod
    def get_token_by_jti(jti: str) -> Optional[ApiAppToken]:
        return ApiAppToken.query.filter_by(jti=jti).first()

    @staticmethod
    def revoke_token_by_jti(jti: str) -> bool:
        """按 jti 撤销单个令牌（即时生效）"""
        token = ApiAppToken.query.filter_by(jti=jti).first()
        if token is None:
            return False
        revoked = OAuthAppService._revoke_token_record(token)
        if revoked:
            OAuthAppService.write_audit(str(token.app_id), 'token_revoke', f'撤销令牌 jti={jti}', None)
        return revoked

    @staticmethod
    def revoke_all_app_tokens(app_id: str) -> int:
        """撤销某应用的所有未过期令牌，返回撤销数量"""
        app = OAuthAppService.get_app(app_id)
        if app is None:
            return 0
        count = 0
        for token in app.tokens.filter_by(revoked=False).all():
            if OAuthAppService._revoke_token_record(token):
                count += 1
        OAuthAppService.write_audit(str(app.id), 'token_revoke_all', f'撤销全部令牌（{count} 个）', None)
        return count

    @staticmethod
    def _revoke_token_record(token: ApiAppToken) -> bool:
        if token.revoked:
            return False
        token.revoked = True
        db.session.commit()

        # 持久化黑名单：写入 TokenBlocklist（与用户令牌同表、同回调），
        # 保证撤销在 Redis 不可用时依然即时生效。
        from app.models.user import TokenBlocklist
        try:
            if TokenBlocklist.query.filter_by(jti=token.jti).first() is None:
                block = TokenBlocklist(
                    jti=token.jti,
                    token_type='app',
                    user_id=str(token.app_id),
                    expires_at=token.expires_at,
                )
                db.session.add(block)
                db.session.commit()
        except Exception as exc:
            current_app.logger.warning(f'[OAuthApp] 写入 TokenBlocklist 失败：{exc}')
            db.session.rollback()

        # Redis 黑名单：加入 jti，TTL 设为令牌剩余有效期，自动清理
        try:
            if redis_client is not None:
                ttl = int((token.expires_at - datetime.now(timezone.utc)).total_seconds())
                ttl = max(ttl, 1)
                redis_client.sadd('oauth:revoked_jti', token.jti)
                redis_client.expire('oauth:revoked_jti', ttl)
        except Exception:
            current_app.logger.warning(f'[OAuthApp] Redis 写入 jti 黑名单失败：jti={token.jti}')
        return True

    @staticmethod
    def list_app_tokens(app_id: str, include_revoked: bool = False) -> List[ApiAppToken]:
        app = OAuthAppService.get_app(app_id)
        if app is None:
            return []
        query = app.tokens
        if not include_revoked:
            query = query.filter_by(revoked=False)
        return query.order_by(ApiAppToken.created_at.desc()).all()

    # ------------------------------------------------------------------ #
    # 审计
    # ------------------------------------------------------------------ #
    @staticmethod
    def write_audit(app_id: Optional[str], action: str, detail: Optional[str], ip: Optional[str]) -> ApiAppAuditLog:
        """写入一条应用审计日志"""
        log = ApiAppAuditLog(
            app_id=uuid.UUID(str(app_id)) if app_id else None,
            action=action,
            detail=detail,
            ip=ip,
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def list_audit_logs(app_id: Optional[str] = None, limit: int = 100) -> List[ApiAppAuditLog]:
        query = ApiAppAuditLog.query
        if app_id is not None:
            try:
                query = query.filter_by(app_id=uuid.UUID(str(app_id)))
            except (ValueError, TypeError):
                return []
        return query.order_by(ApiAppAuditLog.created_at.desc()).limit(limit).all()

    # ------------------------------------------------------------------ #
    # 工具
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_scopes(scopes: Optional[List[str]]) -> List[str]:
        """过滤为合法 scope 列表（去重、保序）。

        入参既可能是空格分隔的字符串，也可能是字符串列表，需兼容处理。
        """
        if not scopes:
            return []
        if isinstance(scopes, str):
            scopes = scopes.split()
        seen = set()
        result = []
        for s in scopes:
            s = str(s).strip()
            if s and s in OAUTH_SCOPES and s not in seen:
                seen.add(s)
                result.append(s)
        return result

    @staticmethod
    def is_valid_scope(scope: str) -> bool:
        return scope in OAUTH_SCOPES
