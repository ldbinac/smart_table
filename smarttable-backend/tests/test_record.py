"""
Record（记录）模块测试
"""
import pytest


class TestRecord:
    """Record功能测试类"""
    
    def test_create_record(self, client, auth_headers, test_table, test_field):
        """测试创建记录"""
        response = client.post(f'/api/records/tables/{test_table.id}/records',
            json={
                'values': {
                    str(test_field.id): '测试数据'
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert str(test_field.id) in data['data']['values']
    
    def test_get_records_list(self, client, auth_headers, test_table, test_record):
        """测试获取记录列表"""
        response = client.get(f'/api/records/tables/{test_table.id}/records',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'items' in data['data']
    
    def test_get_records_pagination(self, client, auth_headers, test_table, test_record):
        """测试记录分页"""
        response = client.get(f'/api/records/tables/{test_table.id}/records?page=1&per_page=10',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'total' in data['data']
        assert 'page' in data['data']
    
    def test_get_record_detail(self, client, auth_headers, test_record):
        """测试获取记录详情"""
        response = client.get(f'/api/records/records/{test_record.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['id'] == str(test_record.id)
    
    def test_update_record(self, client, auth_headers, test_record, test_field):
        """测试更新记录"""
        response = client.put(f'/api/records/records/{test_record.id}',
            json={
                'values': {
                    str(test_field.id): '更新后的数据'
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_delete_record(self, client, auth_headers, test_record):
        """测试删除记录"""
        response = client.delete(f'/api/records/records/{test_record.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_batch_create_records(self, client, auth_headers, test_table, test_field):
        """测试批量创建记录"""
        response = client.post(f'/api/records/tables/{test_table.id}/records/batch',
            json={
                'records': [
                    {'values': {str(test_field.id): '数据1'}},
                    {'values': {str(test_field.id): '数据2'}}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
        data = response.get_json()
        assert 'created_count' in data['data']
    
    def test_batch_update_records(self, client, auth_headers, test_table, test_record, test_field):
        """测试批量更新记录"""
        response = client.put('/api/records/records/batch',
            json={
                'record_ids': [str(test_record.id)],
                'values': {
                    str(test_field.id): '批量更新数据'
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'updated_count' in data['data']
    
    def test_batch_delete_records(self, client, auth_headers, test_record):
        """测试批量删除记录"""
        response = client.delete('/api/records/records/batch',
            json={
                'record_ids': [str(test_record.id)]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'deleted_count' in data['data']
    
    def test_search_records(self, client, auth_headers, test_table, test_record):
        """测试搜索记录"""
        response = client.get(f'/api/records/tables/{test_table.id}/records?search=测试',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
