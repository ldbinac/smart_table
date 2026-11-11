"""
Issue #IKUAYB 回归测试：双向关联字段导出值重复导致无法直接导入。

复现场景（与 issue 描述一致）：
- 水果表：主字段「名称」（单行文本），记录「苹果」「香蕉」
- 价格表：字段「序号」（自动编号）、「水果种类」（关联水果表，双向关联）、
  「价格」（数字）、「市场」（单行文本）
- 价格表手动录入关联后导出，「水果种类」应为「苹果」/「香蕉」，
  修复前实际为「苹果, 苹果」/「香蕉, 香蕉」，导出文件无法直接重新导入。

覆盖链路：
- LinkService.get_record_links / batch_get_record_link_ids（关联数据来源）
- records._format_record_links（前端导出所用的批量接口数据结构）
- ImportExportService._prepare_export_data / export_to_csv / export_to_excel / export_to_json
- LinkService.batch_match_link_values（导入时按值匹配关联）
"""
import csv
import io
import json

import pytest

from app.extensions import db
from app.models import Base, Record, Table
from app.models.field import Field, FieldType
from app.models.link_relation import LinkRelation, RelationshipType
from app.routes.records import _format_record_links
from app.services.import_export_service import ImportExportService
from app.services.link_service import LinkService


@pytest.fixture
def fruit_price_setup(app, db_session, test_user):
    """构造 issue 中的双向关联表格数据"""
    base = Base(
        name='IKUAYB 测试库', description='双向关联导出/导入回环',
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
    db.session.add(fruit_name)
    db.session.commit()
    fruit_table.primary_field_id = fruit_name.id
    db.session.commit()

    serial = Field(
        table_id=price_table.id, name='序号',
        type=FieldType.AUTO_NUMBER.value, order=0, is_primary=True,
        config={'prefix': '', 'digits': 1},
    )
    price = Field(
        table_id=price_table.id, name='价格',
        type=FieldType.NUMBER.value, order=2,
    )
    market = Field(
        table_id=price_table.id, name='市场',
        type=FieldType.SINGLE_LINE_TEXT.value, order=3,
    )
    # 价格表上的关联字段（双向），展示字段为水果表主字段
    fruit_kind = Field(
        table_id=price_table.id, name='水果种类',
        type=FieldType.LINK_TO_RECORD.value, order=1,
        config={
            'linkedTableId': str(fruit_table.id),
            'displayFieldId': str(fruit_name.id),
            'relationshipType': RelationshipType.ONE_TO_MANY.value,
            'bidirectional': True,
        },
    )
    # 双向关联在水果表自动生成的反向字段
    inverse = Field(
        table_id=fruit_table.id, name='价格表',
        type=FieldType.LINK_TO_RECORD.value, order=1,
        config={
            'linkedTableId': str(price_table.id),
            'displayFieldId': str(serial.id),
            'relationshipType': RelationshipType.ONE_TO_MANY.value,
            'bidirectional': True,
        },
    )
    db.session.add_all([serial, price, market, fruit_kind, inverse])
    db.session.commit()
    price_table.primary_field_id = serial.id
    db.session.commit()

    relation = LinkRelation(
        source_table_id=price_table.id,
        target_table_id=fruit_table.id,
        source_field_id=fruit_kind.id,
        target_field_id=inverse.id,
        relationship_type=RelationshipType.ONE_TO_MANY.value,
        bidirectional=True,
    )
    db.session.add(relation)
    db.session.commit()

    apple = Record(
        table_id=fruit_table.id, values={str(fruit_name.id): '苹果'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    banana = Record(
        table_id=fruit_table.id, values={str(fruit_name.id): '香蕉'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    p1 = Record(
        table_id=price_table.id,
        values={str(serial.id): '2026-1', str(price.id): 6, str(market.id): '周谷堆'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    p2 = Record(
        table_id=price_table.id,
        values={str(serial.id): '2026-2', str(price.id): 5, str(market.id): '周谷堆'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    # 用于导入回环验证的空记录
    p3 = Record(
        table_id=price_table.id,
        values={str(serial.id): '2026-3', str(price.id): 6.5, str(market.id): '三十埠'},
        created_by=test_user.id, updated_by=test_user.id,
    )
    db.session.add_all([apple, banana, p1, p2, p3])
    db.session.commit()

    # 模拟界面手动选择关联记录（会同步生成双向镜像 LinkValue）
    ok, err = LinkService.update_link_values(str(relation.id), str(p1.id), [str(apple.id)])
    assert ok, err
    ok, err = LinkService.update_link_values(str(relation.id), str(p2.id), [str(banana.id)])
    assert ok, err

    return {
        'base': base,
        'fruit_table': fruit_table,
        'price_table': price_table,
        'fruit_name': fruit_name,
        'serial': serial,
        'price': price,
        'market': market,
        'fruit_kind': fruit_kind,
        'inverse': inverse,
        'relation': relation,
        'apple': apple,
        'banana': banana,
        'p1': p1,
        'p2': p2,
        'p3': p3,
    }


def _csv_rows(csv_bytes: bytes):
    text = csv_bytes.decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text)))


# ======================================================================
# 1. 关联数据源：双向关联不能被当成两条关联返回
# ======================================================================

class TestBidirectionalLinkSource:

    def test_get_record_links_returns_each_linked_record_once(self, fruit_price_setup):
        s = fruit_price_setup
        links = LinkService.get_record_links(str(s['p1'].id), use_cache=False)
        entries = links.get(str(s['fruit_kind'].id), [])
        assert len(entries) == 1, f'双向关联被重复返回: {entries}'
        assert str(entries[0].get('target_record_id')) == str(s['apple'].id)
        assert entries[0].get('target_record') == '苹果'

    def test_batch_link_ids_are_deduplicated(self, fruit_price_setup):
        s = fruit_price_setup
        ids = LinkService.batch_get_record_link_ids([str(s['p1'].id), str(s['p2'].id)])
        assert ids[str(s['p1'].id)][str(s['fruit_kind'].id)] == [str(s['apple'].id)]
        assert ids[str(s['p2'].id)][str(s['fruit_kind'].id)] == [str(s['banana'].id)]

    def test_batch_links_api_has_no_duplicated_linked_records(self, fruit_price_setup):
        """前端导出使用 /records/links/batch 的 outbound + inbound 结构"""
        s = fruit_price_setup
        links = LinkService.get_record_links(str(s['p1'].id), use_cache=False)
        formatted = _format_record_links(links)
        all_records = [
            r
            for group in (formatted['outbound'], formatted['inbound'])
            for item in group if item['field_id'] == str(s['fruit_kind'].id)
            for r in item['linked_records']
        ]
        assert len(all_records) == 1, f'批量接口返回重复关联: {all_records}'
        assert all_records[0]['display_value'] == '苹果'

    def test_fruit_side_inverse_link_uses_primary_display_value(self, fruit_price_setup):
        """反向关联字段应显示关联记录的主字段值，而不是记录 ID / 无关字段"""
        s = fruit_price_setup
        links = LinkService.get_record_links(str(s['apple'].id), use_cache=False)
        entries = links.get(str(s['inverse'].id), [])
        assert len(entries) == 1, f'反向关联被重复返回: {entries}'
        shown = entries[0].get('target_record') or entries[0].get('source_record')
        assert shown == '2026-1', f'反向关联显示了无效的显示值: {shown}'


# ======================================================================
# 2. 导出：关联字段单元格只能是单个显示名称
# ======================================================================

class TestLinkFieldExport:

    def test_prepare_export_data_formats_link_once(self, fruit_price_setup):
        s = fruit_price_setup
        _, _, _, data = ImportExportService._prepare_export_data(str(s['price_table'].id))
        by_serial = {row['序号']: row['水果种类'] for row in data}
        assert by_serial['2026-1'] == '苹果'
        assert by_serial['2026-2'] == '香蕉'
        assert by_serial['2026-3'] == ''

    def test_csv_export_contains_single_display_name(self, fruit_price_setup):
        s = fruit_price_setup
        content, _ = ImportExportService.export_to_csv(str(s['price_table'].id))
        rows = _csv_rows(content)
        values = {row['序号']: row['水果种类'] for row in rows}
        assert values['2026-1'] == '苹果'
        assert values['2026-2'] == '香蕉'
        assert values['2026-3'] == ''

    def test_excel_export_contains_single_display_name(self, fruit_price_setup):
        pytest.importorskip('openpyxl')
        from openpyxl import load_workbook

        s = fruit_price_setup
        content, _ = ImportExportService.export_to_excel(str(s['price_table'].id))
        wb = load_workbook(io.BytesIO(content))
        ws = wb.active
        header = [c.value for c in ws[1]]
        col = header.index('水果种类') + 1
        values = {ws.cell(row=i, column=1).value: ws.cell(row=i, column=col).value
                  for i in range(2, ws.max_row + 1)}
        assert values['2026-1'] == '苹果'
        assert values['2026-2'] == '香蕉'
        assert values['2026-3'] in (None, '')

    def test_json_export_contains_single_display_name(self, fruit_price_setup):
        s = fruit_price_setup
        content, _ = ImportExportService.export_to_json(str(s['price_table'].id))
        rows = json.loads(content.decode('utf-8'))
        values = {row['序号']: row['水果种类'] for row in rows}
        assert values['2026-1'] == '苹果'
        assert values['2026-2'] == '香蕉'

    def test_export_ignores_display_text_left_by_legacy_import(self, fruit_price_setup):
        """旧版本导入把「苹果」写进 record.values 时，导出仍只输出一个显示名"""
        from sqlalchemy.orm.attributes import flag_modified

        s = fruit_price_setup
        values = dict(s['p1'].values or {})
        values[str(s['fruit_kind'].id)] = '苹果'
        s['p1'].values = values
        flag_modified(s['p1'], 'values')
        db.session.commit()

        _, _, _, data = ImportExportService._prepare_export_data(str(s['price_table'].id))
        by_serial = {row['序号']: row['水果种类'] for row in data}
        assert by_serial['2026-1'] == '苹果'


# ======================================================================
# 3. 导入回环：导出的文件（含历史坏数据）必须能直接匹配关联
# ======================================================================

class TestLinkFieldImportRoundtrip:

    def _match(self, s, value, record_key='p3'):
        return LinkService.batch_match_link_values(
            str(s['fruit_kind'].id),
            str(s['fruit_name'].id),
            [{'record_id': str(s[record_key].id), 'value': value}],
        )

    def test_exported_value_can_be_imported_back(self, fruit_price_setup):
        s = fruit_price_setup
        content, _ = ImportExportService.export_to_csv(
            str(s['price_table'].id), record_ids=[str(s['p1'].id)]
        )
        exported = _csv_rows(content)[0]['水果种类']
        result, error = self._match(s, exported)
        assert error is None
        assert result['matched_count'] == 1
        assert result['unmatched_count'] == 0

    def test_legacy_duplicated_value_can_be_imported(self, fruit_price_setup):
        """1.6.10 导出的「苹果, 苹果」应兼容，不能整串匹配失败"""
        s = fruit_price_setup
        result, error = self._match(s, '苹果, 苹果')
        assert error is None
        assert result['matched_count'] == 1
        assert result['unmatched_count'] == 0

    def test_multi_link_export_value_can_be_imported(self, fruit_price_setup):
        """一对多导出为「苹果, 香蕉」时应建立两条关联"""
        s = fruit_price_setup
        result, error = self._match(s, '苹果, 香蕉')
        assert error is None
        assert result['matched_count'] == 2
        assert result['unmatched_count'] == 0

    def test_exact_name_with_comma_still_matches(self, fruit_price_setup):
        """显示名称本身含逗号时，整串精确匹配优先，不能被拆开"""
        s = fruit_price_setup
        weird = Record(
            table_id=s['fruit_table'].id,
            values={str(s['fruit_name'].id): '苹果, 红'},
            created_by=s['p1'].created_by, updated_by=s['p1'].updated_by,
        )
        db.session.add(weird)
        db.session.commit()

        result, error = self._match(s, '苹果, 红')
        assert error is None
        assert result['matched_count'] == 1
        assert result['unmatched_count'] == 0

    def test_unmatched_value_is_still_reported(self, fruit_price_setup):
        s = fruit_price_setup
        result, error = self._match(s, '不存在的种类')
        assert error is None
        assert result['matched_count'] == 0
        assert result['unmatched_count'] == 1
        assert result['unmatched_values'][0]['value'] == '不存在的种类'

    def test_import_conversion_does_not_store_link_display_text(self, fruit_price_setup):
        """后端导入时关联字段的显示文本不能当作字段值写入"""
        s = fruit_price_setup
        assert ImportExportService._convert_value('苹果, 苹果', s['fruit_kind']) == []
        assert ImportExportService._convert_value('香蕉', s['fruit_kind']) == []
