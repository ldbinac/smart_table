# 退出登录功能实现规范

## Why

当前系统已有基础的认证框架和 logout API 接口，但缺少完整的用户界面交互和端到端的退出流程。需要实现完整的退出登录功能，包括：

1. 前端用户界面中添加明显的退出登录按钮
2. 完善退出登录的用户体验（加载状态、确认提示、重定向）
3. 确保前端清除本地认证信息的完整性
4. 后端已实现 token 撤销功能，需要确保与前端集成的完整性

## What Changes

### 前端变化

* **在 AppHeader 组件中添加用户下拉菜单**：包含用户信息和退出登录按钮

* **实现退出登录确认对话框**：防止误操作，提升用户体验

* **完善 logout 流程**：清除本地存储、重置状态、重定向到登录页

* **添加加载状态和反馈**：退出过程中显示加载提示

* **处理异常情况**：网络错误时也能安全退出（清除本地状态）

### 后端变化

* **已实现**：`/api/auth/logout` 接口（POST）- 撤销当前 token

* **已实现**：`/api/auth/logout-all` 接口（POST）- 撤销所有设备 token

* **已实现**：AuthService.logout\_user() - 令牌撤销逻辑

* **已实现**：AuthService.revoke\_all\_user\_tokens() - 撤销所有令牌

* **无需修改**：后端功能已完整实现

## Impact

### 影响的前端文件

* `d:\_dev\fs_table\smart-table-spec\smart-table\src\components\common\AppHeader.vue` - 添加用户菜单和退出按钮

* `d:\_dev\fs_table\smart-table-spec\smart-table\src\stores\auth\authStore.ts` - 完善 logout 方法

* `d:\_dev\fs_table\smart-table-spec\smart-table\src\views\auth\Login.vue` - 处理退出后的重定向

* `d:\_dev\fs_table\smart-table-spec\smart-table\src\router\guards.ts` - 已实现认证守卫

### 影响的后端文件

* `d:\_dev\fs_table\smart-table-spec\smarttable-backend\app\routes\auth.py` - 已实现 logout 接口

* `d:\_dev\fs_table\smart-table-spec\smarttable-backend\app\services\auth_service.py` - 已实现认证服务

## ADDED Requirements

### Requirement: 前端退出登录按钮

The system SHALL provide a visible logout button in the user header area

* 位于头部右侧用户头像区域

* 点击后显示下拉菜单，包含用户信息和"退出登录"选项

* 支持键盘快捷键操作（可选）

#### Scenario: 用户点击退出登录

* **WHEN** 用户点击退出登录按钮

* **THEN** 显示确认对话框，询问是否确认退出

### Requirement: 退出确认对话框

The system SHALL display a confirmation dialog before logout

* 显示友好的确认提示信息

* 提供"取消"和"确认退出"两个选项

* 防止用户误操作

#### Scenario: 确认退出

* **WHEN** 用户在确认对话框中点击"确认退出"

* **THEN** 执行退出流程，显示加载状态

### Requirement: 清除本地认证信息

The system SHALL clear all authentication data from local storage

* 清除 localStorage 中的 access\_token 和 refresh\_token（如果选择记住登录）

* 清除 sessionStorage 中的 access\_token 和 refresh\_token（如果未选择记住登录）

* 清除用户信息缓存

* 重置认证状态为未登录

#### Scenario: 清除 Token

* **WHEN** 退出登录执行时

* **THEN** 清除所有存储的 token 和用户信息

### Requirement: 重定向到登录页

The system SHALL redirect user to login page after successful logout

* 退出完成后自动跳转到 `/login` 页面

* 清除 URL 中的查询参数（如 redirect 等）

* 显示友好的退出成功提示

#### Scenario: 退出成功

* **WHEN** 退出流程完成

* **THEN** 跳转到登录页面，显示"已安全退出"提示

### Requirement: 后端 Token 撤销

The system SHALL invalidate the current access token on server side

* 调用 `/api/auth/logout` 接口

* 将当前 access token 加入黑名单

* 防止 token 被重复使用

#### Scenario: 正常退出

* **WHEN** 用户确认退出且网络连接正常

* **THEN** 后端撤销 token，返回成功响应

### Requirement: 异常处理

The system SHALL handle network errors gracefully during logout

* 网络错误时也要清除本地状态

* 显示友好的错误提示

* 确保用户能够重新登录

#### Scenario: 网络异常

* **WHEN** 退出时网络不可用或 API 调用失败

* **THEN** 仍然清除本地状态，允许用户重新登录

### Requirement: 多设备退出（可选增强功能）

The system SHALL provide an option to logout from all devices

* 在退出菜单中提供"退出所有设备"选项

* 调用 `/api/auth/logout-all` 接口

* 撤销用户的所有 token

#### Scenario: 从所有设备退出

* **WHEN** 用户选择"退出所有设备"

* **THEN** 撤销该用户的所有 token，强制所有设备重新登录

## MODIFIED Requirements

### Requirement: 现有 logout 方法增强

原有 authStore 中的 logout 方法需要增强：

```typescript
// 原实现
const logout = async (): Promise<void> => {
  try {
    await authService.logout()
  } catch {
    // 忽略错误
  } finally {
    clearToken()
    user.value = null
    isAuthenticated.value = false
    message.success('已安全退出')
  }
}

// 新实现需要：
// 1. 添加 loading 状态
// 2. 添加退出确认步骤
// 3. 完善错误处理
// 4. 添加重定向逻辑
```

## REMOVED Requirements

无

## Security Considerations

### 安全验证机制

1. **JWT 验证**：logout 接口需要有效的 access token（通过 @flask\_jwt\_required 装饰器）
2. **Token 黑名单**：退出的 token 被加入黑名单，无法再次使用
3. **本地清理**：确保本地不残留任何认证信息
4. **防止 CSRF**：使用 JWT 认证，不依赖 Cookie

### 多设备登录状态处理

1. **单设备退出**：仅撤销当前设备的 token，其他设备不受影响
2. **全设备退出**：撤销用户所有 token，所有设备需要重新登录
3. **Token 刷新处理**：退出的 token 无法再用于刷新

## Testing Requirements

### 端到端测试场景

1. **正常退出流程**

   * 点击退出按钮 → 确认退出 → 清除 token → 跳转登录页

2. **网络异常场景**

   * 断开网络 → 点击退出 → 仍清除本地状态 → 跳转登录页

3. **多设备登录**

   * 设备 A 登录 → 设备 B 登录 → 设备 A 退出 → 验证设备 B 状态

4. **Token 失效验证**

   * 退出后 → 尝试使用旧 token 访问 API → 应返回 401

5. **刷新 Token 测试**

   * 退出后 → 尝试使用旧 refresh token → 应返回 401

6. **重复退出测试**

   * 退出后 → 再次调用 logout API → 应正确处理

7. **浏览器多标签页**

   * 标签页 A 退出 → 标签页 B 应同步退出状态

