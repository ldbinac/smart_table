# 数据变更历史记录与查看功能规格说明

## Why

当前系统缺少数据变更历史追踪功能，用户无法查看记录的历史修改情况。这在协作场景下尤为重要，用户需要了解谁修改了数据、何时修改、修改了什么内容。实现变更历史记录功能可以提高数据透明度，便于审计和问题追溯。

## What Changes

### 后端变更

- **新增数据变更历史模型**：创建 `RecordHistory` 模型存储变更记录
- **新增变更历史 API 接口**：
  - `GET /api/records/{record_id}/history` - 获取指定记录的变更历史列表
  - 支持分页查询
- **修改记录保存逻辑**：在创建、更新、删除记录时自动记录变更历史

### 前端变更

- **新增变更历史查看组件**：`RecordHistoryDrawer` 抽屉组件展示变更历史
- **修改 RecordDetailDrawer**：添加"变更历史"页签或按钮，点击打开历史查看界面
- **新增变更历史 API 服务**：`recordHistoryApiService` 调用后端接口

## Impact

### 受影响的后端文件

- `smarttable-backend/app/models/` - 新增 `record_history.py` 模型文件
- `smarttable-backend/app/services/record_service.py` - 修改保存逻辑，添加历史记录
- `smarttable-backend/app/routes/records.py` - 新增获取历史记录接口

### 受影响的前端文件

- `smart-table/src/components/dialogs/RecordDetailDrawer.vue` - 添加历史查看入口
- `smart-table/src/components/dialogs/RecordHistoryDrawer.vue` - 新增历史查看组件
- `smart-table/src/services/api/` - 新增 `recordHistoryApiService.ts`

## ADDED Requirements

### Requirement: 数据变更历史记录存储

系统 SHALL 自动记录所有数据变更操作的历史。

#### Scenario: 创建记录时记录历史
- **WHEN** 用户创建新记录
- **THEN** 系统 SHALL 创建一条变更历史记录
- **AND** 记录类型为 "CREATE"
- **AND** 记录变更人、变更时间、新值快照

#### Scenario: 更新记录时记录历史
- **WHEN** 用户更新记录字段
- **THEN** 系统 SHALL 创建一条变更历史记录
- **AND** 记录类型为 "UPDATE"
- **AND** 记录变更字段、变更前值、变更后值
- **AND** 记录变更人、变更时间

#### Scenario: 删除记录时记录历史
- **WHEN** 用户删除记录
- **THEN** 系统 SHALL 创建一条变更历史记录
- **AND** 记录类型为 "DELETE"
- **AND** 记录删除前的完整数据快照
- **AND** 记录变更人、变更时间

### Requirement: 变更历史查询接口

系统 SHALL 提供查询变更历史的 API 接口。

#### Scenario: 分页查询变更历史
- **GIVEN** 一条记录有多条变更历史
- **WHEN** 调用 `GET /api/records/{record_id}/history?page=1&size=20`
- **THEN** 返回该记录的变更历史列表
- **AND** 按时间倒序排列（最新的在前）
- **AND** 支持分页参数

#### Scenario: 变更历史数据结构
- **WHEN** 获取变更历史列表
- **THEN** 每条历史记录包含：
  - `id`: 历史记录ID
  - `record_id`: 关联记录ID
  - `action`: 操作类型（CREATE/UPDATE/DELETE）
  - `changed_by`: 变更人信息（用户ID、姓名、头像）
  - `changed_at`: 变更时间（精确到秒）
  - `changes`: 变更详情（字段名、旧值、新值）
  - `snapshot`: 数据快照（完整记录数据）

### Requirement: 变更历史查看界面

系统 SHALL 在数据详情页面提供变更历史查看功能。

#### Scenario: 打开变更历史
- **GIVEN** 用户在查看记录详情
- **WHEN** 点击"变更历史"按钮或页签
- **THEN** 打开变更历史查看界面
- **AND** 显示该记录的所有变更历史

#### Scenario: 变更历史展示
- **GIVEN** 变更历史查看界面已打开
- **THEN** 界面 SHALL 显示：
  - 变更人头像和姓名
  - 变更时间（精确到秒）
  - 操作类型（创建/更新/删除）
  - 变更字段对比（旧值 → 新值）
  - 按时间倒序排列

#### Scenario: 分页展示
- **GIVEN** 变更历史记录较多（超过20条）
- **THEN** 界面 SHALL 分页展示
- **AND** 支持翻页操作

## MODIFIED Requirements

无

## REMOVED Requirements

无
