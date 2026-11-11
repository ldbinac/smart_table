"""
复制记录后关联字段显示「关联 N 条」、导出为记录 ID 的回归测试。

根因：复制记录 / 批量创建 / 直接更新等写入路径把关联目标 ID 直接写进
record.values，但没有同步创建 LinkValue 关联记录。表格展示与前端导出
依赖 get_record_links（基于 LinkValue），显示名解析因此失败：
界面显示「关联 N 条」，导出退化为裸 UUID。
"""
import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import delete, select, and_

from app.extensions import db
from app.models import Base, Record, Table
from app.models.field import Field, FieldType
from app.models.link_relation import LinkValue, LinkRelation
from app.services.link_service import LinkService
from app.services.record_service import RecordService


@pytest.fixture
def link_sync_setup(app, db_session, test_user):
    base = Base(
        name='复制关联测试库', description='复制记录关联同步',
        icon='table', color='#6366f1', owner_id=test_user.id,
    )
    db.session.add(base)
    db.session.commit()

    target_table = Table(base_id=base.id, name='目标表', order=0)
    main_table = Table(base_id=base.id, name='主表', order=1)
    db.session.add_all([target_table, main_table])
    db.session.commit()

    target_name = Field(
        table_id=target_table.id, name='名称',
        type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
    )
    main_name = Field(
        table_id=main_table.id, name='关键结果',
        type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
    )
    link_field = Field(
        table_id=main_table.id, name='所属目标',
        type=FieldType.LINK_TO_RECORD.value, order=1,
        config={
            'linkedTableId': str(target_table.id),
            'displayFieldId': str(target_name.id),
            'bidirectional': True,
        },
    )
    db.session.add_all([target_name, main_name, link_field])
    db.session.commit()

    target = Record(
        table_id=target_table.id,
        values={str(target_name.id): '提升产品用户体验'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    source = Record(
        table_id=main_table.id,
        values={str(main_name.id): '用户满意度提升至4.5分'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    db.session.add_all([target, source])
    db.session.commit()

    return {
        'base': base,
        'target_table': target_table,
        'main_table': main_table,
        'target_name': target_name,
        'main_name': main_name,
        'link_field': link_field,
        'target': target,
        'source': source,
        'user': test_user,
    }


def _outbound_displays(links: dict, field_id) -> list:
    """get_record_links 返回 {field_id: [{target_record: 显示值, ...}]}"""
    displays = []
    for item in links.get(str(field_id)) or []:
        value = item.get('target_record')
        if value:
            displays.append(value)
    return displays


class TestCreateRecordSyncsLinks:

    def test_copied_values_create_link_value(self, link_sync_setup):
        s = link_sync_setup
        copied = RecordService.create_record(
            str(s['main_table'].id),
            {
                str(s['main_name'].id): '复制的记录',
                str(s['link_field'].id): [str(s['target'].id)],
            },
            created_by=str(s['user'].id),
        )

        links = LinkService.get_record_links(str(copied.id), use_cache=False)
        assert _outbound_displays(links, s['link_field'].id) == ['提升产品用户体验']
        # values 被规范化为关联目标 ID 列表
        assert list(copied.values.get(str(s['link_field'].id)) or []) == [str(s['target'].id)]

    def test_empty_link_value_kept_as_is(self, link_sync_setup):
        s = link_sync_setup
        copied = RecordService.create_record(
            str(s['main_table'].id),
            {str(s['main_name'].id): '无关联复制', str(s['link_field'].id): []},
            created_by=str(s['user'].id),
        )
        links = LinkService.get_record_links(str(copied.id), use_cache=False)
        assert _outbound_displays(links, s['link_field'].id) == []
        assert copied.values.get(str(s['link_field'].id)) == []

    def test_existing_bad_values_fallback_to_values_ids(self, link_sync_setup):
        """存量坏数据：values 有关联 ID 但 LinkValue 缺失（修复前复制产生）"""
        s = link_sync_setup
        copied = RecordService.create_record(
            str(s['main_table'].id),
            {
                str(s['main_name'].id): '历史复制的记录',
                str(s['link_field'].id): [str(s['target'].id)],
            },
            created_by=str(s['user'].id),
        )
        # 模拟修复前产生的坏数据：删掉 LinkValue，仅保留 values 中的 ID
        db.session.execute(
            delete(LinkValue).where(LinkValue.source_record_id == str(copied.id))
        )
        db.session.commit()

        links = LinkService.get_record_links(str(copied.id), use_cache=False)
        assert _outbound_displays(links, s['link_field'].id) == ['提升产品用户体验']


class TestUpdateRecordSyncsLinks:

    def test_update_with_link_values_creates_link_value(self, link_sync_setup):
        s = link_sync_setup
        record = RecordService.create_record(
            str(s['main_table'].id),
            {str(s['main_name'].id): '普通记录'},
            created_by=str(s['user'].id),
        )

        RecordService.update_record(
            record,
            {str(s['link_field'].id): [str(s['target'].id)]},
            updated_by=str(s['user'].id),
        )

        links = LinkService.get_record_links(str(record.id), use_cache=False)
        assert _outbound_displays(links, s['link_field'].id) == ['提升产品用户体验']


class TestBatchCreateSyncsLinks:

    def test_batch_create_syncs_link_values(self, app, client, link_sync_setup):
        s = link_sync_setup
        with app.app_context():
            token = create_access_token(identity=str(s['user'].id))

        resp = client.post(
            f'/api/tables/{s["main_table"].id}/records/batch',
            json={'records': [
                {
                    'values': {
                        str(s['main_name'].id): '粘贴行',
                        str(s['link_field'].id): [str(s['target'].id)],
                    },
                },
            ]},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200, resp.get_json()
        record_ids = resp.get_json()['data']['record_ids']

        links = LinkService.get_record_links(record_ids[0], use_cache=False)
        assert _outbound_displays(links, s['link_field'].id) == ['提升产品用户体验']


class TestCopyBidirectionalCardinality:

    @pytest.fixture
    def one_to_one_setup(self, app, db_session, test_user):
        base = Base(name='一对一复制测试库', owner_id=test_user.id)
        db.session.add(base)
        db.session.commit()
        target_table = Table(base_id=base.id, name='目标表', order=0)
        main_table = Table(base_id=base.id, name='主表', order=1)
        db.session.add_all([target_table, main_table])
        db.session.commit()

        target_name = Field(
            table_id=target_table.id, name='名称',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
        )
        main_name = Field(
            table_id=main_table.id, name='关键结果',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0, is_primary=True,
        )
        db.session.add_all([target_name, main_name])
        db.session.commit()

        # 用真实路径创建双向一对一关联字段（会创建反向字段与带 target_field_id 的关联）
        res = LinkService.create_link_field(
            str(main_table.id),
            {
                'name': '所属目标',
                'target_table_id': str(target_table.id),
                'relationship_type': 'one_to_one',
                'display_field_id': str(target_name.id),
                'bidirectional': True,
            },
            user_id=str(test_user.id),
        )
        assert res['success'], res
        link_field_id = res['field']['id']
        link_field = db.session.get(Field, link_field_id)

        target = Record(
            table_id=target_table.id, values={str(target_name.id): '提升产品用户体验'},
            created_by=test_user.id, updated_by=test_user.id,
        )
        source = Record(
            table_id=main_table.id, values={str(main_name.id): '用户满意度提升至4.5分'},
            created_by=test_user.id, updated_by=test_user.id,
        )
        db.session.add_all([target, source])
        db.session.commit()

        # 建立原始双向关联（一对一），使目标侧已有一条反向关联
        relation, _ = LinkService._get_or_create_link_relation_for_field(link_field)
        LinkService.update_link_values(
            str(relation.id), str(source.id), [str(target.id)], updated_by=str(test_user.id)
        )
        return {
            'base': base, 'target_table': target_table, 'main_table': main_table,
            'target_name': target_name, 'main_name': main_name, 'link_field': link_field,
            'target': target, 'source': source, 'relation': relation, 'user': test_user,
        }

    def test_one_to_one_copy_does_not_duplicate_target_backlink(self, one_to_one_setup):
        s = one_to_one_setup
        copied = RecordService.create_record(
            str(s['main_table'].id),
            {
                str(s['main_name'].id): '复制的记录',
                str(s['link_field'].id): [str(s['target'].id)],
            },
            created_by=str(s['user'].id),
        )

        # 复制出的记录不应建立该关联
        copy_links = LinkService.get_record_links(str(copied.id), use_cache=False)
        assert _outbound_displays(copy_links, s['link_field'].id) == []
        # values 中该字段被移除，避免单元格显示「关联 1 条」却无关联数据
        assert copied.values.get(str(s['link_field'].id)) is None

        # 原记录关联不被破坏
        orig_links = LinkService.get_record_links(str(s['source'].id), use_cache=False)
        assert _outbound_displays(orig_links, s['link_field'].id) == ['提升产品用户体验']

        # 目标侧反向关联仍只有 1 条（指向原记录），未因复制变成 2 条
        reverse_relation = db.session.execute(
            select(LinkRelation).where(
                and_(
                    LinkRelation.source_field_id == str(s['relation'].target_field_id),
                    LinkRelation.target_field_id == str(s['relation'].source_field_id),
                )
            )
        ).scalar_one_or_none()
        assert reverse_relation is not None
        backlink_count = db.session.execute(
            select(LinkValue).where(
                and_(
                    LinkValue.link_relation_id == reverse_relation.id,
                    LinkValue.source_record_id == str(s['target'].id),
                )
            )
        ).scalars().all()
        assert len(backlink_count) == 1
