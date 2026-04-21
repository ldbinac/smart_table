"""
自动编号字段测试
"""
import pytest
from datetime import datetime
from app.models.field import Field, FieldType


class TestAutoNumberField:
    """自动编号字段测试类"""

    def test_auto_number_config_defaults(self):
        """测试自动编号配置默认值"""
        field = Field(
            name='测试编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id'
        )

        config = field.get_auto_number_config()
        assert config['prefix'] == ''
        assert config['suffix'] == ''
        assert config['digitLength'] == 0
        assert config['includeDate'] is False
        assert config['dateFormat'] == 'YYYYMMDD'
        assert config['startNumber'] == 1

    def test_auto_number_config_custom(self):
        """测试自定义自动编号配置"""
        field = Field(
            name='订单编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id',
            config={
                'prefix': 'ORD-',
                'suffix': '-X',
                'digitLength': 4,
                'includeDate': True,
                'dateFormat': 'YYYYMM',
                'startNumber': 100
            }
        )

        config = field.get_auto_number_config()
        assert config['prefix'] == 'ORD-'
        assert config['suffix'] == '-X'
        assert config['digitLength'] == 4
        assert config['includeDate'] is True
        assert config['dateFormat'] == 'YYYYMM'
        assert config['startNumber'] == 100

    def test_generate_auto_number_simple(self):
        """测试生成简单自动编号"""
        field = Field(
            name='编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id'
        )

        result = field.generate_auto_number(1)
        assert result == '1'

        result = field.generate_auto_number(100)
        assert result == '100'

    def test_generate_auto_number_with_prefix_suffix(self):
        """测试生成带前缀后缀的自动编号"""
        field = Field(
            name='编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id',
            config={
                'prefix': 'NO-',
                'suffix': '-A'
            }
        )

        result = field.generate_auto_number(1)
        assert result == 'NO-1-A'

        result = field.generate_auto_number(100)
        assert result == 'NO-100-A'

    def test_generate_auto_number_with_padding(self):
        """测试生成带前导零的自动编号"""
        field = Field(
            name='编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id',
            config={
                'digitLength': 5
            }
        )

        result = field.generate_auto_number(1)
        assert result == '00001'

        result = field.generate_auto_number(100)
        assert result == '00100'

        result = field.generate_auto_number(100000)
        assert result == '100000'

    def test_generate_auto_number_with_date(self):
        """测试生成带日期前缀的自动编号"""
        field = Field(
            name='编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id',
            config={
                'includeDate': True,
                'dateFormat': 'YYYYMMDD'
            }
        )

        result = field.generate_auto_number(1)
        # 验证格式包含当前日期
        today = datetime.now().strftime('%Y%m%d')
        assert result.startswith(f'{today}-')
        assert result.endswith('-1')

    def test_generate_auto_number_with_date_YYYYMM(self):
        """测试生成带年月前缀的自动编号"""
        field = Field(
            name='编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id',
            config={
                'includeDate': True,
                'dateFormat': 'YYYYMM'
            }
        )

        result = field.generate_auto_number(1)
        # 验证格式包含当前年月
        this_month = datetime.now().strftime('%Y%m')
        assert result.startswith(f'{this_month}-')

    def test_generate_auto_number_full_config(self):
        """测试生成完整配置的自动编号"""
        field = Field(
            name='订单编号',
            type=FieldType.AUTO_NUMBER.value,
            table_id='test-table-id',
            config={
                'prefix': 'ORD-',
                'suffix': '-X',
                'digitLength': 4,
                'includeDate': True,
                'dateFormat': 'YYMMDD'
            }
        )

        result = field.generate_auto_number(1)
        # 验证格式: ORD-YYMMDD-0001-X
        assert result.startswith('ORD-')
        assert result.endswith('-0001-X')
        assert len(result) == len('ORD-') + 6 + len('-0001-X')  # YYMMDD = 6 chars

    def test_non_auto_number_field_returns_simple_number(self):
        """测试非自动编号字段返回简单数字"""
        field = Field(
            name='普通字段',
            type=FieldType.SINGLE_LINE_TEXT.value,
            table_id='test-table-id'
        )

        result = field.generate_auto_number(100)
        assert result == '100'

        config = field.get_auto_number_config()
        assert config == {}


class TestAutoNumberInRecord:
    """记录在创建时自动编号测试类"""

    def test_create_record_with_auto_number(self, client, auth_headers, test_table):
        """测试创建记录时自动生成编号"""
        # 1. 创建自动编号字段
        response = client.post(
            f'/api/tables/{test_table.id}/fields',
            json={
                'name': '编号',
                'type': 'auto_number',
                'options': {
                    'prefix': 'NO-',
                    'digitLength': 3
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        field_data = response.get_json()['data']
        field_id = field_data['id']

        # 2. 创建记录
        response = client.post(
            f'/api/tables/{test_table.id}/records',
            json={
                'values': {}
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        record_data = response.get_json()['data']

        # 3. 验证自动编号已生成
        assert field_id in record_data['values']
        auto_number = record_data['values'][field_id]
        assert auto_number.startswith('NO-')
        assert '001' in auto_number

    def test_create_multiple_records_auto_increment(self, client, auth_headers, test_table):
        """测试创建多条记录时编号自动递增"""
        # 1. 创建自动编号字段
        response = client.post(
            f'/api/tables/{test_table.id}/fields',
            json={
                'name': '编号',
                'type': 'auto_number',
                'options': {
                    'prefix': 'ORD-',
                    'startNumber': 10
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        field_id = response.get_json()['data']['id']

        # 2. 创建多条记录
        numbers = []
        for i in range(3):
            response = client.post(
                f'/api/tables/{test_table.id}/records',
                json={'values': {}},
                headers=auth_headers
            )
            assert response.status_code == 201
            record_data = response.get_json()['data']
            auto_number = record_data['values'][field_id]
            numbers.append(auto_number)

        # 3. 验证编号递增
        assert numbers[0] == 'ORD-10'
        assert numbers[1] == 'ORD-11'
        assert numbers[2] == 'ORD-12'
