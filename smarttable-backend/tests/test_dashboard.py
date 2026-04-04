"""
Dashboard 模块 API 测试
"""
import pytest
import json


class TestDashboard:
    """Dashboard 功能测试类"""
    
    def test_create_dashboard(self, client, auth_headers, test_base):
        """测试创建 Dashboard"""
        response = client.post('/api/dashboards',
            json={
                'base_id': str(test_base.id),
                'name': '数据概览',
                'description': '项目数据总览面板',
                'layout': {
                    'columns': 4,
                    'gap': 16
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['name'] == '数据概览'
    
    def test_create_dashboard_without_auth(self, client, test_base):
        """测试无认证创建 Dashboard"""
        response = client.post('/api/dashboards',
            json={
                'base_id': str(test_base.id),
                'name': '未授权仪表盘'
            }
        )
        
        assert response.status_code == 401
    
    def test_get_dashboards_list(self, client, auth_headers, test_base):
        """测试获取 Dashboard 列表"""
        response = client.get(f'/api/bases/{test_base.id}/dashboards',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'items' in data['data']
    
    def test_get_dashboard_detail(self, client, auth_headers, test_base):
        """测试获取 Dashboard 详情"""
        create_resp = client.post('/api/dashboards',
            json={
                'base_id': str(test_base.id),
                'name': '详情测试仪表盘'
            },
            headers=auth_headers
        )
        dashboard_id = create_resp.get_json()['data']['id']
        
        response = client.get(f'/api/dashboards/{dashboard_id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '详情测试仪表盘'
    
    def test_update_dashboard(self, client, auth_headers, test_base):
        """测试更新 Dashboard"""
        create_resp = client.post('/api/dashboards',
            json={
                'base_id': str(test_base.id),
                'name': '待更新仪表盘'
            },
            headers=auth_headers
        )
        dashboard_id = create_resp.get_json()['data']['id']
        
        response = client.put(f'/api/dashboards/{dashboard_id}',
            json={
                'name': '更新后的仪表盘名',
                'description': '更新后的描述信息'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '更新后的仪表盘名'
    
    def test_delete_dashboard(self, client, auth_headers, test_base):
        """测试删除 Dashboard"""
        create_resp = client.post('/api/dashboards',
            json={
                'base_id': str(test_base.id),
                'name': '可删除的仪表盘'
            },
            headers=auth_headers
        )
        dashboard_id = create_resp.get_json()['data']['id']
        
        response = client.delete(f'/api/dashboards/{dashboard_id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
    
    def test_delete_nonexistent_dashboard(self, client, auth_headers):
        """测试删除不存在的 Dashboard"""
        response = client.delete('/api/dashboards/nonexistent-id',
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_create_dashboard_with_widgets(self, client, auth_headers, test_base):
        """测试带 Widget 的 Dashboard 创建"""
        response = client.post('/api/dashboards',
            json={
                'base_id': str(test_base.id),
                'name': '组件仪表盘',
                'widgets': [
                    {
                        'type': 'stat',
                        'title': '总记录数',
                        'config': {'source_table': 'table-1'}
                    },
                    {
                        'type': 'chart',
                        'title': '趋势图',
                        'config': {'chart_type': 'line'}
                    }
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code in [201, 200]
