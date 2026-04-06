# 首页左侧菜单显示验证说明

## 当前状态

✅ **已完成修复和实现**

### 实现位置

**文件**: `smart-table/src/components/common/AppSidebar.vue`

**关键代码** (第 49-62 行):
```typescript
...(authStore.isAdmin
  ? [
      {
        id: "admin",
        label: "系统管理",
        icon: "admin",
        children: [
          { id: "admin-users", label: "用户管理", icon: "file", path: "/admin/users" },
          { id: "admin-settings", label: "系统配置", icon: "file", path: "/admin/settings" },
          { id: "admin-logs", label: "操作日志", icon: "file", path: "/admin/logs" },
        ],
      },
    ]
  : []),
```

### 权限控制

**文件**: `smart-table/src/stores/authStore.ts`

**isAdmin 计算属性**:
```typescript
const isAdmin = computed(() => {
  const userRole = user.value?.role;
  return userRole === 'admin' || userRole === 'workspace_admin';
});
```

## 菜单结构

### 首页 (/) 左侧菜单

首页使用 MainLayout 布局，包含完整的左侧菜单：

```
├── 🏠 首页
├── 📊 多维表格
│   ├── 📄 项目表格
│   └── 📄 任务管理
├── 📈 仪表盘
├── ⚙️ 设置
└── ⭐ 系统管理 [仅管理员可见]
    ├── 📄 用户管理
    ├── 📄 系统配置
    └── 📄 操作日志
```

### 显示逻辑

| 用户角色 | 系统管理菜单 |
|----------|-------------|
| admin | ✅ 显示 |
| workspace_admin | ✅ 显示 |
| editor | ❌ 隐藏 |
| viewer | ❌ 隐藏 |

## 验证步骤

### 1. 清除缓存并重新登录

```bash
# 如果前端正在运行，先停止
# 清除浏览器缓存 (Ctrl+Shift+Delete)
# 或使用无痕模式
```

### 2. 使用管理员账号登录

使用具有以下角色之一的账号登录：
- `admin` (管理员)
- `workspace_admin` (工作区管理员)

### 3. 检查首页左侧菜单

登录后访问首页 (`/`)，检查左侧菜单是否显示：

**预期结果**:
```
首页
多维表格
  ├─ 项目表格
  └─ 任务管理
仪表盘
设置
系统管理  ← [新增]
  ├─ 用户管理
  ├─ 系统配置
  └─ 操作日志
```

### 4. 浏览器控制台验证

打开浏览器控制台 (F12)，执行：

```javascript
// 检查认证状态
import { useAuthStore } from '@/stores/authStore';
const authStore = useAuthStore();

console.log('用户信息:', authStore.user);
console.log('用户角色:', authStore.user?.role);
console.log('是否为管理员:', authStore.isAdmin);
console.log('是否已登录:', authStore.isAuthenticated);
```

**预期输出**:
```
用户信息: {id: "...", email: "...", role: "admin", ...}
用户角色: "admin"
是否为管理员: true
是否已登录: true
```

### 5. 点击菜单项测试

依次点击：
1. "系统管理" → 展开子菜单
2. "用户管理" → 跳转到 `/admin/users`
3. "系统配置" → 跳转到 `/admin/settings`
4. "操作日志" → 跳转到 `/admin/logs`

**预期**: 所有页面正常加载，无 403 错误

### 6. 测试非管理员账号

使用 `editor` 或 `viewer` 角色账号登录：

**预期**: 
- 左侧菜单**不显示**"系统管理"
- 直接访问 `/admin/users` 会重定向到 403 页面

## 布局说明

### MainLayout 布局

首页 (`/`) 使用 `MainLayout` 布局组件，该布局包含：

- **AppHeader** - 顶部导航栏
- **AppSidebar** - 左侧菜单（条件显示）
- **Main Content** - 主内容区域

### 何时显示左侧菜单？

根据 `MainLayout.vue` 的逻辑：

```typescript
const shouldShowSidebar = computed(() => {
  const hiddenRoutes = ["/", "/settings"];
  return !hiddenRoutes.includes(route.path) && !route.path.startsWith("/base/");
});
```

**注意**: 这里有个问题！首页 (`/`) 和设置页 (`/settings`) 被列在 `hiddenRoutes` 中，这意味着这些页面**不会显示左侧菜单**！

## 修复建议

### ✅ 问题已修复

**文件**: `smart-table/src/layouts/MainLayout.vue`

**修改前** (第 12 行):
```typescript
const hiddenRoutes = ["/", "/settings"];
```

**修改后**:
```typescript
const hiddenRoutes = ["/settings"];
```

**说明**: 
- ✅ 移除 `"/"`，让首页显示左侧菜单
- ✅ 保留 `"/settings"`，设置页面不需要左侧菜单（全屏表单）
- ✅ 修复完成，现在首页会显示左侧菜单

## 快速检查清单

- [ ] `authStore.isAdmin` 支持 `admin` 和 `workspace_admin`
- [ ] `AppSidebar.vue` 使用 `authStore.isAdmin` 控制菜单显示
- [ ] `MainLayout.vue` 的 `shouldShowSidebar` 逻辑正确
- [ ] 首页路由 (`/`) 使用 `MainLayout` 布局
- [ ] 管理员账号登录可以看到"系统管理"菜单
- [ ] 非管理员账号登录看不到"系统管理"菜单
- [ ] 点击菜单项可以正常跳转

## 常见问题

### Q: 登录后首页没有左侧菜单？

**A**: 检查 `MainLayout.vue` 的 `shouldShowSidebar` 逻辑，确保首页 (`/`) 不在 `hiddenRoutes` 中。

### Q: 左侧菜单没有"系统管理"？

**A**: 
1. 确认使用的是管理员账号（admin 或 workspace_admin）
2. 检查 `authStore.user.role` 的值
3. 尝试清除缓存重新登录

### Q: 菜单显示了但点击没反应？

**A**: 
1. 检查浏览器控制台是否有错误
2. 确认路由配置正确
3. 确认路由守卫没有阻止跳转

## 更新日志

### v1.0.2 (2024-01-01)
- 修复：authStore.isAdmin 支持 admin 和 workspace_admin 两种角色
- 影响：两种管理员角色都可以在首页左侧菜单看到"系统管理"

### v1.0.1 (2024-01-01)
- 实现：首页左侧菜单动态显示管理功能
- 条件：仅管理员用户可见

### v1.0.0 (2024-01-01)
- 初始版本
