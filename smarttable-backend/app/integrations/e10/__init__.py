"""
泛微 E10 OAuth2 单点登录集成入口。

上游 ``app/__init__.py`` 只需要调用一次::

    from app.integrations.e10 import register_e10_integration
    register_e10_integration(app)

本模块负责：
- 读取 E10_* 配置；
- 注册 ``/api/integrations/e10`` 蓝图；
- 首次登录时按需创建 ``e10_sso_identities`` 表（开发环境 ``db.create_all`` 会直接建表）。
"""
from __future__ import annotations

import logging

from flask import Flask

from .config import E10Config
from .models import E10Identity  # noqa: F401  确保模型进入 db.metadata
from .routes import e10_bp

logger = logging.getLogger(__name__)

_BLUEPRINT_NAME = e10_bp.name


def register_e10_integration(app: Flask) -> E10Config:
    """注册 E10 SSO 集成；重复调用是幂等的。"""
    cfg = E10Config.from_app(app)
    app.extensions['e10_integration'] = cfg

    if _BLUEPRINT_NAME not in app.blueprints:
        app.register_blueprint(e10_bp, url_prefix='/api/integrations/e10')

    if not cfg.enabled:
        logger.info('[E10] SSO 集成未启用（设置 E10_SSO_ENABLED=true 开启）')
        return cfg

    if not cfg.ready:
        logger.warning(
            '[E10] SSO 已启用但配置不完整，缺少: %s',
            ', '.join(cfg.missing) or 'unknown',
        )
        return cfg

    logger.info('[E10] SSO 集成已启用: base_url=%s', cfg.base_url)

    if cfg.enforce_sso:
        _install_local_auth_guard(app)

    if cfg.auto_create_schema:
        with app.app_context():
            try:
                # 关键：全新数据库在 run.py 迁移前只有部分表时，不能抢先创建本表，
                # 否则会让迁移误判为“旧库”而跳过 db.create_all()。
                # 仅在 users 表已存在（数据库已初始化）时预创建；否则延迟到首次登录。
                from sqlalchemy import inspect

                from app.extensions import db

                if inspect(db.engine).has_table('users'):
                    E10Identity.ensure_schema()
                else:
                    logger.info('[E10] users 表尚未创建，e10_sso_identities 将在首次登录时创建')
            except Exception as exc:
                # 首次启动时数据库可能尚未初始化；登录时会再次尝试
                logger.warning(
                    '[E10] 启动时创建 e10_sso_identities 表失败，将在首次登录时重试: %s',
                    exc,
                )
    return cfg


def _install_local_auth_guard(app: Flask) -> None:
    """E10_ENFORCE_SSO=true 时，在服务端禁用本地账号密码登录/注册 API。"""
    if app.extensions.get('e10_local_auth_guard'):
        return

    from flask import request

    from app.utils.response import error_response

    from .i18n import t

    @app.before_request
    def _block_local_auth():
        path = (request.path or '').rstrip('/')
        if path in ('/api/auth/login', '/api/auth/register'):
            return error_response(
                t('e10_sso_only_login'),
                code=403,
                error='e10_sso_only',
            )

    app.extensions['e10_local_auth_guard'] = True
    logger.info('[E10] 已强制仅允许 E10 单点登录（本地登录/注册 API 已禁用）')
