# 前端API集成与数据存储重构规范

## 背景与目标

基于已完成的Flask后端API，将前端从IndexedDB本地存储全面迁移为RESTful API调用，构建完整的前后端分离多维表格管理系统。

## 当前状态

- ✅ Flask后端已完成（50+ API端点）
- ✅ 数据库模型与迁移脚本就绪
- ✅ Docker部署配置完成
- ⚠️ 前端仍使用IndexedDB本地存储
- ⚠️ 缺少API客户端封装
- ⚠️ 用户认证模块待完善

## 需求变更

### ADDED: 前端数据存储重构

#### Requirement: API客户端封装层
系统应提供统一的API客户端，处理所有HTTP通信。

**Scenario: 请求发送**
- **WHEN** 前端需要调用后端API
- **THEN** 通过封装层发送请求，自动处理Token、错误、超时

**Scenario: 响应处理**
- **WHEN** 收到后端响应
- **THEN** 统一解析响应格式，处理成功/错误状态

**Scenario: 错误处理**
- **WHEN** 请求失败或返回错误
- **THEN** 统一处理错误，显示友好提示

#### Requirement: IndexedDB迁移
系统应将现有IndexedDB操作替换为API调用。

**Scenario: 数据查询**
- **WHEN** 用户查询数据
- **THEN** 通过API获取数据，不再从IndexedDB读取

**Scenario: 数据修改**
- **WHEN** 用户增删改数据
- **THEN** 通过API提交变更，后端持久化到PostgreSQL

### ADDED: 用户认证与授权模块

#### Requirement: 用户注册功能
系统应提供用户注册界面和功能。

**Scenario: 注册成功**
- **GIVEN** 用户填写有效注册信息
- **WHEN** 提交注册表单
- **THEN** 创建用户账号，自动登录

**Scenario: 注册验证**
- **GIVEN** 用户填写无效信息
- **WHEN** 提交注册表单
- **THEN** 显示验证错误，阻止提交

#### Requirement: 用户登录功能
系统应提供用户登录界面和功能。

**Scenario: 登录成功**
- **GIVEN** 用户输入正确凭证
- **WHEN** 提交登录表单
- **THEN** 获取JWT令牌，进入系统

**Scenario: 登录失败**
- **GIVEN** 用户输入错误凭证
- **WHEN** 提交登录表单
- **THEN** 显示错误提示，限制重试次数

#### Requirement: JWT令牌管理
系统应安全存储和管理JWT令牌。

**Scenario: 令牌存储**
- **WHEN** 登录成功
- **THEN** 安全存储Access Token和Refresh Token

**Scenario: 令牌刷新**
- **GIVEN** Access Token即将过期
- **WHEN** 发送请求前
- **THEN** 自动使用Refresh Token获取新令牌

**Scenario: 令牌过期**
- **GIVEN** 令牌已过期且无法刷新
- **WHEN** 用户尝试访问受保护资源
- **THEN** 重定向到登录页面

#### Requirement: 权限控制
系统应基于用户角色控制访问权限。

**Scenario: 页面访问控制**
- **GIVEN** 用户无权限访问某页面
- **WHEN** 尝试访问该页面
- **THEN** 显示403错误或重定向

**Scenario: 功能权限控制**
- **GIVEN** 用户无权限执行某操作
- **WHEN** 尝试执行该操作
- **THEN** 禁用相关按钮或显示权限不足提示

### ADDED: Base成员管理模块

#### Requirement: 成员CRUD功能
系统应提供完整的Base成员管理功能。

**Scenario: 成员列表**
- **WHEN** 查看Base成员
- **THEN** 显示成员列表，支持分页和筛选

**Scenario: 添加成员**
- **GIVEN** 管理员在成员管理页面
- **WHEN** 添加新成员并设置角色
- **THEN** 成员被添加到Base，收到通知

**Scenario: 编辑成员**
- **GIVEN** 管理员在成员管理页面
- **WHEN** 修改成员角色
- **THEN** 更新成员权限

**Scenario: 移除成员**
- **GIVEN** 管理员在成员管理页面
- **WHEN** 移除成员
- **THEN** 成员失去该Base访问权限

### ADDED: 请求/响应拦截器

#### Requirement: 加载状态管理
系统应在请求期间显示加载状态。

**Scenario: 请求开始**
- **WHEN** 发送API请求
- **THEN** 显示加载指示器

**Scenario: 请求结束**
- **WHEN** 收到响应（成功或失败）
- **THEN** 隐藏加载指示器

#### Requirement: 全局错误提示
系统应统一处理API错误并提示用户。

**Scenario: 网络错误**
- **GIVEN** 网络连接失败
- **WHEN** 发送API请求
- **THEN** 显示网络错误提示

**Scenario: 服务器错误**
- **GIVEN** 服务器返回5xx错误
- **WHEN** 处理响应
- **THEN** 显示服务器错误提示，建议重试

**Scenario: 业务错误**
- **GIVEN** 服务器返回4xx错误
- **WHEN** 处理响应
- **THEN** 根据错误码显示具体错误信息

## 技术方案

### 架构设计

```
前端应用
├── API Client (Axios封装)
├── Auth Module (JWT管理)
├── Services (业务API调用)
├── Stores (Pinia状态管理)
├── Components (Vue组件)
└── Views (页面视图)
```

### API客户端设计

```typescript
// api/client.ts
class ApiClient {
  request(config: AxiosRequestConfig): Promise<ApiResponse>
  get(url: string, params?: object): Promise<ApiResponse>
  post(url: string, data?: object): Promise<ApiResponse>
  put(url: string, data?: object): Promise<ApiResponse>
  delete(url: string): Promise<ApiResponse>
}
```

### 认证流程

```
登录 -> 获取Token -> 存储Token -> 后续请求携带Token
                    |
                    v
            Token过期 -> 自动刷新 -> 刷新失败 -> 重新登录
```

## 影响范围

### 受影响模块
- 前端所有数据操作模块
- 用户认证相关组件
- Base管理模块
- 路由守卫
- 状态管理Store

### 新增模块
- API Client封装
- 认证服务
- 拦截器配置
- 权限指令

## 接口规范

### 基础URL
```
开发环境: http://localhost:5000/api
生产环境: https://api.smarttable.com/api
```

### 认证头
```
Authorization: Bearer <access_token>
```

### 响应格式
```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... },
  "meta": { ... }
}
```
