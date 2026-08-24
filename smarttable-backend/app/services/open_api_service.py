"""
开放 API 服务（第三方应用以应用身份访问数据）

设计要点：
- 应用身份：通过 g.oauth_app 传入（由 @open_api_auth_required 设置），不依赖 g.current_user。
- 授权粒度：应用仅能访问其 allowed_bases 白名单内的 Base；越权返回 403。
- scope 检查在路由层由 @require_open_scope 完成，本服务聚焦「Base 授权校验 + 数据访问」。
- 应用以授权 Base 的「所有者视角」读写数据，记录的操作人记为应用 id（便于审计追溯）。

复用现有 RecordService / TableService / FieldService / Base 模型，不修改其内部逻辑。
"""
import uuid
from typing import Optional, List, Tuple, Any, Dict

from app.models.base import Base
from app.models.table import Table
from app.models.record import Record
from app.services.table_service import TableService
from app.services.field_service import FieldService
from app.services.record_service import RecordService

# 应用身份访问时，scope 检查在路由层完成；此处仅做 Base 授权校验
SCOPE_BASE_READ = 'base:read'
SCOPE_TABLE_READ = 'table:read'
SCOPE_FIELD_READ = 'field:read'
SCOPE_RECORD_READ = 'record:read'
SCOPE_RECORD_WRITE = 'record:write'


class OpenAPIError(Exception):
    """开放 API 业务错误（携带 i18n key 与 HTTP 状态码）"""

    def __init__(self, message_key: str, status: int = 403, error: str = 'forbidden'):
        self.message_key = message_key
        self.status = status
        self.error = error
        super().__init__(message_key)


class OpenAPIService:
    """第三方应用开放 API 服务类（静态方法）"""

    # ------------------------------------------------------------------ #
    # 授权校验
    # ------------------------------------------------------------------ #
    @staticmethod
    def assert_base_authorized(app, base_id: str) -> Base:
        """校验应用是否获得该 Base 的访问授权，返回 Base 实例或抛出 OpenAPIError"""
        try:
            base_uuid = uuid.UUID(str(base_id))
        except (ValueError, TypeError):
            raise OpenAPIError('oauth_base_not_authorized', status=404, error='not_found')

        allowed = set(str(b) for b in (app.allowed_bases or []))
        if str(base_uuid) not in allowed:
            raise OpenAPIError('oauth_base_not_authorized', status=403, error='forbidden')

        base = Base.query.get(base_uuid)
        if base is None:
            raise OpenAPIError('oauth_base_not_authorized', status=404, error='not_found')
        return base

    @staticmethod
    def assert_table_belongs_to_base(base_id: str, table_id: str) -> Table:
        """校验表属于该 Base，返回 Table 实例或抛出 OpenAPIError"""
        try:
            table = TableService.get_table(str(table_id))
        except Exception:
            table = None
        if table is None or str(getattr(table, 'base_id', None)) != str(base_id):
            raise OpenAPIError('resource_not_found', status=404, error='not_found')
        return table

    @staticmethod
    def assert_record_belongs(table_id: str, record_id: str) -> Record:
        """校验记录存在且属于该表，返回 Record 实例或抛出 OpenAPIError"""
        record = RecordService.get_record_by_id(str(record_id))
        if record is None or str(getattr(record, 'table_id', None)) != str(table_id):
            raise OpenAPIError('resource_not_found', status=404, error='not_found')
        return record

    # ------------------------------------------------------------------ #
    # Base 元数据
    # ------------------------------------------------------------------ #
    @staticmethod
    def list_bases(app) -> List[Dict[str, Any]]:
        """列出应用授权访问的 Base（按 allowed_bases 过滤）"""
        allowed_ids = [uuid.UUID(str(b)) for b in (app.allowed_bases or [])]
        if not allowed_ids:
            return []
        bases = Base.query.filter(Base.id.in_(allowed_ids)).all()
        return [b.to_dict() for b in bases]

    @staticmethod
    def get_base(app, base_id: str) -> Dict[str, Any]:
        """获取单个授权 Base 详情"""
        base = OpenAPIService.assert_base_authorized(app, base_id)
        return base.to_dict()

    # ------------------------------------------------------------------ #
    # 表 / 字段元数据
    # ------------------------------------------------------------------ #
    @staticmethod
    def list_tables(app, base_id: str) -> List[Dict[str, Any]]:
        """列出 Base 下的所有表"""
        OpenAPIService.assert_base_authorized(app, base_id)
        tables = TableService.get_all_tables(str(base_id))
        return [t.to_dict() for t in tables]

    @staticmethod
    def get_table(app, base_id: str, table_id: str) -> Dict[str, Any]:
        """获取单个表详情"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        table = TableService.get_table(str(table_id))
        return table.to_dict()

    @staticmethod
    def list_fields(app, base_id: str, table_id: str) -> List[Dict[str, Any]]:
        """列出表的所有字段（结构元数据）"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        fields = FieldService.get_all_fields(str(table_id))
        return [f.to_dict() for f in fields]

    # ------------------------------------------------------------------ #
    # 记录查询
    # ------------------------------------------------------------------ #
    @staticmethod
    def list_records(
        app,
        base_id: str,
        table_id: str,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """分页列出表记录"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        records, total = RecordService.get_table_records(
            table_id=str(table_id),
            page=page,
            per_page=per_page,
        )
        return [r.to_dict() for r in records], total

    @staticmethod
    def search_records(app, base_id: str, table_id: str, query: str) -> List[Dict[str, Any]]:
        """在表中搜索记录"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        # 必须按字段逐列匹配（部分数据库对整列 JSON 的 ilike 失效），
        # 传入表内全部字段 id 以保证跨字段搜索正确。
        fields = FieldService.get_all_fields(str(table_id))
        field_ids = [str(f.id) for f in fields]
        records = RecordService.search_records(
            table_id=str(table_id),
            query=query,
            field_ids=field_ids,
        )
        return [r.to_dict() for r in records]

    @staticmethod
    def get_record(app, base_id: str, table_id: str, record_id: str) -> Dict[str, Any]:
        """获取单条记录详情"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        record = OpenAPIService.assert_record_belongs(table_id, record_id)
        return record.to_dict()

    # ------------------------------------------------------------------ #
    # 记录写操作
    # ------------------------------------------------------------------ #
    @staticmethod
    def create_record(
        app,
        base_id: str,
        table_id: str,
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建记录，操作者记为应用 id"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        record = RecordService.create_record(
            table_id=str(table_id),
            values=values or {},
            created_by=str(app.id),
        )
        return record.to_dict()

    @staticmethod
    def update_record(
        app,
        base_id: str,
        table_id: str,
        record_id: str,
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新记录，操作者记为应用 id"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        record = OpenAPIService.assert_record_belongs(table_id, record_id)
        record = RecordService.update_record(
            record=record,
            values=values or {},
            updated_by=str(app.id),
        )
        return record.to_dict()

    @staticmethod
    def delete_record(app, base_id: str, table_id: str, record_id: str) -> bool:
        """删除记录，操作者记为应用 id"""
        OpenAPIService.assert_base_authorized(app, base_id)
        OpenAPIService.assert_table_belongs_to_base(base_id, table_id)
        record = OpenAPIService.assert_record_belongs(table_id, record_id)
        return RecordService.delete_record(record=record, deleted_by=str(app.id))
