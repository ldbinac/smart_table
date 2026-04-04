"""
数据库类型兼容层
提供跨 PostgreSQL / SQLite 的类型兼容支持
解决测试环境使用 SQLite 时 psycopg2 未安装的导入错误
"""
import uuid
from typing import Any

from sqlalchemy import String, TypeDecorator


class CompatUUID(TypeDecorator):
    """
    兼容 UUID 类型
    
    PostgreSQL: 使用原生 UUID 类型
    SQLite/其他: 使用 String(36) 存储
    """
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            try:
                from sqlalchemy.dialects.postgresql import UUID as PG_UUID
                return dialect.type_descriptor(PG_UUID(as_uuid=True))
            except ImportError:
                pass
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, str):
            try:
                uuid.UUID(value)
                return value
            except ValueError:
                raise ValueError(f"Invalid UUID string: {value}")
        raise ValueError(f"Expected UUID or str, got {type(value)}")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        return uuid.UUID(str(value))


class CompatJSON(TypeDecorator):
    """
    兼容 JSON 类型
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            try:
                from sqlalchemy.dialects.postgresql import JSON as PG_JSON
                return dialect.type_descriptor(PG_JSON())
            except ImportError:
                pass
        return dialect.type_descriptor(String)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        import json
        return json.dumps(value, ensure_ascii=False, default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        import json
        if isinstance(value, dict | list):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
