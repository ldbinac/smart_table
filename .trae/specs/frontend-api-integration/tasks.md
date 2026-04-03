# 前端API集成与数据存储重构任务清单

## 阶段一：API基础设施搭建 ✅

### 任务 1：API客户端封装 ✅
- [x] 1.1 安装Axios并创建基础配置
  - [x] 安装axios依赖
  - [x] 创建 `src/api/config.ts` 配置文件
  - [x] 配置基础URL、超时、重试策略

- [x] 1.2 实现请求/响应拦截器
  - [x] 创建 `src/api/client.ts`（包含拦截器）
  - [x] 实现请求拦截器（添加Token、加载状态）
  - [x] 实现响应拦截器（错误处理、Token刷新）
  - [x] 实现错误拦截器（统一错误提示）

- [x] 1.3 创建API客户端类
  - [x] 创建 `src/api/client.ts`
  - [x] 实现get/post/put/delete/patch/upload方法
  - [x] 实现请求取消功能（AbortController）
  - [x] 实现请求重试机制

- [x] 1.4 类型定义
  - [x] 创建 `src/api/types.ts`
  - [x] 定义ApiResponse统一响应类型
  - [x] 定义ApiError错误类型
  - [x] 定义请求配置类型
  - [x] 定义所有业务类型（User, Base, Table, Field, Record, View, Dashboard, Attachment）

### 任务 2：认证模块开发 ✅
- [x] 2.1 JWT令牌管理
  - [x] 创建 `src/utils/auth/token.ts`
  - [x] 实现Token存储（localStorage/sessionStorage）
  - [x] 实现Token读取和解析
  - [x] 实现Token过期检查

- [x] 2.2 认证服务
  - [x] 创建 `src/services/api/authService.ts`
  - [x] 实现login方法
  - [x] 实现register方法
  - [x] 实现logout方法
  - [x] 实现refreshToken方法
  - [x] 实现getCurrentUser方法

- [x] 2.3 认证状态管理
  - [x] 创建 `src/stores/auth/authStore.ts`
  - [x] 实现用户状态管理
  - [x] 实现登录状态持久化
  - [x] 实现权限状态管理

- [x] 2.4 路由守卫
  - [x] 创建 `src/router/guards.ts`
  - [x] 实现认证守卫（authGuard）
  - [x] 实现权限守卫（permissionGuard）
  - [x] 实现管理员守卫（adminGuard）
  - [x] 实现标题守卫（titleGuard）

## 阶段二：业务服务层重构 ✅

### 任务 3：Base服务迁移 ✅
- [x] 3.1 创建Base API服务
  - [x] 创建 `src/services/api/baseApiService.ts`
  - [x] 实现getBases方法（列表查询）
  - [x] 实现getBase方法（详情查询）
  - [x] 实现createBase方法（创建）
  - [x] 实现updateBase方法（更新）
  - [x] 实现deleteBase方法（删除）
  - [x] 实现toggleArchiveBase方法（归档切换）
  - [x] 实现toggleStarBase方法（收藏切换）
  - [x] 实现duplicateBase方法（复制）
  - [x] 实现成员管理方法（getBaseMembers/addBaseMember/updateMemberRole/removeBaseMember）

- [ ] 3.2 重构Base Store
  - [ ] 修改 `src/stores/baseStore.ts`
  - [ ] 替换IndexedDB调用为API调用
  - [ ] 保持Store接口不变
  - [ ] 添加加载状态管理

### 任务 4：Table服务迁移 ✅
- [x] 4.1 创建Table API服务
  - [x] 创建 `src/services/api/tableApiService.ts`
  - [x] 实现getTables方法
  - [x] 实现getTable方法
  - [x] 实现createTable方法
  - [x] 实现updateTable方法
  - [x] 实现deleteTable方法
  - [x] 实现duplicateTable方法（复制）
  - [x] 实现reorderTables方法

- [ ] 4.2 重构Table Store
  - [ ] 修改 `src/stores/tableStore.ts`
  - [ ] 替换IndexedDB调用为API调用
  - [ ] 更新Table类型定义

### 任务 5：Field服务迁移 ✅
- [x] 5.1 创建Field API服务
  - [x] 创建 `src/services/api/fieldApiService.ts`
  - [x] 实现getFields方法
  - [x] 实现createField方法
  - [x] 实现updateField方法
  - [x] 实现deleteField方法
  - [x] 实现reorderFields方法
  - [x] 实现getFieldTypes方法

- [ ] 5.2 重构Field Store
  - [ ] 修改 `src/stores/fieldStore.ts`
  - [ ] 替换IndexedDB调用为API调用

### 任务 6：Record服务迁移 ✅
- [x] 6.1 创建Record API服务
  - [x] 创建 `src/services/api/recordApiService.ts`
  - [x] 实现getRecords方法（支持分页）
  - [x] 实现getRecord方法
  - [x] 实现createRecord方法
  - [x] 实现updateRecord方法
  - [x] 实现deleteRecord方法
  - [x] 实现batchCreateRecords方法
  - [x] 实现batchUpdateRecords方法
  - [x] 实现batchDeleteRecords方法
  - [x] 实现computeFormulas方法

- [ ] 6.2 重构Record Store
  - [ ] 修改 `src/stores/recordStore.ts`
  - [ ] 替换IndexedDB调用为API调用
  - [ ] 更新分页逻辑

### 任务 7：View服务迁移 ✅
- [x] 7.1 创建View API服务
  - [x] 创建 `src/services/api/viewApiService.ts`
  - [x] 实现getViews方法
  - [x] 实现getView方法
  - [x] 实现createView方法
  - [x] 实现updateView方法
  - [x] 实现deleteView方法
  - [x] 实现duplicateView方法
  - [x] 实现setDefaultView方法
  - [x] 实现reorderViews方法
  - [x] 实现getViewTypes方法

- [ ] 7.2 重构View Store
  - [ ] 修改 `src/stores/viewStore.ts`
  - [ ] 替换IndexedDB调用为API调用

## 阶段三：用户界面开发 ✅

### 任务 8：登录页面 ✅
- [x] 8.1 登录表单组件
  - [x] 创建 `src/components/auth/LoginForm.vue`
  - [x] 实现邮箱/密码输入
  - [x] 实现表单验证
  - [x] 实现记住登录状态选项
  - [x] 实现登录按钮和加载状态

- [x] 8.2 登录页面
  - [x] 创建 `src/views/auth/Login.vue`
  - [x] 集成LoginForm组件
  - [x] 实现登录成功跳转
  - [x] 实现登录失败提示
  - [x] 添加注册入口链接

### 任务 9：注册页面 ✅
- [x] 9.1 注册表单组件
  - [x] 创建 `src/components/auth/RegisterForm.vue`
  - [x] 实现用户名/邮箱/密码输入
  - [x] 实现密码确认验证
  - [x] 实现表单验证规则
  - [x] 实现注册按钮和加载状态

- [x] 9.2 注册页面
  - [x] 创建 `src/views/auth/Register.vue`
  - [x] 集成RegisterForm组件
  - [x] 实现注册成功处理
  - [x] 实现注册失败提示
  - [x] 添加登录入口链接

### 任务 10：用户管理模块（部分完成）
- [ ] 10.1 用户资料页面
  - [ ] 创建 `src/views/UserProfile.vue`
  - [ ] 实现用户信息展示
  - [ ] 实现信息编辑功能
  - [ ] 实现密码修改功能

- [ ] 10.2 用户列表（管理员）
  - [ ] 创建 `src/views/admin/UserList.vue`
  - [ ] 实现用户列表展示
  - [ ] 实现用户状态管理
  - [ ] 实现权限分配功能

### 任务 11：Base成员管理 ✅
- [x] 11.1 成员列表组件
  - [x] 创建 `src/components/base/MemberList.vue`
  - [x] 实现成员列表展示
  - [x] 实现角色显示
  - [x] 实现分页功能

- [x] 11.2 添加成员对话框
  - [x] 创建 `src/components/base/AddMemberDialog.vue`
  - [x] 实现用户搜索功能
  - [x] 实现角色选择
  - [x] 实现添加确认

- [x] 11.3 成员管理页面
  - [x] 创建 `src/views/base/MemberManagement.vue`
  - [x] 集成MemberList组件
  - [x] 集成AddMemberDialog组件
  - [x] 实现编辑成员角色
  - [x] 实现移除成员功能

## 阶段四：全局功能完善 ✅

### 任务 12：加载状态管理 ✅
- [x] 12.1 全局加载指示器
  - [x] 创建 `src/stores/loadingStore.ts`
  - [x] 实现请求计数器
  - [x] 实现延迟显示（避免闪烁）

- [x] 12.2 请求加载关联
  - [x] 在拦截器中集成加载状态
  - [x] 实现加载状态管理

### 任务 13：错误提示系统 ✅
- [x] 13.1 消息提示组件
  - [x] 使用Element Plus ElMessage/ElNotification
  - [x] 实现成功/错误/警告提示
  - [x] 实现自动关闭
  - [x] 实现手动关闭

- [x] 13.2 消息服务
  - [x] 创建 `src/utils/message.ts`
  - [x] 实现message.success方法
  - [x] 实现message.error方法
  - [x] 实现message.warning方法
  - [x] 实现message.info方法

- [x] 13.3 错误处理集成
  - [x] 在响应拦截器中调用消息提示
  - [x] 实现错误分类处理
  - [x] 实现网络错误特殊处理

### 任务 14：权限指令与组件（待完成）
- [ ] 14.1 权限指令
  - [ ] 创建 `src/directives/permission.ts`
  - [ ] 实现v-permission指令
  - [ ] 实现v-role指令

- [ ] 14.2 权限控制组件
  - [ ] 创建 `src/components/common/PermissionWrapper.vue`
  - [ ] 实现基于权限的内容显示控制
  - [ ] 实现基于角色的内容显示控制

## 阶段五：测试与优化（待完成）

### 任务 15：单元测试
- [ ] 15.1 API客户端测试
  - [ ] 测试请求拦截器
  - [ ] 测试响应拦截器
  - [ ] 测试错误处理

- [ ] 15.2 服务层测试
  - [ ] 测试AuthService
  - [ ] 测试BaseService
  - [ ] 测试TableService

- [ ] 15.3 Store测试
  - [ ] 测试AuthStore
  - [ ] 测试BaseStore

### 任务 16：集成测试
- [ ] 16.1 认证流程测试
  - [ ] 测试登录流程
  - [ ] 测试注册流程
  - [ ] 测试Token刷新

- [ ] 16.2 数据操作测试
  - [ ] 测试CRUD操作
  - [ ] 测试批量操作
  - [ ] 测试分页功能

### 任务 17：性能优化
- [ ] 17.1 请求优化
  - [ ] 实现请求去重
  - [ ] 实现请求缓存
  - [ ] 实现请求合并

- [ ] 17.2 加载优化
  - [ ] 实现路由懒加载
  - [ ] 实现组件按需加载
  - [ ] 优化首屏加载速度

## 任务依赖关系

```
阶段一：API基础设施 ✅
├── 1.1-1.4 API客户端封装 ✅
└── 2.1-2.4 认证模块 ✅
    │
    ▼
阶段二：业务服务层 ✅（API服务完成，Store重构待完成）
├── 3.1-3.2 Base服务 ✅
├── 4.1-4.2 Table服务 ✅
├── 5.1-5.2 Field服务 ✅
├── 6.1-6.2 Record服务 ✅
└── 7.1-7.2 View服务 ✅
    │
    ▼
阶段三：用户界面 ✅（核心页面完成）
├── 8.1-8.2 登录页面 ✅
├── 9.1-9.2 注册页面 ✅
├── 10.1-10.2 用户管理（部分完成）
└── 11.1-11.3 成员管理 ✅
    │
    ▼
阶段四：全局功能 ✅（核心功能完成）
├── 12.1-12.2 加载状态 ✅
├── 13.1-13.3 错误提示 ✅
└── 14.1-14.2 权限控制（待完成）
    │
    ▼
阶段五：测试优化（待完成）
├── 15.1-15.3 单元测试
├── 16.1-16.2 集成测试
└── 17.1-17.2 性能优化
```

## 已创建文件清单

### API基础设施
- `src/api/types.ts` - 类型定义
- `src/api/config.ts` - API配置
- `src/api/client.ts` - API客户端

### 工具函数
- `src/utils/auth/token.ts` - Token管理
- `src/utils/message.ts` - 消息提示

### 服务层
- `src/services/api/index.ts` - 服务索引
- `src/services/api/authService.ts` - 认证服务
- `src/services/api/baseApiService.ts` - Base服务
- `src/services/api/tableApiService.ts` - Table服务
- `src/services/api/fieldApiService.ts` - Field服务
- `src/services/api/recordApiService.ts` - Record服务
- `src/services/api/viewApiService.ts` - View服务

### 状态管理
- `src/stores/auth/authStore.ts` - 认证状态
- `src/stores/loadingStore.ts` - 加载状态

### 路由
- `src/router/guards.ts` - 路由守卫
- `src/router/index.ts` - 路由配置（已更新）

### 组件
- `src/components/auth/LoginForm.vue` - 登录表单
- `src/components/auth/RegisterForm.vue` - 注册表单
- `src/components/base/MemberList.vue` - 成员列表
- `src/components/base/AddMemberDialog.vue` - 添加成员对话框

### 页面
- `src/views/auth/Login.vue` - 登录页面
- `src/views/auth/Register.vue` - 注册页面
- `src/views/base/MemberManagement.vue` - 成员管理页面

## 下一步工作

1. **Store层重构** - 将现有Store从IndexedDB迁移到API调用
2. **权限指令** - 实现v-permission和v-role指令
3. **用户资料页面** - 完善用户管理功能
4. **测试覆盖** - 编写单元测试和集成测试
5. **性能优化** - 实现请求缓存和组件懒加载
