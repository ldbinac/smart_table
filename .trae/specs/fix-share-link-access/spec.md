# 修复分享链接访问权限异常问题规格说明

## Why

当前系统通过分享链接访问多维表格时存在权限异常问题。用户通过分享链接（如 http://localhost:3000/#/share/ad2e5c00-956b-4af3-bd59-34d5452f6d79）成功打开分享页面后，点击"进入多维表格"按钮跳转到 Base 页面时，接口 `/api/bases/{base_id}` 返回 403 状态码。这是因为后端没有正确处理分享令牌（share_token），导致即使用户通过有效分享链接访问，也无法获得 Base 的访问权限。

## What Changes

### 后端 API 变更

- **修改 `GET /bases/{base_id}` 接口**：增加对 `share_token` 查询参数或请求头的支持，当用户不是 Base 成员时，验证 share_token 的有效性，如果有效则自动添加用户为 Base 成员并返回 Base 信息

### 前端 Store 变更

- **修改 `baseStore.fetchBase` 方法**：增加可选的 `shareToken` 参数，在请求 Base 详情时将 share_token 传递给后端

### 前端 API Service 变更

- **修改 `baseApiService.getBase` 方法**：支持传递 `shareToken` 参数

## Impact

### 受影响的后端文件

- `smarttable-backend/app/routes/bases.py` - 修改 `get_base` 路由，增加 share_token 验证逻辑
- `smarttable-backend/app/services/base_service.py` - 可能需要添加通过分享令牌验证权限的方法

### 受影响的前端文件

- `smart-table/src/stores/baseStore.ts` - 修改 `fetchBase` 方法签名和实现
- `smart-table/src/services/api/baseApiService.ts` - 修改 `getBase` 方法签名和实现

## ADDED Requirements

### Requirement: 分享令牌传递机制

系统 SHALL 支持通过分享令牌访问 Base 详情接口。

#### Scenario: 通过分享令牌访问 Base
- **WHEN** 用户通过分享链接进入 Base 页面
- **AND** 前端从 localStorage 获取到 share_token
- **THEN** 前端 SHALL 在请求 Base 详情时将 share_token 传递给后端
- **AND** 后端 SHALL 验证 share_token 的有效性
- **AND** 如果 share_token 有效，后端 SHALL 自动将当前用户添加为 Base 成员
- **AND** 后端 SHALL 返回 Base 详情信息

### Requirement: 后端权限验证增强

系统 SHALL 在检查 Base 访问权限时，支持通过分享令牌验证。

#### Scenario: 非成员用户通过分享链接访问
- **GIVEN** 用户不是 Base 的成员
- **AND** 用户提供了有效的 share_token
- **WHEN** 用户请求 Base 详情
- **THEN** 系统 SHALL 验证 share_token 的有效性
- **AND** 如果有效，自动创建 BaseMember 记录，角色为 viewer 或 editor（根据分享权限）
- **AND** 返回 Base 详情

#### Scenario: 无效分享令牌
- **GIVEN** 用户提供了无效的 share_token
- **WHEN** 用户请求 Base 详情
- **THEN** 系统 SHALL 返回 403 权限错误

## MODIFIED Requirements

### Requirement: Base 详情接口

**原需求**: `GET /bases/{base_id}` 仅支持成员访问

**修改后**: `GET /bases/{base_id}` 支持通过 `share_token` 查询参数或请求头访问

- 优先检查用户是否是成员
- 如果不是成员，检查是否提供了有效的 share_token
- 如果 share_token 有效，自动添加用户为成员并返回数据
- 如果都无效，返回 403 错误

## REMOVED Requirements

无
