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
            'username': 'newuser',
            'password': 'Password123!',
            'nickname': '新用户'
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
            'username': 'testuser',
            'password': 'Password123!'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
    
    def test_register_weak_password(self, client):
        """测试弱密码"""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'password': '123'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
    
    def test_login_success(self, client, test_user):
        """测试成功登录"""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
    
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
            'password': 'password123'
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
            'password': 'password123'
        })
        refresh_token = login_response.get_json()['data']['refresh_token']
        
        response = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data['data']
    
    def test_logout(self, client, test_user, auth_headers):
        """测试登出"""
        response = client.post('/api/auth/logout', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
