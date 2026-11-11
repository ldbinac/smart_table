"""
Issue #IKUAYB 评论问题回归测试：水果表反向关联字段显示「关联 1 条」/ 弹窗显示 UUID。

覆盖后端显示值解析：
- 反向字段缺少 displayFieldId 时，不能用对端表（inverseField）的展示字段
  去当前记录取值，也不能把记录 ID（UUID）当成显示名返回；
- 自动创建双向关联反向字段时，即使源表没有 primary_field_id，
  也必须给出一个可用的 displayFieldId。
"""
import uuid

import pytest

from app.extensions import db
from app.models import Base, Record, Table
from app.models.field import Field, FieldType
from app.services.link_service import LinkService


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


@pytest.fixture
def display_setup(app, db_session, test_user):
    base = Base(
        name='显示值测试库', description='反向关联显示值',
        icon='table', color='#6366f1', owner_id=test_user.id,
    )
    db.session.add(base)
    db.session.commit()

    fruit_table = Table(base_id=base.id, name='水果表', order=0)
    price_table = Table(base_id=base.id, name='价格表', order=1)
    db.session.add_all([fruit_table, price_table])
    db.session.commit()

    fruit_name = Field(
        table_id=fruit_table.id, name='名称',
        type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
    )
    serial = Field(
        table_id=price_table.id, name='序号',
        type=FieldType.AUTO_NUMBER.value, order=0, is_primary=True,
    )
    db.session.add_all([fruit_name, serial])
    db.session.commit()
    price_table.primary_field_id = serial.id
    db.session.commit()

    # 正向字段：展示字段指向水果表的「名称」
    forward = Field(
        table_id=price_table.id, name='水果种类',
        type=FieldType.LINK_TO_RECORD.value, order=1,
        config={
            'linkedTableId': str(fruit_table.id),
            'displayFieldId': str(fruit_name.id),
        },
    )
    db.session.add(forward)
    db.session.commit()

    # 反向字段：没有 displayFieldId，只配置了 inverseFieldId
    inverse = Field(
        table_id=fruit_table.id, name='价格表',
        type=FieldType.LINK_TO_RECORD.value, order=1,
        config={
            'linkedTableId': str(price_table.id),
            'inverseFieldId': str(forward.id),
            'bidirectional': True,
        },
    )
    # 无任何展示配置的反向字段（模拟老数据）
    inverse_plain = Field(
        table_id=fruit_table.id, name='价格表(旧)',
        type=FieldType.LINK_TO_RECORD.value, order=2,
        config={'linkedTableId': str(price_table.id)},
    )
    db.session.add_all([inverse, inverse_plain])
    db.session.commit()

    p1 = Record(
        table_id=price_table.id,
        # 人为放入对端表展示字段的 ID 作为 key，验证不会被跨表误读
        values={str(fruit_name.id): '错误的水果名', str(serial.id): '2026-1'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    p2 = Record(
        table_id=price_table.id,
        values={
            str(serial.id): '',
            'raw-id': 'a874fc42-c70b-45dd-93a6-cc61652f9b01',
            str(forward.id): [str(uuid.uuid4())],
        },
        created_by=test_user.id, updated_by=test_user.id,
    )
    db.session.add_all([p1, p2])
    db.session.commit()

    return {
        'base': base,
        'fruit_table': fruit_table,
        'price_table': price_table,
        'fruit_name': fruit_name,
        'serial': serial,
        'forward': forward,
        'inverse': inverse,
        'inverse_plain': inverse_plain,
        'p1': p1,
        'p2': p2,
        'user': test_user,
    }


class TestGetLinkDisplayValueFallback:

    def test_inverse_field_does_not_use_cross_table_display_field(self, display_setup):
        s = display_setup
        value = LinkService._get_link_display_value(s['p1'], str(s['inverse'].id))
        assert value == '2026-1'
        assert value != '错误的水果名'
        assert not _is_uuid(value)

    def test_record_id_scalar_is_not_used_as_display_value(self, display_setup):
        s = display_setup
        value = LinkService._get_link_display_value(s['p2'], str(s['inverse_plain'].id))
        assert not _is_uuid(value)
        assert value != 'a874fc42-c70b-45dd-93a6-cc61652f9b01'

    def test_configured_display_field_still_wins(self, display_setup):
        s = display_setup
        record = Record(
            table_id=s['price_table'].id,
            values={str(s['fruit_name'].id): '苹果'},
        )
        value = LinkService._get_link_display_value(record, str(s['forward'].id))
        assert value == '苹果'


class TestCreateBidirectionalField:

    def test_inverse_field_has_display_field_without_primary_field(self, display_setup):
        s = display_setup
        # 模拟源表未维护 primary_field_id 的历史数据
        s['price_table'].primary_field_id = None
        db.session.commit()

        result = LinkService.create_link_field(
            str(s['price_table'].id),
            {
                'name': '新建关联',
                'target_table_id': str(s['fruit_table'].id),
                'relationship_type': 'many_to_many',
                'bidirectional': True,
            },
            user_id=str(s['user'].id),
        )
        assert result['success'] is True, result
        inverse = result['inverse_field']
        assert inverse is not None
        display_field_id = (inverse.get('config') or {}).get('displayFieldId')
        assert display_field_id, '反向字段缺少 displayFieldId'

        display_field = db.session.get(Field, display_field_id)
        assert display_field is not None
        assert str(display_field.table_id) == str(s['price_table'].id)
