"""
认证模块测试
"""
import pytest
import json


class TestAuth:
    """认证功能测试类"""
    
    def test_register_success(self, client):
        """测试成功注册"""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'name': '新用户',
            'password': 'Test1234!'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert 'user' in data['data']
        assert data['data']['user']['email'] == 'newuser@example.com'
    
    def test_register_missing_fields(self, client):
        """测试注册字段缺失"""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
    
    def test_register_invalid_email(self, client):
        """测试无效邮箱格式"""
        response = client.post('/api/auth/register', json={
            'email': 'invalid-email',
            'name': 'testuser',
            'password': 'Test1234!'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
    
    def test_register_weak_password(self, client):
        """测试弱密码"""
        response = client.post('/api/auth/register', json={
            'email': 'test2@example.com',
            'name': 'testuser',
            'password': '123'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
    
    def test_login_success(self, client, test_user):
        """测试成功登录"""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'Test1234!'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        tokens = data.get('data', {}).get('tokens', data.get('data', {}))
        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
    
    def test_login_wrong_password(self, client, test_user):
        """测试密码错误"""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['code'] == 401
    
    def test_login_nonexistent_user(self, client):
        """测试不存在的用户"""
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'Test1234!'
        })
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client, test_user, auth_headers):
        """测试获取当前用户"""
        response = client.get('/api/auth/me', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['email'] == 'test@example.com'
    
    def test_get_current_user_no_token(self, client):
        """测试无Token获取用户"""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
    
    def test_refresh_token(self, client, test_user):
        """测试刷新Token"""
        login_response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'Test1234!'
        })
        login_data = login_response.get_json()['data']
        refresh_token = login_data.get('tokens', {}).get('refresh_token', login_data.get('refresh_token'))
        
        response = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        assert response.status_code == 200
        data = response.get_json()
        resp_tokens = data.get('data', {}).get('tokens', data.get('data', {}))
        assert 'access_token' in resp_tokens
    
    def test_logout(self, client, test_user, auth_headers):
        """测试登出"""
        response = client.post('/api/auth/logout', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
