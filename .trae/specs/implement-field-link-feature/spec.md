# 字段关联功能规格文档

## Why

多维表用户需要建立数据表之间的关联关系，以便更好地组织和管理数据。例如：
- 客户表与订单表的一对多关联
- 员工表与部门表的多对一关联
- 项目表与任务表的一对多关联

通过实现字段关联功能，用户可以：
- 建立表与表之间的数据关系
- 快速查看关联数据
- 通过关联字段进行数据筛选和分组

## What Changes

### 前端变更
1. **新增关联字段配置界面** - 创建/编辑关联字段时的配置选项
2. **新增关联字段显示组件** - 在表格、看板等视图中显示关联数据
3. **新增关联选择器组件** - 用于选择关联记录
4. **修改字段类型定义** - 完善 Link 字段类型配置选项
5. **新增关联关系服务** - 处理关联数据的 CRUD 操作
6. **各视图集成关联字段** - TableView、GroupedTableView、KanbanView、RecordDetailDrawer、CalendarView

### 后端变更
1. **新增关联关系模型** - 存储表与表之间的关联关系
2. **修改记录服务** - 支持关联字段的数据处理
3. **新增关联字段 API** - 提供关联数据的查询和更新接口
4. **数据迁移脚本** - 为现有数据建立关联关系支持

### 数据库变更
1. **新增 link_relations 表** - 存储关联关系定义
2. **新增 link_values 表** - 存储关联字段的值

**BREAKING**: 关联字段的数据存储格式将改变，需要数据迁移

## Impact

- 受影响的前端文件：
  - `smart-table/src/types/fields.ts` - 字段类型定义
  - `smart-table/src/components/fields/` - 新增 LinkField 组件
  - `smart-table/src/components/dialogs/FieldDialog.vue` - 字段配置对话框
  - `smart-table/src/services/api/` - 新增 linkApiService.ts
  - `smart-table/src/components/views/TableView/` - 表格视图关联字段集成
  - `smart-table/src/components/groups/GroupedTableView.vue` - 分组表格视图关联字段集成
  - `smart-table/src/components/views/KanbanView/` - 看板视图关联字段集成
  - `smart-table/src/components/dialogs/RecordDetailDrawer.vue` - 记录详情关联字段集成
  - `smart-table/src/components/views/CalendarView/` - 日历视图关联字段集成

- 受影响的后端文件：
  - `smarttable-backend/app/models/` - 新增 link_relation.py
  - `smarttable-backend/app/services/record_service.py` - 记录服务
  - `smarttable-backend/app/routes/fields.py` - 字段路由
  - `smarttable-backend/app/routes/records.py` - 记录路由

## ADDED Requirements

### Requirement: 关联字段创建与配置

系统应支持创建和配置关联字段。

#### Scenario: 创建一对一关联字段
- **GIVEN** 用户正在创建新字段
- **WHEN** 选择字段类型为"关联"
- **AND** 选择关联类型为"一对一"
- **AND** 选择目标数据表
- **AND** 选择显示字段
- **THEN** 成功创建一对一关联字段
- **AND** 自动生成反向关联字段（可选）

#### Scenario: 创建一对多关联字段
- **GIVEN** 用户正在创建新字段
- **WHEN** 选择字段类型为"关联"
- **AND** 选择关联类型为"一对多"
- **AND** 选择目标数据表
- **AND** 选择显示字段
- **THEN** 成功创建一对多关联字段
- **AND** 在目标表中自动生成反向关联字段（可选）

#### Scenario: 创建多对一关联字段
- **GIVEN** 用户正在创建新字段
- **WHEN** 选择字段类型为"关联"
- **AND** 选择关联类型为"多对一"
- **AND** 选择目标数据表
- **AND** 选择显示字段
- **THEN** 成功创建多对一关联字段
- **AND** 多条记录可以关联到同一条目标记录

#### Scenario: 配置双向关联
- **GIVEN** 用户正在配置关联字段
- **WHEN** 启用"双向关联"选项
- **THEN** 系统自动在目标表中创建对应的反向关联字段
- **AND** 保持两个字段的数据同步

### Requirement: 关联数据显示与编辑

系统应支持在视图中显示和编辑关联数据。

#### Scenario: 在表格视图中显示关联数据
- **GIVEN** 表格中存在关联字段
- **WHEN** 用户查看表格视图
- **THEN** 关联字段显示关联记录的目标字段值
- **AND** 多个关联值以逗号分隔显示
- **AND** 支持点击关联标签跳转

#### Scenario: 在分组表格视图中显示关联数据
- **GIVEN** 分组表格中存在关联字段
- **WHEN** 用户查看分组表格视图
- **THEN** 关联字段正确显示关联记录
- **AND** 支持在分组行中编辑关联字段
- **AND** 关联数据随分组展开/折叠保持同步

#### Scenario: 在看板视图中显示关联数据
- **GIVEN** 看板卡片中存在关联字段
- **WHEN** 用户查看看板视图
- **THEN** 关联字段在卡片上正确显示
- **AND** 支持点击关联标签跳转
- **AND** 关联数据随卡片移动保持同步

#### Scenario: 在记录详情中显示和编辑关联数据
- **GIVEN** 记录详情中存在关联字段
- **WHEN** 用户查看记录详情
- **THEN** 关联字段正确显示关联记录
- **AND** 支持在详情中编辑关联字段
- **AND** 支持打开关联选择器选择记录

#### Scenario: 在日历视图中显示关联数据
- **GIVEN** 日历视图中存在关联字段
- **WHEN** 用户查看日历视图
- **THEN** 关联字段在事件卡片上正确显示
- **AND** 支持点击关联标签跳转

#### Scenario: 编辑关联字段值
- **GIVEN** 用户正在编辑记录
- **WHEN** 点击关联字段单元格
- **THEN** 弹出关联记录选择器
- **AND** 显示目标表中的可选记录列表
- **AND** 支持搜索和筛选目标记录

#### Scenario: 批量编辑关联字段
- **GIVEN** 用户选择了多条记录
- **WHEN** 批量编辑关联字段
- **THEN** 支持添加关联、移除关联、替换关联三种操作

### Requirement: 各视图关联字段集成

#### Scenario: GroupedTableView 关联字段集成
- **GIVEN** GroupedTableView 组件已存在
- **WHEN** 集成 LinkField 组件
- **THEN** 分组表格行中正确显示关联字段
- **AND** 支持点击关联标签跳转
- **AND** 支持在分组行中编辑关联字段
- **AND** 关联数据随分组展开/折叠保持同步

#### Scenario: KanbanView 关联字段集成
- **GIVEN** KanbanView 组件已存在
- **WHEN** 在看板卡片中集成 LinkField 组件
- **THEN** 看板卡片正确显示关联字段
- **AND** 支持点击关联标签跳转
- **AND** 关联数据随卡片移动保持同步

#### Scenario: RecordDetailDrawer 关联字段集成
- **GIVEN** RecordDetailDrawer 组件已存在
- **WHEN** 在详情表单中集成 LinkField 组件
- **THEN** 记录详情正确显示关联字段
- **AND** 支持在详情中编辑关联字段
- **AND** 支持打开关联选择器选择记录

#### Scenario: CalendarView 关联字段集成
- **GIVEN** CalendarView 组件已存在
- **WHEN** 在日历事件卡片中集成 LinkField 组件
- **THEN** 日历事件卡片正确显示关联字段
- **AND** 支持点击关联标签跳转

### Requirement: 关联关系维护

系统应自动维护关联关系的数据一致性。

#### Scenario: 删除关联记录
- **GIVEN** 记录 A 关联了记录 B
- **WHEN** 删除记录 B
- **THEN** 自动移除记录 A 中对记录 B 的关联引用
- **AND** 触发关联变更事件

#### Scenario: 更新关联记录
- **GIVEN** 记录 A 关联了记录 B
- **WHEN** 修改记录 B 的显示字段值
- **THEN** 自动更新记录 A 中关联字段的显示值

### Requirement: 关联数据加载性能

系统应优化关联数据的加载性能。

#### Scenario: 懒加载关联数据
- **GIVEN** 表格包含多个关联字段
- **WHEN** 加载表格数据
- **THEN** 关联字段仅加载显示所需的最小数据
- **AND** 关联详情数据按需懒加载

#### Scenario: 关联数据缓存
- **GIVEN** 用户多次查看同一关联数据
- **WHEN** 关联数据未发生变化
- **THEN** 从缓存中读取关联数据
- **AND** 避免重复的数据库查询

## MODIFIED Requirements

### Requirement: 字段类型定义

**原需求**: 关联字段类型已定义但功能不完整

**修改后**: 
- 完善 Link 字段的配置选项
- 支持 relationshipType: "oneToOne" | "oneToMany" | "manyToOne"
- 支持 linkedTableId、displayFieldId、bidirectional 等配置

### Requirement: 记录数据存储

**原需求**: 关联字段值存储为简单数组

**修改后**:
- 关联字段值存储为关联记录 ID 数组
- 支持通过关联关系表查询完整关联数据
- 保持与现有数据格式的向后兼容

### Requirement: 视图集成

**原需求**: 仅在 TableView 中支持关联字段

**修改后**:
- 在 GroupedTableView 中支持关联字段显示和编辑
- 在 KanbanView 中支持关联字段显示
- 在 RecordDetailDrawer 中支持关联字段显示和编辑
- 在 CalendarView 中支持关联字段显示

## REMOVED Requirements

### Requirement: 多对多关联

**原因**: 当前版本优先实现一对一、一对多和多对一关联，多对多关联复杂度较高，计划在后续版本实现

**迁移**: 用户可通过两个一对多关联字段间接实现多对多关系
