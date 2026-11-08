"""
日期时间序列化工具

SQLite 等数据库驱动读取 DateTime(timezone=True) 列时会丢失 tzinfo，
返回 naive datetime。直接 .isoformat() 输出不带时区后缀的字符串，
前端 JavaScript new Date() 会按本地时间解析（ES 规范行为），导致时区偏差。

本模块提供统一的序列化函数，确保输出始终带 UTC 时区后缀 (+00:00)。
"""
from datetime import datetime, timezone


def serialize_datetime(dt: datetime | None) -> str | None:
    """将 datetime 序列化为带 UTC 时区后缀的 ISO 字符串

    - 若 dt 为 None，返回 None
    - 若 dt 为 naive datetime（tzinfo=None），假设为 UTC 并补上时区信息
    - 若 dt 已带时区信息（aware），保持原样输出

    示例:
        >>> serialize_datetime(None)
        None
        >>> serialize_datetime(datetime(2026, 11, 8, 7, 32, 4))  # naive
        '2026-11-08T07:32:04+00:00'
        >>> serialize_datetime(datetime(2026, 11, 8, 7, 32, 4, tzinfo=timezone.utc))  # aware
        '2026-11-08T07:32:04+00:00'
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
