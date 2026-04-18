# 管理员菜单显示问题排查与验证

## 问题描述

ADMIN 角色用户登录后，左侧导航菜单未显示"系统管理"菜单选项。

## 问题原因

**已定位**: `authStore.isAdmin` 计算属性只检查了 `'admin'` 角色，未包含 `'workspace_admin'` 角色。

### 修复前
```typescript
const isAdmin = computed(() => user.value?.role === 'admin');
```

### 修复后
```typescript
const isAdmin = computed(() => {
  const userRole = user.value?.role;
  return userRole === 'admin' || userRole === 'workspace_admin';
});
```

## 验证步骤

### 1. 检查用户角色

登录 ADMIN 或 WORKSPACE_ADMIN 角色账号后，在浏览器控制台执行：

```javascript
// 检查当前用户角色
console.log('用户角色:', authStore.user.role);
console.log('是否为管理员:', authStore.isAdmin);
```

**预期结果**:
- `user.role` 应该是 `'admin'` 或 `'workspace_admin'`
- `isAdmin` 应该返回 `true`

### 2. 检查菜单渲染

在浏览器控制台执行：

```javascript
// 检查导航菜单项
import { useAuthStore } from '@/stores/authStore';
const authStore = useAuthStore();
console.log('isAdmin:', authStore.isAdmin);
```

**预期结果**:
- 控制台应显示 `isAdmin: true`
- 左侧菜单应显示"系统管理"及其子菜单

### 3. 访问管理页面

尝试直接访问以下 URL：
- `/admin/users` - 用户管理
- `/admin/settings` - 系统配置
- `/admin/logs` - 操作日志

**预期结果**:
- 页面正常加载
- 不会出现 403 错误

### 4. 测试不同角色

#### 测试 ADMIN 角色
1. 使用 ADMIN 角色账号登录
2. 检查是否显示"系统管理"菜单
3. 尝试访问管理页面

**预期**: 菜单显示，页面可访问

#### 测试 WORKSPACE_ADMIN 角色
1. 使用 WORKSPACE_ADMIN 角色账号登录
2. 检查是否显示"系统管理"菜单
3. 尝试访问管理页面

**预期**: 菜单显示，页面可访问

#### 测试 EDITOR 角色
1. 使用 EDITOR 角色账号登录
2. 检查是否显示"系统管理"菜单
3. 尝试直接访问 `/admin/users`

**预期**: 菜单不显示，访问管理页面跳转到 403

### 5. 检查后端 API

使用 ADMIN 角色调用管理 API：

```bash
# 获取用户列表
curl -H "Authorization: Bearer <your_token>" \
     http://localhost:5000/api/admin/users
```

**预期结果**: API 正常返回数据

## 相关文件

### 前端文件
- `src/stores/authStore.ts` - 认证状态管理（已修复）
- `src/components/common/AppSidebar.vue` - 侧边栏菜单组件
- `src/router/guards.ts` - 路由守卫
- `src/router/index.ts` - 路由配置

### 后端文件
- `app/utils/decorators.py` - 权限装饰器
- `app/routes/admin.py` - 管理 API 路由
- `app/models/user.py` - 用户模型

## 角色对照表

| 角色 | 值 | 是否管理员 | 可访问管理功能 |
|------|-----|-----------|--------------|
| 管理员 | `admin` | ✅ | ✅ |
| 工作区管理员 | `workspace_admin` | ✅ | ✅ |
| 编辑者 | `editor` | ❌ | ❌ |
| 查看者 | `viewer` | ❌ | ❌ |

## 常见问题

### Q1: 修复后仍然看不到菜单怎么办？

**排查步骤**:
1. 清除浏览器缓存
2. 重新登录
3. 检查控制台是否有错误信息
4. 确认 `authStore.user.role` 的值

### Q2: 菜单显示了但访问页面 403 怎么办？

**可能原因**:
- 路由守卫未正确应用
- 后端权限装饰器检查失败

**排查步骤**:
1. 检查路由配置中 `beforeEnter: adminGuard` 是否存在
2. 检查后端 API 是否有 `@admin_required` 装饰器
3. 检查 JWT token 是否有效

### Q3: WORKSPACE_ADMIN 角色无法访问怎么办？

**检查项目**:
1. 确认后端 `admin_required` 装饰器包含 `workspace_admin`
2. 确认前端 `isAdmin` 计算属性包含 `workspace_admin`
3. 检查数据库中用户角色字段值

## 代码检查清单

- [x] `authStore.isAdmin` 包含 `admin` 和 `workspace_admin`
- [x] `adminGuard` 使用 `authStore.isAdmin`
- [x] 路由配置中管理页面应用 `adminGuard`
- [x] `AppSidebar.vue` 使用 `authStore.isAdmin` 控制菜单显示
- [x] 后端 `admin_required` 装饰器检查两种角色
- [x] 所有管理 API 都有 `@admin_required` 保护

## 测试报告模板

### 测试环境
- 浏览器：Chrome / Firefox / Edge
- 前端版本：[填写]
- 后端版本：[填写]

### 测试结果

| 测试项 | ADMIN 角色 | WORKSPACE_ADMIN 角色 | EDITOR 角色 |
|--------|-----------|---------------------|------------|
| 菜单显示 | ✅/❌ | ✅/❌ | ✅/❌ |
| 用户管理页面访问 | ✅/❌ | ✅/❌ | ✅/❌ |
| 系统配置页面访问 | ✅/❌ | ✅/❌ | ✅/❌ |
| 操作日志页面访问 | ✅/❌ | ✅/❌ | ✅/❌ |
| API 调用成功 | ✅/❌ | ✅/❌ | ✅/❌ |

### 问题记录

如有问题，请记录：
1. 问题描述
2. 复现步骤
3. 错误信息
4. 截图

## 更新日志

### v1.0.1 (2024-01-01)
- 修复：`authStore.isAdmin` 现在支持 `admin` 和 `workspace_admin` 两种角色
- 影响：WORKSPACE_ADMIN 角色用户现在可以看到系统管理菜单

### v1.0.0 (2024-01-01)
- 初始版本
- 实现管理员用户管理系统
