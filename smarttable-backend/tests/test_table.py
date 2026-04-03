"""
Table（表格）模块测试
"""
import pytest


class TestTable:
    """Table功能测试类"""
    
    def test_create_table(self, client, auth_headers, test_base):
        """测试创建表格"""
        response = client.post('/api/tables',
            json={
                'base_id': str(test_base.id),
                'name': '新表格',
                'description': '这是一个新的表格'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['name'] == '新表格'
    
    def test_get_tables_list(self, client, auth_headers, test_base, test_table):
        """测试获取表格列表"""
        response = client.get(f'/api/bases/{test_base.id}/tables', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'items' in data['data']
    
    def test_get_table_detail(self, client, auth_headers, test_table):
        """测试获取表格详情"""
        response = client.get(f'/api/tables/{test_table.id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == test_table.name
    
    def test_update_table(self, client, auth_headers, test_table):
        """测试更新表格"""
        response = client.put(f'/api/tables/{test_table.id}',
            json={
                'name': '更新后的表格名称',
                'description': '更新后的描述'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '更新后的表格名称'
    
    def test_delete_table(self, client, auth_headers, test_table):
        """测试删除表格"""
        response = client.delete(f'/api/tables/{test_table.id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_reorder_tables(self, client, auth_headers, test_base, test_table):
        """测试重新排序表格"""
        response = client.put(f'/api/bases/{test_base.id}/tables/reorder',
            json={
                'table_orders': [
                    {'id': str(test_table.id), 'order': 1}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
