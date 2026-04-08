"""
成员管理和分享链接功能测试脚本
测试所有新增的 API 接口
"""
import requests
import json
from datetime import datetime, timedelta

# API 基础 URL
BASE_URL = 'http://localhost:5000/api'

# 测试用户凭证
TEST_USER = {
    'email': 'test@example.com',
    'password': 'Test123!'
}

# 存储访问令牌
access_token = None

def login():
    """登录获取访问令牌"""
    print('\n=== 测试登录 ===')
    try:
        response = requests.post(f'{BASE_URL}/auth/login', json=TEST_USER)
        if response.status_code == 200:
            data = response.json()
            global access_token
            access_token = data['data']['access_token']
            print('✓ 登录成功')
            return True
        else:
            print(f'✗ 登录失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 登录异常：{e}')
        return False

def get_headers():
    """获取请求头"""
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

def test_create_base():
    """测试创建 Base"""
    print('\n=== 测试创建 Base ===')
    try:
        data = {
            'name': f'测试 Base {datetime.now().strftime("%Y%m%d%H%M%S")}',
            'description': '用于测试成员管理和分享功能',
            'icon': 'folder',
            'color': '#6366f1'
        }
        response = requests.post(f'{BASE_URL}/bases', json=data, headers=get_headers())
        if response.status_code == 201:
            result = response.json()
            base_id = result['data']['id']
            print(f'✓ Base 创建成功，ID: {base_id}')
            return base_id
        else:
            print(f'✗ Base 创建失败：{response.text}')
            return None
    except Exception as e:
        print(f'✗ 创建 Base 异常：{e}')
        return None

def test_get_members(base_id):
    """测试获取成员列表"""
    print(f'\n=== 测试获取成员列表 (Base ID: {base_id}) ===')
    try:
        response = requests.get(f'{BASE_URL}/bases/{base_id}/members', headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            members = result['data']
            print(f'✓ 获取成员列表成功，共 {len(members)} 个成员')
            for member in members:
                print(f'  - {member["user"]["name"]} ({member["role"]})')
            return True
        else:
            print(f'✗ 获取成员列表失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 获取成员列表异常：{e}')
        return False

def test_add_member(base_id):
    """测试添加成员"""
    print(f'\n=== 测试添加成员 (Base ID: {base_id}) ===')
    try:
        data = {
            'email': 'member@example.com',
            'role': 'editor'
        }
        response = requests.post(f'{BASE_URL}/bases/{base_id}/members', json=data, headers=get_headers())
        if response.status_code == 201:
            result = response.json()
            print(f'✓ 添加成员成功：{result["data"]["user"]["name"]}')
            return True
        elif response.status_code == 400:
            print(f'⚠ 添加成员失败（可能是用户不存在）：{response.text}')
            return False
        else:
            print(f'✗ 添加成员失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 添加成员异常：{e}')
        return False

def test_update_member_role(base_id, user_id):
    """测试更新成员角色"""
    print(f'\n=== 测试更新成员角色 (Base ID: {base_id}, User ID: {user_id}) ===')
    try:
        data = {
            'role': 'admin'
        }
        response = requests.put(f'{BASE_URL}/bases/{base_id}/members/{user_id}', json=data, headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            print(f'✓ 更新成员角色成功：{result["data"]["user"]["name"]} -> {result["data"]["role"]}')
            return True
        else:
            print(f'✗ 更新成员角色失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 更新成员角色异常：{e}')
        return False

def test_create_share(base_id):
    """测试创建分享链接"""
    print(f'\n=== 测试创建分享链接 (Base ID: {base_id}) ===')
    try:
        data = {
            'permission': 'edit',
            'expires_at': int((datetime.now() + timedelta(days=7)).timestamp())
        }
        response = requests.post(f'{BASE_URL}/bases/{base_id}/shares', json=data, headers=get_headers())
        if response.status_code == 201:
            result = response.json()
            share_token = result['data']['share_token']
            print(f'✓ 创建分享链接成功，Token: {share_token[:8]}...')
            print(f'  权限：{result["data"]["permission"]}')
            print(f'  过期时间：{datetime.fromtimestamp(result["data"]["expires_at"])}')
            return share_token
        else:
            print(f'✗ 创建分享链接失败：{response.text}')
            return None
    except Exception as e:
        print(f'✗ 创建分享链接异常：{e}')
        return None

def test_get_shares(base_id):
    """测试获取分享列表"""
    print(f'\n=== 测试获取分享列表 (Base ID: {base_id}) ===')
    try:
        response = requests.get(f'{BASE_URL}/bases/{base_id}/shares', headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            shares = result['data']
            print(f'✓ 获取分享列表成功，共 {len(shares)} 个分享')
            for share in shares:
                print(f'  - Token: {share["share_token"][:8]}... 权限：{share["permission"]}')
            return True
        else:
            print(f'✗ 获取分享列表失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 获取分享列表异常：{e}')
        return False

def test_access_share(share_token):
    """测试通过分享令牌访问 Base"""
    print(f'\n=== 测试访问分享链接 (Token: {share_token[:8]}...) ===')
    try:
        response = requests.get(f'{BASE_URL}/share/{share_token}')
        if response.status_code == 200:
            result = response.json()
            print(f'✓ 访问分享链接成功')
            print(f'  Base: {result["data"]["base"]["name"]}')
            print(f'  权限：{result["data"]["permission"]}')
            return True
        else:
            print(f'✗ 访问分享链接失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 访问分享链接异常：{e}')
        return False

def test_get_shared_by_me():
    """测试获取我创建的分享"""
    print(f'\n=== 测试获取我创建的分享 ===')
    try:
        response = requests.get(f'{BASE_URL}/bases/shared-by-me', headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            shares = result['data']
            print(f'✓ 获取我创建的分享成功，共 {len(shares)} 个分享')
            return True
        else:
            print(f'✗ 获取我创建的分享失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 获取我创建的分享异常：{e}')
        return False

def test_delete_share(share_id):
    """测试删除分享链接"""
    print(f'\n=== 测试删除分享链接 (Share ID: {share_id}) ===')
    try:
        response = requests.delete(f'{BASE_URL}/shares/{share_id}', headers=get_headers())
        if response.status_code == 200:
            print(f'✓ 删除分享链接成功')
            return True
        else:
            print(f'✗ 删除分享链接失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 删除分享链接异常：{e}')
        return False

def test_remove_member(base_id, user_id):
    """测试移除成员"""
    print(f'\n=== 测试移除成员 (Base ID: {base_id}, User ID: {user_id}) ===')
    try:
        response = requests.delete(f'{BASE_URL}/bases/{base_id}/members/{user_id}', headers=get_headers())
        if response.status_code == 200:
            print(f'✓ 移除成员成功')
            return True
        else:
            print(f'✗ 移除成员失败：{response.text}')
            return False
    except Exception as e:
        print(f'✗ 移除成员异常：{e}')
        return False

def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('成员管理和分享链接功能测试')
    print('=' * 60)
    
    # 1. 登录
    if not login():
        print('\n✗ 测试终止：无法登录')
        return
    
    # 2. 创建 Base
    base_id = test_create_base()
    if not base_id:
        print('\n✗ 测试终止：无法创建 Base')
        return
    
    # 3. 获取成员列表
    test_get_members(base_id)
    
    # 4. 添加成员（可能失败，因为用户可能不存在）
    test_add_member(base_id)
    
    # 5. 创建分享链接
    share_token = test_create_share(base_id)
    
    # 6. 获取分享列表
    test_get_shares(base_id)
    
    # 7. 访问分享链接
    if share_token:
        test_access_share(share_token)
    
    # 8. 获取我创建的分享
    test_get_shared_by_me()
    
    # 9. 删除分享链接
    if share_token:
        # 先获取分享 ID
        response = requests.get(f'{BASE_URL}/bases/{base_id}/shares', headers=get_headers())
        if response.status_code == 200:
            shares = response.json()['data']
            if shares:
                share_id = shares[0]['id']
                test_delete_share(share_id)
    
    print('\n' + '=' * 60)
    print('测试完成')
    print('=' * 60)

if __name__ == '__main__':
    run_all_tests()
