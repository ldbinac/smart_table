# 管理员用户管理系统 API 文档

## 概述

本文档描述了管理员用户管理系统的所有 API 接口。所有管理 API 都需要管理员权限（ADMIN 或 WORKSPACE_ADMIN 角色）。

## 认证

所有 API 请求都需要在 Header 中包含 JWT Token：

```
Authorization: Bearer <your_jwt_token>
```

## 基础信息

- **基础 URL**: `/api/admin`
- **数据格式**: JSON
- **字符编码**: UTF-8

## 用户管理 API

### 1. 获取用户列表

**请求**
```
GET /api/admin/users
```

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| per_page | integer | 否 | 每页数量，默认 20 |
| search | string | 否 | 搜索关键词（邮箱/姓名） |
| role | string | 否 | 角色筛选 (admin/workspace_admin/editor/viewer) |
| status | string | 否 | 状态筛选 (active/inactive/suspended/deleted) |

**响应示例**
```json
{
  "code": 200,
  "message": "获取用户列表成功",
  "data": {
    "users": [
      {
        "id": "uuid",
        "email": "user@example.com",
        "name": "张三",
        "role": "editor",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 100
    }
  }
}
```

### 2. 创建用户

**请求**
```
POST /api/admin/users
```

**请求体**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123",
  "name": "李四",
  "role": "editor"
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "创建用户成功",
  "data": {
    "user": {
      "id": "uuid",
      "email": "newuser@example.com",
      "name": "李四",
      "role": "editor",
      "status": "active",
      "must_change_password": true
    }
  }
}
```

### 3. 获取用户详情

**请求**
```
GET /api/admin/users/:user_id
```

**响应**
```json
{
  "code": 200,
  "message": "获取用户信息成功",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "张三",
      "role": "editor",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

### 4. 更新用户信息

**请求**
```
PUT /api/admin/users/:user_id
```

**请求体**
```json
{
  "email": "newemail@example.com",
  "name": "新名字",
  "role": "workspace_admin",
  "status": "active"
}
```

### 5. 删除用户

**请求**
```
DELETE /api/admin/users/:user_id
```

**响应**
```json
{
  "code": 200,
  "message": "删除用户成功"
}
```

### 6. 更新用户状态

**请求**
```
PUT /api/admin/users/:user_id/status
```

**请求体**
```json
{
  "status": "suspended"
}
```

**可选状态值**
- `active`: 活跃
- `inactive`: 未激活
- `suspended`: 已暂停
- `deleted`: 已删除

### 7. 重置用户密码

**请求**
```
POST /api/admin/users/:user_id/reset-password
```

**请求体（可选）**
```json
{
  "temporary_password": "TempPass123"
}
```

**响应**
```json
{
  "code": 200,
  "message": "重置密码成功",
  "data": {
    "temporary_password": "TempPass123"
  }
}
```

## 系统配置 API

### 1. 获取系统配置

**请求**
```
GET /api/admin/settings
```

**响应**
```json
{
  "code": 200,
  "message": "获取系统配置成功",
  "data": {
    "configs": {
      "system_name": {
        "config_key": "system_name",
        "config_value": "Smart Table",
        "config_group": "basic",
        "description": "系统名称"
      },
      "password_min_length": {
        "config_key": "password_min_length",
        "config_value": 8,
        "config_group": "security",
        "description": "密码最小长度"
      }
    }
  }
}
```

### 2. 更新系统配置

**请求**
```
PUT /api/admin/settings
```

**请求体**
```json
{
  "configs": [
    {
      "key": "system_name",
      "value": "新系统名称",
      "group": "basic",
      "description": "系统名称"
    }
  ]
}
```

## 操作日志 API

### 1. 获取操作日志

**请求**
```
GET /api/admin/operation-logs
```

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码 |
| per_page | integer | 否 | 每页数量 |
| user_id | string | 否 | 操作人 ID |
| action | string | 否 | 操作类型 |
| entity_type | string | 否 | 实体类型 |
| start_date | string | 否 | 开始日期 (ISO 8601) |
| end_date | string | 否 | 结束日期 (ISO 8601) |

**响应**
```json
{
  "code": 200,
  "message": "获取操作日志成功",
  "data": {
    "logs": [
      {
        "id": "uuid",
        "user_id": "uuid",
        "action": "create",
        "entity_type": "user",
        "entity_id": "uuid",
        "old_value": null,
        "new_value": {"email": "user@example.com"},
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 100
    }
  }
}
```

### 2. 导出操作日志

**请求**
```
GET /api/admin/operation-logs/export
```

**查询参数**
同"获取操作日志"

**响应**
- Content-Type: text/csv
- 文件名：operation_logs_YYYYMMDD_HHMMSS.csv

## 角色管理 API

### 1. 获取所有角色

**请求**
```
GET /api/admin/roles
```

**响应**
```json
{
  "code": 200,
  "message": "获取角色列表成功",
  "data": {
    "roles": [
      {
        "name": "admin",
        "label": "管理员",
        "description": "系统管理员，拥有所有权限"
      },
      {
        "name": "workspace_admin",
        "label": "工作区管理员",
        "description": "工作区管理员，拥有工作区管理权限"
      },
      {
        "name": "editor",
        "label": "编辑者",
        "description": "可以编辑数据"
      },
      {
        "name": "viewer",
        "label": "查看者",
        "description": "只能查看数据"
      }
    ]
  }
}
```

## 错误响应

### 通用错误格式
```json
{
  "code": 400,
  "message": "错误描述信息",
  "error": "详细错误信息"
}
```

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 安全注意事项

1. **密码安全**
   - 密码长度至少 8 位
   - 建议包含大小写字母、数字、特殊字符
   - 管理员重置的密码为临时密码，首次登录强制修改

2. **权限控制**
   - 所有管理 API 都需要管理员权限
   - 操作会自动记录到操作日志

3. **数据保护**
   - 删除用户为软删除，数据仍保留在数据库
   - 敏感操作会记录详细日志

## 使用示例

### JavaScript (Axios)
```javascript
const axios = require('axios');

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Authorization': `Bearer ${jwtToken}`
  }
});

// 获取用户列表
async function getUserList() {
  const response = await apiClient.get('/admin/users', {
    params: {
      page: 1,
      per_page: 20,
      search: '张三'
    }
  });
  return response.data;
}

// 创建用户
async function createUser(userData) {
  const response = await apiClient.post('/admin/users', userData);
  return response.data;
}

// 重置密码
async function resetPassword(userId) {
  const response = await apiClient.post(`/admin/users/${userId}/reset-password`);
  return response.data;
}
```

### Python (Requests)
```python
import requests

BASE_URL = 'https://your-domain.com/api'
HEADERS = {
    'Authorization': f'Bearer {jwt_token}',
    'Content-Type': 'application/json'
}

# 获取用户列表
def get_user_list(page=1, per_page=20, search=None):
    params = {'page': page, 'per_page': per_page}
    if search:
        params['search'] = search
    
    response = requests.get(f'{BASE_URL}/admin/users', 
                          headers=HEADERS, params=params)
    return response.json()

# 创建用户
def create_user(email, password, name, role='editor'):
    data = {
        'email': email,
        'password': password,
        'name': name,
        'role': role
    }
    response = requests.post(f'{BASE_URL}/admin/users', 
                           headers=HEADERS, json=data)
    return response.json()

# 重置密码
def reset_password(user_id):
    response = requests.post(f'{BASE_URL}/admin/users/{user_id}/reset-password',
                           headers=HEADERS)
    return response.json()
```

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本
- 用户管理功能
- 系统配置功能
- 操作日志功能
- 角色管理功能
