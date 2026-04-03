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
                'type': 'text',
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
        assert 'items' in data['data']
    
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
        response = client.put(f'/api/tables/{test_table.id}/fields/reorder',
            json={
                'field_orders': [
                    {'id': str(test_field.id), 'order': 1}
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
