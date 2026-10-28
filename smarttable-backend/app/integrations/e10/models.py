"""
E10 身份映射模型。

该表只由本集成使用，不修改上游 ``users`` 表结构。
表会在首次登录时按需创建（``checkfirst=True``），也可通过
``schema.sql.example`` 手工创建。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db_types import CompatJSON, CompatUUID
from app.extensions import db

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class E10Identity(db.Model):
    """E10 人员标识与 SmartTable 用户的绑定关系。"""

    __tablename__ = 'e10_sso_identities'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # E10 /profile 返回的 id，其含义由 E10「账号映射规则」决定
    e10_user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        CompatUUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    e10_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # E10 返回的 attributes（目前文档说明暂不返回，保留以兼容后续版本）
    attributes: Mapped[Optional[dict]] = mapped_column(CompatJSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship('User', lazy='joined')

    @classmethod
    def ensure_schema(cls) -> None:
        """
        幂等创建本集成专用表。

        只创建 ``e10_sso_identities``，不触碰上游表；``checkfirst=True``
        在 SQLite / PostgreSQL 上均表现为「不存在才创建」。
        """
        cls.__table__.create(bind=db.engine, checkfirst=True)

    def __repr__(self) -> str:  # pragma: no cover - 仅调试使用
        return f'<E10Identity {self.e10_user_id} -> {self.user_id}>'
