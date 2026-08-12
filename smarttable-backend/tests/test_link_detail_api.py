"""
主从表（主从关联）后端接口单元测试

覆盖范围：
- LinkService.get_linked_records_detail：正常返回、关键词过滤、分页、错误处理
- LinkService.create_and_link_record：正常创建并关联、一对一关系限制
- API 路由 GET /records/<id>/links/<field_id>/details：返回正确格式
- API 路由 POST /records/<id>/links/<field_id>/records：创建并关联
"""
import uuid

import pytest

from app.extensions import db
from app.models import Base, Record, Table
from app.models.field import Field, FieldType
from app.models.link_relation import LinkRelation, LinkValue, RelationshipType
from app.services.link_service import LinkService


# ======================================================================
# 公共 fixture：构造主从表关联测试数据
# ======================================================================

@pytest.fixture
def link_setup(app, db_session, test_user):
    """创建主从表关联测试数据：源表 + 目标表 + 关联字段 + 关联关系 + 记录 + 关联值"""
    base = Base(
        name='主从表测试库', description='主从表测试',
        icon='table', color='#6366f1', owner_id=test_user.id,
    )
    db.session.add(base)
    db.session.commit()

    # 源表（主表）和目标表（从表）
    source_table = Table(base_id=base.id, name='主表', order=0)
    target_table = Table(base_id=base.id, name='从表', order=1)
    db.session.add_all([source_table, target_table])
    db.session.commit()

    # 源表主字段
    source_primary = Field(
        table_id=source_table.id, name='名称',
        type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
    )
    db.session.add(source_primary)
    db.session.commit()
    source_table.primary_field_id = source_primary.id
    db.session.commit()

    # 目标表主字段
    target_primary = Field(
        table_id=target_table.id, name='任务名',
        type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
    )
    db.session.add(target_primary)
    db.session.commit()
    target_table.primary_field_id = target_primary.id
    db.session.commit()

    # 源表上的关联字段，config 指向目标表
    link_field = Field(
        table_id=source_table.id, name='关联任务',
        type=FieldType.LINK_TO_RECORD.value, order=1,
        config={
            'linkedTableId': str(target_table.id),
            'relationshipType': RelationshipType.ONE_TO_MANY.value,
        },
    )
    db.session.add(link_field)
    db.session.commit()

    # 关联关系（一对多，非双向）
    link_relation = LinkRelation(
        source_table_id=source_table.id,
        target_table_id=target_table.id,
        source_field_id=link_field.id,
        target_field_id=None,
        relationship_type=RelationshipType.ONE_TO_MANY.value,
        bidirectional=False,
    )
    db.session.add(link_relation)
    db.session.commit()

    # 源表记录
    source_record = Record(
        table_id=source_table.id,
        values={str(source_primary.id): '主记录A'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    db.session.add(source_record)

    # 目标表记录
    target_record_1 = Record(
        table_id=target_table.id,
        values={str(target_primary.id): '子任务一'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    target_record_2 = Record(
        table_id=target_table.id,
        values={str(target_primary.id): '子任务二'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    db.session.add_all([target_record_1, target_record_2])
    db.session.commit()

    # 关联值：source_record -> target_record_1 / target_record_2
    lv1 = LinkValue(
        link_relation_id=link_relation.id,
        source_record_id=source_record.id,
        target_record_id=target_record_1.id,
    )
    lv2 = LinkValue(
        link_relation_id=link_relation.id,
        source_record_id=source_record.id,
        target_record_id=target_record_2.id,
    )
    db.session.add_all([lv1, lv2])
    db.session.commit()

    return {
        'base': base,
        'source_table': source_table,
        'target_table': target_table,
        'source_primary': source_primary,
        'target_primary': target_primary,
        'link_field': link_field,
        'link_relation': link_relation,
        'source_record': source_record,
        'target_record_1': target_record_1,
        'target_record_2': target_record_2,
    }


# ======================================================================
# LinkService.get_linked_records_detail
# ======================================================================

class TestGetLinkedRecordsDetail:
    """get_linked_records_detail 服务方法测试"""

    def test_returns_linked_records(self, app, link_setup):
        """正常返回关联记录详情"""
        data = link_setup
        result, err = LinkService.get_linked_records_detail(
            record_id=str(data['source_record'].id),
            field_id=str(data['link_field'].id),
        )
        assert err is None
        assert result is not None

        # 总数为 2
        assert result['total'] == 2
        assert len(result['records']) == 2

        # fields 包含目标表字段
        field_ids = [f['id'] for f in result['fields']]
        assert str(data['target_primary'].id) in field_ids

        # link_relation 正确
        assert result['link_relation']['id'] == str(data['link_relation'].id)

        # 每条记录包含完整字段
        record_ids = [r['id'] for r in result['records']]
        assert str(data['target_record_1'].id) in record_ids
        assert str(data['target_record_2'].id) in record_ids
        for r in result['records']:
            assert 'values' in r
            assert 'created_at' in r
            assert 'updated_at' in r

        # 分页字段
        assert result['page'] == 1
        assert result['per_page'] == 50

    def test_keyword_filter(self, app, link_setup):
        """关键词对主字段值进行模糊过滤"""
        data = link_setup
        result, err = LinkService.get_linked_records_detail(
            record_id=str(data['source_record'].id),
            field_id=str(data['link_field'].id),
            keyword='一',
        )
        assert err is None
        assert result['total'] == 1
        assert result['records'][0]['id'] == str(data['target_record_1'].id)

    def test_keyword_no_match(self, app, link_setup):
        """关键词无匹配时返回空"""
        data = link_setup
        result, err = LinkService.get_linked_records_detail(
            record_id=str(data['source_record'].id),
            field_id=str(data['link_field'].id),
            keyword='不存在的关键词',
        )
        assert err is None
        assert result['total'] == 0
        assert result['records'] == []

    def test_pagination(self, app, link_setup):
        """分页返回"""
        data = link_setup
        result, err = LinkService.get_linked_records_detail(
            record_id=str(data['source_record'].id),
            field_id=str(data['link_field'].id),
            page=1, per_page=1,
        )
        assert err is None
        assert result['total'] == 2
        assert len(result['records']) == 1
        assert result['page'] == 1
        assert result['per_page'] == 1

    def test_nonexistent_field(self, app, link_setup):
        """不存在的字段返回错误"""
        result, err = LinkService.get_linked_records_detail(
            record_id=str(link_setup['source_record'].id),
            field_id=str(uuid.uuid4()),
        )
        assert result is None
        assert err == '字段不存在'

    def test_non_link_field(self, app, link_setup):
        """非关联字段返回错误"""
        data = link_setup
        result, err = LinkService.get_linked_records_detail(
            record_id=str(data['source_record'].id),
            field_id=str(data['source_primary'].id),  # 文本字段
        )
        assert result is None
        assert '不是关联类型' in err

    def test_nonexistent_record_returns_empty(self, app, link_setup):
        """不存在的源记录返回空结果（不报错）"""
        result, err = LinkService.get_linked_records_detail(
            record_id=str(uuid.uuid4()),
            field_id=str(link_setup['link_field'].id),
        )
        assert err is None
        assert result['total'] == 0
        assert result['records'] == []

    def test_no_link_relation(self, app, link_setup):
        """关联关系不存在返回错误"""
        data = link_setup
        # 创建一个新的关联字段但不创建 LinkRelation
        new_link_field = Field(
            table_id=data['source_table'].id, name='未关联的字段',
            type=FieldType.LINK_TO_RECORD.value, order=2,
            config={'linkedTableId': str(data['target_table'].id)},
        )
        db.session.add(new_link_field)
        db.session.commit()
        result, err = LinkService.get_linked_records_detail(
            record_id=str(data['source_record'].id),
            field_id=str(new_link_field.id),
        )
        assert result is None
        assert err == '关联关系不存在'


# ======================================================================
# LinkService.create_and_link_record
# ======================================================================

class TestCreateAndLinkRecord:
    """create_and_link_record 服务方法测试"""

    def test_creates_and_links(self, app, link_setup, test_user):
        """正常创建记录并建立关联（一对多，追加到现有关联）"""
        data = link_setup
        target_primary_id = str(data['target_primary'].id)

        result, err = LinkService.create_and_link_record(
            source_record_id=str(data['source_record'].id),
            field_id=str(data['link_field'].id),
            values={target_primary_id: '新子任务'},
            user_id=str(test_user.id),
        )
        assert err is None
        assert result is not None

        # 新记录的值正确
        assert result['record']['values'][target_primary_id] == '新子任务'
        # 关联值已建立
        assert result['link_value'] is not None
        assert result['link_value']['source_record_id'] == str(data['source_record'].id)
        assert result['link_value']['target_record_id'] == result['record']['id']

        # 原有 2 条关联 + 新增 1 条 = 3 条（验证追加而非覆盖）
        detail, detail_err = LinkService.get_linked_records_detail(
            record_id=str(data['source_record'].id),
            field_id=str(data['link_field'].id),
        )
        assert detail_err is None
        assert detail['total'] == 3

    def test_one_to_one_constraint(self, app, link_setup, test_user):
        """一对一关系限制：源记录已有关联时拒绝再次创建"""
        data = link_setup
        # 将关联关系改为一对一
        data['link_relation'].relationship_type = RelationshipType.ONE_TO_ONE.value
        db.session.commit()
        # source_record 已经存在关联值，应被拦截
        result, err = LinkService.create_and_link_record(
            source_record_id=str(data['source_record'].id),
            field_id=str(data['link_field'].id),
            values={str(data['target_primary'].id): '新子任务'},
            user_id=str(test_user.id),
        )
        assert result is None
        assert '一对一' in err

    def test_one_to_one_allows_first(self, app, db_session, test_user):
        """一对一关系：无关联时允许创建"""
        base = Base(
            name='一对一测试库', icon='table', color='#6366f1', owner_id=test_user.id,
        )
        db.session.add(base)
        db.session.commit()

        source_table = Table(base_id=base.id, name='主表', order=0)
        target_table = Table(base_id=base.id, name='从表', order=1)
        db.session.add_all([source_table, target_table])
        db.session.commit()

        source_primary = Field(
            table_id=source_table.id, name='名称',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
        )
        db.session.add(source_primary)
        db.session.commit()
        source_table.primary_field_id = source_primary.id

        target_primary = Field(
            table_id=target_table.id, name='任务名',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
        )
        db.session.add(target_primary)
        db.session.commit()
        target_table.primary_field_id = target_primary.id
        db.session.commit()

        link_field = Field(
            table_id=source_table.id, name='关联任务',
            type=FieldType.LINK_TO_RECORD.value, order=1,
            config={'linkedTableId': str(target_table.id)},
        )
        db.session.add(link_field)
        db.session.commit()

        link_relation = LinkRelation(
            source_table_id=source_table.id,
            target_table_id=target_table.id,
            source_field_id=link_field.id,
            target_field_id=None,
            relationship_type=RelationshipType.ONE_TO_ONE.value,
            bidirectional=False,
        )
        db.session.add(link_relation)
        db.session.commit()

        source_record = Record(
            table_id=source_table.id,
            values={str(source_primary.id): '主记录'},
            created_by=test_user.id, updated_by=test_user.id,
        )
        db.session.add(source_record)
        db.session.commit()

        # 无关联时，一对一允许创建
        result, err = LinkService.create_and_link_record(
            source_record_id=str(source_record.id),
            field_id=str(link_field.id),
            values={str(target_primary.id): '唯一子任务'},
            user_id=str(test_user.id),
        )
        assert err is None
        assert result is not None
        assert result['record']['values'][str(target_primary.id)] == '唯一子任务'

    def test_nonexistent_field(self, app, link_setup, test_user):
        """不存在的字段返回错误"""
        data = link_setup
        result, err = LinkService.create_and_link_record(
            source_record_id=str(data['source_record'].id),
            field_id=str(uuid.uuid4()),
            values={},
            user_id=str(test_user.id),
        )
        assert result is None
        assert err == '字段不存在'


# ======================================================================
# API 路由测试
# ======================================================================

class TestLinkDetailAPI:
    """主从表 API 路由测试"""

    def test_get_details_api(self, client, auth_headers, link_setup):
        """GET /records/<id>/links/<field_id>/details 返回正确格式"""
        data = link_setup
        response = client.get(
            f'/api/records/{data["source_record"].id}/links/{data["link_field"].id}/details',
            headers=auth_headers,
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True

        result = json_data['data']
        assert result['total'] == 2
        assert len(result['records']) == 2
        assert len(result['fields']) >= 1
        assert 'link_relation' in result
        assert result['link_relation']['id'] == str(data['link_relation'].id)
        # 每条记录包含完整字段
        for r in result['records']:
            assert 'id' in r
            assert 'values' in r
            assert 'created_at' in r
            assert 'updated_at' in r

    def test_get_details_api_with_keyword(self, client, auth_headers, link_setup):
        """GET 接口支持关键词过滤"""
        data = link_setup
        response = client.get(
            f'/api/records/{data["source_record"].id}/links/{data["link_field"].id}/details?keyword=一',
            headers=auth_headers,
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['data']['total'] == 1
        assert json_data['data']['records'][0]['id'] == str(data['target_record_1'].id)

    def test_get_details_api_record_not_found(self, client, auth_headers, link_setup):
        """GET 接口源记录不存在返回 404"""
        response = client.get(
            f'/api/records/{uuid.uuid4()}/links/{link_setup["link_field"].id}/details',
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_details_api_non_link_field(self, client, auth_headers, link_setup):
        """GET 接口非关联字段返回 400"""
        data = link_setup
        response = client.get(
            f'/api/records/{data["source_record"].id}/links/{data["source_primary"].id}/details',
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_create_and_link_api(self, client, auth_headers, link_setup):
        """POST /records/<id>/links/<field_id>/records 创建并关联"""
        data = link_setup
        target_primary_id = str(data['target_primary'].id)
        response = client.post(
            f'/api/records/{data["source_record"].id}/links/{data["link_field"].id}/records',
            json={'values': {target_primary_id: 'API新建子任务'}},
            headers=auth_headers,
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['data']['record']['values'][target_primary_id] == 'API新建子任务'
        assert json_data['data']['link_value'] is not None

        # 验证通过 details 接口可查到新记录
        detail_response = client.get(
            f'/api/records/{data["source_record"].id}/links/{data["link_field"].id}/details',
            headers=auth_headers,
        )
        assert detail_response.status_code == 200
        assert detail_response.get_json()['data']['total'] == 3

    def test_create_and_link_api_record_not_found(self, client, auth_headers, link_setup):
        """POST 接口源记录不存在返回 404"""
        data = link_setup
        response = client.post(
            f'/api/records/{uuid.uuid4()}/links/{data["link_field"].id}/records',
            json={'values': {}},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_and_link_api_no_body(self, client, auth_headers, link_setup):
        """POST 接口请求体为空对象返回 400"""
        data = link_setup
        response = client.post(
            f'/api/records/{data["source_record"].id}/links/{data["link_field"].id}/records',
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400
