# 退出所有设备功能修复说明

## 问题描述

之前点击"退出所有设备"后，其他浏览器的登录状态仍然有效，因为 `revoke_all_user_tokens()` 方法只是简单地增加了缓存中的版本号，但没有在生成 token 时包含版本号，也没有在验证 token 时检查版本号。

## 解决方案

实现了基于版本号的令牌失效机制：

### 1. 生成 Token 时包含版本号

**文件**: `app/services/auth_service.py`

```python
@staticmethod
def generate_tokens(user_id: str) -> Dict[str, Any]:
    # 获取当前令牌版本号
    cache_key = f"user_token_version:{user_id}"
    token_version = cache.get(cache_key) or 0
    
    # 创建访问令牌，包含版本号
    access_token = create_access_token(
        identity=user_id,
        expires_delta=timedelta(seconds=AuthService.ACCESS_TOKEN_EXPIRES),
        additional_claims={'token_version': token_version}
    )
    
    # 创建刷新令牌，包含版本号
    refresh_token = create_refresh_token(
        identity=user_id,
        expires_delta=timedelta(seconds=AuthService.REFRESH_TOKEN_EXPIRES),
        additional_claims={'token_version': token_version}
    )
```

### 2. 验证 Token 时检查版本号

**文件**: `app/extensions.py`

```python
@jwt_manager.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """检查令牌是否被撤销"""
    from app.models.user import TokenBlocklist
    from app.extensions import cache
    
    jti = jwt_payload["jti"]
    user_id = jwt_payload.get("sub")
    
    # 先检查是否在黑名单中
    token = TokenBlocklist.query.filter_by(jti=jti).first()
    if token is not None:
        return True
    
    # 检查令牌版本号（用于退出所有设备功能）
    cache_key = f"user_token_version:{user_id}"
    current_version = cache.get(cache_key) or 0
    token_version = jwt_payload.get('token_version', 0)
    
    # 如果令牌版本号小于当前版本号，说明令牌已失效
    if token_version < current_version:
        return True
    
    return False
```

### 3. 退出所有设备时增加版本号

**文件**: `app/services/auth_service.py`（已有实现）

```python
@staticmethod
def revoke_all_user_tokens(user_id: str) -> bool:
    cache_key = f"user_token_version:{user_id}"
    current_version = cache.get(cache_key) or 0
    cache.set(cache_key, current_version + 1, timeout=2592000)  # 30 天
    return True
```

## 工作流程

1. **用户首次登录**
   - 缓存中没有版本号，默认为 0
   - 生成的 token 包含 `token_version: 0`

2. **多设备登录**
   - 设备 A 登录：生成 token (version=0)
   - 设备 B 登录：生成 token (version=0)

3. **退出所有设备**
   - 调用 `revoke_all_user_tokens()`
   - 缓存中的版本号变为 1
   - 当前设备的 token 也被加入黑名单

4. **后续请求验证**
   - 设备 A 的 token (version=0) < 当前版本 (version=1) → 失效
   - 设备 B 的 token (version=0) < 当前版本 (version=1) → 失效

## 修改的文件

1. **`app/services/auth_service.py`**
   - 修改 `generate_tokens()` 方法，添加版本号到 token claims

2. **`app/extensions.py`**
   - 修改 `check_if_token_revoked()` 方法，添加版本号检查

## 测试步骤

### 准备
1. 重启后端服务
2. 清除 Redis 缓存（可选）

### 测试 1: 单设备退出
1. 浏览器 A 登录
2. 点击"退出登录"
3. 验证：成功退出，跳转到登录页

### 测试 2: 多设备退出
1. 浏览器 A 登录
2. 浏览器 B（或无痕模式）登录同一账号
3. 在浏览器 A 点击"退出所有设备"
4. 验证浏览器 A：成功退出，跳转到登录页
5. 在浏览器 B 尝试操作（如访问 API 或刷新页面）
6. 验证浏览器 B：应该收到 401 错误，跳转到登录页

### 测试 3: Token 失效验证
1. 浏览器 A 登录
2. 复制当前 token
3. 点击"退出所有设备"
4. 使用旧 token 调用 API
5. 验证：应该返回 401 Unauthorized

## 注意事项

1. **缓存依赖**: 该功能依赖 Redis 缓存，确保 Redis 服务正常运行
2. **缓存过期时间**: 版本号缓存 30 天过期，之后用户需要重新登录
3. **向后兼容**: 旧的 token 没有 `token_version` claim，会被视为 version=0
4. **性能影响**: 每次 token 验证都需要读取缓存，但 Redis 性能很高，影响可忽略

## 验证成功标志

- [ ] 多设备登录后，退出所有设备成功
- [ ] 所有设备的 token 都失效
- [ ] 后端无错误日志
- [ ] 前端显示正确的提示信息

## 后续优化建议

1. **持久化版本号**: 可以将版本号存储到数据库，避免 Redis 重启后失效
2. **细粒度控制**: 可以为每个设备生成不同的版本号，实现单独退出某个设备
3. **监控日志**: 添加退出所有设备的日志记录，便于审计
