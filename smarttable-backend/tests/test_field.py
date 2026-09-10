"""
Field（字段）模块测试
"""
import pytest


class TestField:
    """Field功能测试类"""
    
    def test_create_field(self, client, auth_headers, test_table):
        """测试创建字段"""
        response = client.post(f'/api/tables/{test_table.id}/fields',
            json={
                'name': '新字段',
                'type': 'single_line_text',
                'is_required': False
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['name'] == '新字段'
    
    def test_create_number_field(self, client, auth_headers, test_table):
        """测试创建数字字段"""
        response = client.post(f'/api/tables/{test_table.id}/fields',
            json={
                'name': '数量',
                'type': 'number',
                'options': {
                    'precision': 2,
                    'default_value': 0
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['type'] == 'number'
    
    def test_create_select_field(self, client, auth_headers, test_table):
        """测试创建选择字段"""
        response = client.post(f'/api/tables/{test_table.id}/fields',
            json={
                'name': '状态',
                'type': 'single_select',
                'options': {
                    'choices': [
                        {'value': 'todo', 'color': 'blue'},
                        {'value': 'done', 'color': 'green'}
                    ]
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['type'] == 'single_select'
    
    def test_get_fields_list(self, client, auth_headers, test_table, test_field):
        """测试获取字段列表"""
        response = client.get(f'/api/tables/{test_table.id}/fields', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert isinstance(data['data'], list)
        assert len(data['data']) > 0
    
    def test_update_field(self, client, auth_headers, test_field):
        """测试更新字段"""
        response = client.put(f'/api/fields/{test_field.id}',
            json={
                'name': '更新后的字段名',
                'is_required': True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '更新后的字段名'
    
    def test_delete_field(self, client, auth_headers, test_field):
        """测试删除字段"""
        response = client.delete(f'/api/fields/{test_field.id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_reorder_fields(self, client, auth_headers, test_table, test_field):
        """测试重新排序字段"""
        response = client.post('/api/fields/reorder',
            json={
                'table_id': str(test_table.id),
                'orders': [
                    {'field_id': str(test_field.id), 'order': 1}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
    
    def test_get_field_types(self, client, auth_headers):
        """测试获取字段类型列表"""
        response = client.get('/api/fields/types', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert len(data['data']) > 0

    def test_update_field_type_converts_values(self, client, auth_headers, test_table, test_record):
        """测试修改字段类型时自动转换已有记录值"""
        # 创建数字字段并写入记录值
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
            json={'name': '数量', 'type': 'number'},
            headers=auth_headers
        )
        assert field_resp.status_code == 201
        field_data = field_resp.get_json()['data']
        field_id = field_data['id']

        record_resp = client.put(f'/api/records/{test_record.id}',
            json={'values': {field_id: 42}},
            headers=auth_headers
        )
        assert record_resp.status_code == 200

        # 将字段类型从 number 改为 single_line_text
        update_resp = client.put(f'/api/fields/{field_id}',
            json={'type': 'single_line_text'},
            headers=auth_headers
        )
        assert update_resp.status_code == 200
        update_data = update_resp.get_json()
        assert update_data['data']['type'] == 'single_line_text'

        # 验证记录值已转换为字符串
        get_resp = client.get(f'/api/records/{test_record.id}', headers=auth_headers)
        assert get_resp.status_code == 200
        values = get_resp.get_json()['data']['values']
        assert values[field_id] == '42'

    def test_update_field_single_to_multi_select(self, client, auth_headers, test_table, test_record):
        """测试单选字段改为多选字段时值转换为数组"""
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
            json={
                'name': '状态',
                'type': 'single_select',
                'options': {'choices': [{'value': 'done', 'color': 'green'}]}
            },
            headers=auth_headers
        )
        assert field_resp.status_code == 201
        field_id = field_resp.get_json()['data']['id']

        client.put(f'/api/records/{test_record.id}',
            json={'values': {field_id: 'done'}},
            headers=auth_headers
        )

        update_resp = client.put(f'/api/fields/{field_id}',
            json={'type': 'multi_select'},
            headers=auth_headers
        )
        assert update_resp.status_code == 200

        get_resp = client.get(f'/api/records/{test_record.id}', headers=auth_headers)
        assert get_resp.status_code == 200
        values = get_resp.get_json()['data']['values']
        assert values[field_id] == ['done']

    def test_create_auto_number_field(self, client, auth_headers, test_table):
        """测试创建自动编号字段"""
        response = client.post(f'/api/tables/{test_table.id}/fields',
            json={
                'name': '编号',
                'type': 'auto_number',
                'options': {
                    'prefix': 'NO-',
                    'suffix': '-A',
                    'digitLength': 4,
                    'startNumber': 1,
                    'includeDate': False
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['type'] == 'auto_number'
        assert data['data']['options']['prefix'] == 'NO-'
        assert data['data']['options']['digitLength'] == 4

    def test_create_auto_number_field_with_date(self, client, auth_headers, test_table):
        """测试创建带日期前缀的自动编号字段"""
        response = client.post(f'/api/tables/{test_table.id}/fields',
            json={
                'name': '订单编号',
                'type': 'auto_number',
                'options': {
                    'prefix': 'ORD-',
                    'digitLength': 3,
                    'includeDate': True,
                    'dateFormat': 'YYYYMM'
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['options']['includeDate'] is True
        assert data['data']['options']['dateFormat'] == 'YYYYMM'


from types import SimpleNamespace
from app.models.field import FieldType
from app.services.field_service import FieldService


class TestFieldTypeConversion:
    """字段类型转换规则引擎测试（无损优先 + 唯一有损例外 date_time→date）"""

    # ---------------- 纯函数：_convert_value_for_type ----------------
    def test_convert_value_text_upgrades(self):
        assert FieldService._convert_value_for_type('hello', 'single_line_text', 'email') == 'hello'
        assert FieldService._convert_value_for_type('hello', 'single_line_text', 'long_text') == 'hello'

    def test_convert_value_number_to_text(self):
        assert FieldService._convert_value_for_type(3, 'number', 'single_line_text') == '3'
        assert FieldService._convert_value_for_type(3.5, 'number', 'single_line_text') == '3.5'

    def test_convert_value_single_to_multi_select(self):
        assert FieldService._convert_value_for_type('a', 'single_select', 'multi_select') == ['a']
        assert FieldService._convert_value_for_type(None, 'single_select', 'multi_select') is None

    def test_convert_value_date_to_datetime(self):
        assert FieldService._convert_value_for_type('2023-05-01', 'date', 'date_time') == '2023-05-01T00:00:00Z'

    def test_convert_value_datetime_to_date_truncates(self):
        assert FieldService._convert_value_for_type('2023-05-01T12:34:56Z', 'date_time', 'date') == '2023-05-01'

    def test_convert_value_multi_select_to_text_keeps_ids(self):
        assert FieldService._convert_value_for_type(['a', 'b'], 'multi_select', 'single_line_text') == 'a, b'

    def test_convert_value_numeric_family_keeps_number(self):
        assert FieldService._convert_value_for_type(5, 'number', 'currency') == 5
        assert FieldService._convert_value_for_type(5, 'number', 'percent') == 5

    def test_convert_value_formula_to_text(self):
        # 公式结果按目标类型承载：数值结果转文本
        assert FieldService._convert_value_for_type(12.5, 'formula', 'single_line_text') == '12.5'

    # ---------------- 纯函数：_is_valid_type_conversion ----------------
    def test_is_valid_type_conversion_lossless_allowed(self):
        assert FieldService._is_valid_type_conversion('number', 'currency', True) == 'allowed'
        assert FieldService._is_valid_type_conversion('date', 'date_time', True) == 'allowed'

    def test_is_valid_type_conversion_forbidden(self):
        assert FieldService._is_valid_type_conversion('number', 'single_select', True) == 'forbidden'
        assert FieldService._is_valid_type_conversion('link_to_record', 'single_line_text', True) == 'forbidden'
        assert FieldService._is_valid_type_conversion('single_line_text', 'formula', True) == 'forbidden'
        assert FieldService._is_valid_type_conversion('created_by', 'single_line_text', True) == 'forbidden'

    def test_is_valid_type_conversion_primary_auto_number_to_text(self):
        # 主字段为自动编号且有数据时，允许转为文本类（单行/多行/富文本）
        assert FieldService._is_valid_type_conversion('auto_number', 'single_line_text', True, is_primary=True) == 'allowed'
        assert FieldService._is_valid_type_conversion('auto_number', 'long_text', True, is_primary=True) == 'allowed'
        assert FieldService._is_valid_type_conversion('auto_number', 'rich_text', True, is_primary=True) == 'allowed'
        # 非主字段自动编号有数据时仍禁止转文本（保持原规则）
        assert FieldService._is_valid_type_conversion('auto_number', 'single_line_text', True, is_primary=False) == 'forbidden'
        # 主字段自动编号有数据转非文本类仍禁止
        assert FieldService._is_valid_type_conversion('auto_number', 'number', True, is_primary=True) == 'forbidden'

    def test_is_valid_type_conversion_text_to_contact_forbidden(self):
        # 文本类字段（单行/多行/富文本）已有数据时，不得转为电话/邮箱/链接，
        # 否则既有文本可能不符合目标类型的格式校验，转换后产生非法数据
        for from_type in FieldService.TEXT_TYPES:
            for to_type in (FieldType.PHONE.value, FieldType.EMAIL.value, FieldType.URL.value):
                assert FieldService._is_valid_type_conversion(from_type, to_type, True) == 'forbidden'
        # 无数据时仍可自由转换（无既有文本需要校验）
        assert FieldService._is_valid_type_conversion('single_line_text', 'email', False) == 'allowed'
        assert FieldService._is_valid_type_conversion('long_text', 'phone', False) == 'allowed'

    def test_is_valid_type_conversion_lossy_only_datetime_to_date(self):
        assert FieldService._is_valid_type_conversion('date_time', 'date', True) == 'lossy'
        # 反向 date -> date_time 无损
        assert FieldService._is_valid_type_conversion('date', 'date_time', True) == 'allowed'
        # 其它有损一律 forbidden（多选转单选会丢数据）
        assert FieldService._is_valid_type_conversion('multi_select', 'single_select', True) == 'forbidden'

    def test_is_valid_type_conversion_no_data_free(self):
        # 无数据时，在任意类型之间自由转换（含系统/引用/公式类型）
        assert FieldService._is_valid_type_conversion('date_time', 'date', False) == 'allowed'
        assert FieldService._is_valid_type_conversion('number', 'single_select', False) == 'allowed'
        assert FieldService._is_valid_type_conversion('link_to_record', 'single_line_text', False) == 'allowed'
        assert FieldService._is_valid_type_conversion('created_by', 'single_line_text', False) == 'allowed'
        assert FieldService._is_valid_type_conversion('single_line_text', 'formula', False) == 'allowed'
        assert FieldService._is_valid_type_conversion('single_line_text', 'auto_number', False) == 'allowed'

    # ---------------- 纯函数：_value_fits_type ----------------
    def test_value_fits_type(self):
        assert FieldService._value_fits_type('123', 'number') is True
        assert FieldService._value_fits_type('abc', 'number') is False
        assert FieldService._value_fits_type('2023-05-01', 'date') is True
        assert FieldService._value_fits_type('2023/05/01', 'date') is False
        assert FieldService._value_fits_type('a@b.com', 'email') is True
        assert FieldService._value_fits_type('not-an-email', 'email') is False

    # ---------------- _evaluate_conversion ----------------
    def test_evaluate_conversion_primary_text_only(self):
        f = SimpleNamespace(type='number', is_primary=True)
        # 主字段（已有数据）转非文本类型 -> 禁止（值用作记录标题）
        verdict, reason, _ = FieldService._evaluate_conversion(f, 'currency', True)
        assert verdict == 'forbidden'
        assert reason == 'field_type_conversion_primary_text_only'
        # 主字段（已有数据）转文本类 -> 允许
        verdict2, _, _ = FieldService._evaluate_conversion(f, 'long_text', True)
        assert verdict2 == 'allowed'

    def test_evaluate_conversion_primary_empty_allows_any_type(self):
        f = SimpleNamespace(type='number', is_primary=True)
        # 主字段尚未产生数据：允许转换为任意类型（含自动编号/引用/公式等）
        assert FieldService._evaluate_conversion(f, 'auto_number', False)[0] == 'allowed'
        assert FieldService._evaluate_conversion(f, 'link_to_record', False)[0] == 'allowed'
        assert FieldService._evaluate_conversion(f, 'formula', False)[0] == 'allowed'
        assert FieldService._evaluate_conversion(f, 'currency', False)[0] == 'allowed'

    def test_evaluate_conversion_primary_auto_number_to_text(self):
        f = SimpleNamespace(type='auto_number', is_primary=True)
        # 主字段为自动编号且有数据 -> 可转为文本类（单行/多行/富文本）
        assert FieldService._evaluate_conversion(f, 'single_line_text', True)[0] == 'allowed'
        assert FieldService._evaluate_conversion(f, 'long_text', True)[0] == 'allowed'
        assert FieldService._evaluate_conversion(f, 'rich_text', True)[0] == 'allowed'
        # 主字段为自动编号且有数据 -> 转非文本类仍禁止
        assert FieldService._evaluate_conversion(f, 'number', True)[0] == 'forbidden'

    def test_evaluate_conversion_primary_text_to_auto_number_forbidden(self):
        # 反之：主字段为文本且有数据时，无法再转为自动编号
        f = SimpleNamespace(type='single_line_text', is_primary=True)
        verdict, reason, _ = FieldService._evaluate_conversion(f, 'auto_number', True)
        assert verdict == 'forbidden'
        assert reason == 'field_type_conversion_primary_text_only'

    def test_evaluate_conversion_text_to_contact_blocked_reason(self):
        # 文本类字段已有数据转电话/邮箱/链接：禁止并给出专用原因
        for from_type in FieldService.TEXT_TYPES:
            f = SimpleNamespace(type=from_type, is_primary=False)
            verdict, reason, _ = FieldService._evaluate_conversion(f, FieldType.EMAIL.value, True)
            assert verdict == 'forbidden'
            assert reason == 'field_type_conversion_text_to_contact_blocked'

    def test_e2e_primary_auto_number_to_text_allowed(self, db_session, test_table, test_user):
        # 端到端：主字段为自动编号且已有数据时，可转为文本类；非文本类仍禁止
        from app.models.field import Field, FieldType
        from app.models.record import Record

        field = Field(table_id=test_table.id, name='编号', type=FieldType.AUTO_NUMBER.value,
                      is_primary=True, is_required=False, order=0, options={'prefix': 'NO-'})
        db_session.add(field)
        db_session.flush()
        record = Record(table_id=test_table.id, values={str(field.id): 1},
                        created_by=test_user.id, updated_by=test_user.id)
        db_session.add(record)
        db_session.flush()

        conv = FieldService.get_convertible_types(field)
        allowed_types = {item['type'] for item in conv['allowed']}
        blocked_types = {item['type'] for item in conv['blocked']}
        assert conv['hasData'] is True
        # 单行 / 多行 / 富文本放行
        assert FieldType.SINGLE_LINE_TEXT.value in allowed_types
        assert FieldType.LONG_TEXT.value in allowed_types
        assert FieldType.RICH_TEXT.value in allowed_types
        # 非文本类型（如数值）仍被禁止
        assert FieldType.NUMBER.value in blocked_types

    def test_evaluate_conversion_lossy_notice(self):
        f = SimpleNamespace(type='date_time', is_primary=False)
        verdict, _, notice = FieldService._evaluate_conversion(f, 'date', True)
        assert verdict == 'lossy'
        assert notice == 'field_type_conversion_lossy_datetime_to_date'

    def test_evaluate_conversion_formula_freeze_notice(self):
        f = SimpleNamespace(type='formula', is_primary=False)
        verdict, _, notice = FieldService._evaluate_conversion(f, 'single_line_text', True)
        assert verdict == 'allowed'
        assert notice == 'field_type_conversion_notice_formula_freeze'

    def test_evaluate_conversion_member_to_text_notice(self):
        f = SimpleNamespace(type='collaborator', is_primary=False)
        verdict, _, notice = FieldService._evaluate_conversion(f, 'single_line_text', True)
        assert verdict == 'allowed'
        assert notice == 'field_type_conversion_notice_keep_member_id'

    # ---------------- 端到端：无数据自由转换 ----------------
    def test_e2e_no_data_free_conversion(self, client, auth_headers, test_table):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '文本', 'type': 'single_line_text'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']
        resp = client.put(f'/api/fields/{field_id}', json={'type': 'email'}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['data']['type'] == 'email'

    # ---------------- 端到端：有损转换需确认 ----------------
    def test_e2e_lossy_requires_confirm(self, client, auth_headers, test_table, test_record):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '时间', 'type': 'date_time'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']
        client.put(f'/api/records/{test_record.id}',
                   json={'values': {field_id: '2023-05-01T12:34:56Z'}}, headers=auth_headers)
        # 未确认 -> 需要二次确认
        resp = client.put(f'/api/fields/{field_id}', json={'type': 'date'}, headers=auth_headers)
        assert resp.status_code == 409
        assert resp.get_json().get('error') == 'lossy_conversion_requires_confirmation'
        # 携带确认标记 -> 成功且值被截断为日期
        resp2 = client.put(f'/api/fields/{field_id}', json={'type': 'date', 'confirmLossy': True}, headers=auth_headers)
        assert resp2.status_code == 200
        get_resp = client.get(f'/api/records/{test_record.id}', headers=auth_headers)
        values = get_resp.get_json()['data']['values']
        assert values[field_id] == '2023-05-01'

    # ---------------- 端到端：禁止转换被拒且类型不变 ----------------
    def test_e2e_forbidden_conversion_rejected(self, client, auth_headers, test_table, test_record):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '文本', 'type': 'single_line_text'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']
        client.put(f'/api/records/{test_record.id}',
                   json={'values': {field_id: 'hello'}}, headers=auth_headers)
        resp = client.put(f'/api/fields/{field_id}', json={'type': 'link'}, headers=auth_headers)
        assert resp.status_code == 400
        get_resp = client.get(f'/api/fields/{field_id}', headers=auth_headers)
        assert get_resp.get_json()['data']['type'] == 'single_line_text'

    # ---------------- 端到端：文本字段有数据后禁止转电话/邮箱/链接 ----------------
    def test_e2e_text_to_contact_blocked(self, client, auth_headers, test_table, test_record):
        # 文本字段已有数据后，不得转换为电话/邮箱/链接（避免原有文本不符合目标格式校验）
        for target in ('email', 'phone', 'url'):
            field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                     json={'name': '文本', 'type': 'single_line_text'}, headers=auth_headers)
            field_id = field_resp.get_json()['data']['id']
            client.put(f'/api/records/{test_record.id}',
                       json={'values': {field_id: 'hello'}}, headers=auth_headers)
            resp = client.put(f'/api/fields/{field_id}', json={'type': target}, headers=auth_headers)
            assert resp.status_code == 400
            assert resp.get_json().get('error') == 'field_type_conversion_text_to_contact_blocked'
            get_resp = client.get(f'/api/fields/{field_id}', headers=auth_headers)
            assert get_resp.get_json()['data']['type'] == 'single_line_text'

    # ---------------- 端到端：可转换类型接口 ----------------
    def test_convertible_types_interface(self, client, auth_headers, test_table):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '数字', 'type': 'number'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']
        resp = client.get(f'/api/fields/{field_id}/convertible-types', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['hasData'] is False
        allowed_types = {item['type'] for item in data['allowed']}
        assert 'currency' in allowed_types
        # 空字段（无数据）可转换为任意类型，引用/公式类型不再被禁止
        assert 'link_to_record' in allowed_types
        blocked_types = {item['type'] for item in data['blocked']}
        assert 'link_to_record' not in blocked_types

    # ---------------- 端到端：空字段转引用/计算类型需配置（关联关系一致） ----------------
    def test_e2e_empty_field_to_link_requires_config(self, client, auth_headers, test_table):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '空字段', 'type': 'single_line_text'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']

        # 缺少关联表配置 -> 拒绝
        missing = client.put(f'/api/fields/{field_id}', json={'type': 'link_to_record'}, headers=auth_headers)
        assert missing.status_code == 400
        assert missing.get_json().get('error') == 'field_configuration_missing_linked_table_id'

        # 提供关联表配置 -> 成功，类型与配置保持一致
        ok = client.put(f'/api/fields/{field_id}',
                        json={'type': 'link_to_record', 'config': {'linkedTableId': str(test_table.id)}},
                        headers=auth_headers)
        assert ok.status_code == 200
        assert ok.get_json()['data']['type'] == 'link_to_record'

    def test_e2e_empty_field_to_formula_requires_config(self, client, auth_headers, test_table):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '空字段2', 'type': 'single_line_text'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']

        # 缺少公式表达式 -> 拒绝
        missing = client.put(f'/api/fields/{field_id}', json={'type': 'formula'}, headers=auth_headers)
        assert missing.status_code == 400
        assert missing.get_json().get('error') == 'field_configuration_missing_formula'

        # 提供公式 -> 成功
        ok = client.put(f'/api/fields/{field_id}',
                        json={'type': 'formula', 'config': {'formula': '1 + 1'}},
                        headers=auth_headers)
        assert ok.status_code == 200
        assert ok.get_json()['data']['type'] == 'formula'

    # ---------------- 端到端：空字段允许转换为原本禁止的系统/引用类型 ----------------
    def test_e2e_empty_field_to_auto_number_allowed(self, client, auth_headers, test_table):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '空字段3', 'type': 'single_line_text'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']
        resp = client.put(f'/api/fields/{field_id}',
                          json={'type': 'auto_number', 'options': {'prefix': 'NO-'}}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['data']['type'] == 'auto_number'

    def test_e2e_empty_field_convertible_types_now_allow_reference(self, client, auth_headers, test_table):
        field_resp = client.post(f'/api/tables/{test_table.id}/fields',
                                 json={'name': '空字段4', 'type': 'single_line_text'}, headers=auth_headers)
        field_id = field_resp.get_json()['data']['id']
        resp = client.get(f'/api/fields/{field_id}/convertible-types', headers=auth_headers)
        data = resp.get_json()['data']
        assert data['hasData'] is False
        allowed_types = {item['type'] for item in data['allowed']}
        # 无数据时空字段可转任意类型（含引用/公式/自动编号）
        assert 'link_to_record' in allowed_types
        assert 'formula' in allowed_types
        assert 'auto_number' in allowed_types
        assert 'created_by' in allowed_types
        assert data['blocked'] == []
