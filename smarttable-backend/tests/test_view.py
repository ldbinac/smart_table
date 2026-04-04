"""
View（视图）模块测试
"""
import pytest


class TestView:
    """View功能测试类"""
    
    def test_create_view(self, client, auth_headers, test_table):
        """测试创建视图"""
        response = client.post(f'/api/views/tables/{test_table.id}/views',
            json={
                'name': '新视图',
                'type': 'grid'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['name'] == '新视图'
    
    def test_create_gallery_view(self, client, auth_headers, test_table):
        """测试创建画廊视图"""
        response = client.post(f'/api/views/tables/{test_table.id}/views',
            json={
                'name': '画廊视图',
                'type': 'gallery',
                'config': {
                    'card_size': 'medium'
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['type'] == 'gallery'
    
    def test_create_kanban_view(self, client, auth_headers, test_table):
        """测试创建看板视图"""
        response = client.post(f'/api/views/tables/{test_table.id}/views',
            json={
                'name': '看板视图',
                'type': 'kanban',
                'config': {
                    'group_by_field': 'status-field-id'
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['type'] == 'kanban'
    
    def test_get_views_list(self, client, auth_headers, test_table, test_view):
        """测试获取视图列表"""
        response = client.get(f'/api/views/tables/{test_table.id}/views',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'items' in data['data']
    
    def test_get_view_detail(self, client, auth_headers, test_view):
        """测试获取视图详情"""
        response = client.get(f'/api/views/views/{test_view.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['id'] == str(test_view.id)
    
    def test_update_view(self, client, auth_headers, test_view):
        """测试更新视图"""
        response = client.put(f'/api/views/views/{test_view.id}',
            json={
                'name': '更新后的视图名',
                'filters': [
                    {'field_id': 'field-1', 'operator': 'equals', 'value': 'test'}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_duplicate_view(self, client, auth_headers, test_view):
        """测试复制视图"""
        response = client.post(f'/api/views/views/{test_view.id}/duplicate',
            json={
                'name': '复制的视图'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['name'] == '复制的视图'
    
    def test_delete_view(self, client, auth_headers, test_table):
        """测试删除视图"""
        create_response = client.post(f'/api/views/tables/{test_table.id}/views',
            json={
                'name': '可删除的视图',
                'type': 'grid'
            },
            headers=auth_headers
        )
        view_id = create_response.get_json()['data']['id']
        
        response = client.delete(f'/api/views/views/{view_id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_reorder_views(self, client, auth_headers, test_table, test_view):
        """测试重新排序视图"""
        response = client.put(f'/api/views/tables/{test_table.id}/views/reorder',
            json={
                'view_orders': [
                    {'id': str(test_view.id), 'order': 2}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_get_view_types(self, client, auth_headers):
        """测试获取视图类型列表"""
        response = client.get('/api/views/views/types', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert len(data['data']) > 0
    
    def test_set_default_view(self, client, auth_headers, test_table, test_view):
        """测试设置默认视图（任务 19.6）"""
        response = client.put(
            f'/api/tables/{test_table.id}/views/{test_view.id}/set-default',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_set_default_nonexistent_view(self, client, auth_headers, test_table):
        """测试设置不存在的视图为默认"""
        response = client.put(
            f'/api/tables/{test_table.id}/views/nonexistent-id/set-default',
            headers=auth_headers
        )
        
        assert response.status_code == 404
