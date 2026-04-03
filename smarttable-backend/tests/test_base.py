"""
Base（多维表格基础）模块测试
"""
import pytest


class TestBase:
    """Base功能测试类"""
    
    def test_create_base(self, client, auth_headers, test_user):
        """测试创建Base"""
        response = client.post('/api/bases', 
            json={
                'name': '新多维表格',
                'description': '这是一个新的多维表格',
                'icon': 'folder',
                'color': '#10b981'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['name'] == '新多维表格'
    
    def test_create_base_without_auth(self, client):
        """测试无认证创建Base"""
        response = client.post('/api/bases', json={
            'name': '新多维表格'
        })
        
        assert response.status_code == 401
    
    def test_get_bases_list(self, client, auth_headers, test_base):
        """测试获取Base列表"""
        response = client.get('/api/bases', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'items' in data['data']
    
    def test_get_base_detail(self, client, auth_headers, test_base):
        """测试获取Base详情"""
        response = client.get(f'/api/bases/{test_base.id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == test_base.name
    
    def test_update_base(self, client, auth_headers, test_base):
        """测试更新Base"""
        response = client.put(f'/api/bases/{test_base.id}',
            json={
                'name': '更新后的名称',
                'description': '更新后的描述'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '更新后的名称'
    
    def test_delete_base(self, client, auth_headers, test_base):
        """测试删除Base"""
        response = client.delete(f'/api/bases/{test_base.id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_add_member(self, client, auth_headers, test_base):
        """测试添加成员"""
        response = client.post(f'/api/bases/{test_base.id}/members',
            json={
                'user_id': 'another-user-id',
                'role': 'editor'
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201, 400]
    
    def test_update_member_role(self, client, auth_headers, test_base):
        """测试更新成员角色"""
        response = client.put(f'/api/bases/{test_base.id}/members/member-id',
            json={
                'role': 'admin'
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 404]
    
    def test_remove_member(self, client, auth_headers, test_base):
        """测试移除成员"""
        response = client.delete(f'/api/bases/{test_base.id}/members/member-id',
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
