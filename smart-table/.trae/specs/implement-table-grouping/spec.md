# 表格视图数据分组功能规格文档

## Why
当前表格视图仅支持平铺展示所有数据记录，当数据量较大时，用户难以快速定位和分析特定类别的数据。通过实现数据分组功能，用户可以按照业务维度（如状态、类型、日期等）对数据进行层级化组织，提升数据浏览效率和分析能力。

## What Changes
- **新增分组配置面板**：在表格视图工具栏添加分组按钮，点击后展开分组配置面板
- **支持多级分组**：允许用户选择多个字段创建层级化的分组结构（最多支持3级）
- **分组展开/折叠**：分组标题可点击展开/折叠，显示/隐藏该分组下的详细数据
- **实时分组更新**：分组字段变更时，表格立即重新渲染分组结果
- **分组状态持久化**：保存用户的分组配置到视图配置中，下次访问时自动恢复
- **响应式设计**：确保分组功能在不同屏幕尺寸下正常显示和操作

## Impact
- **Affected specs**: 表格视图、视图配置、数据展示
- **Affected code**: 
  - `src/views/Base.vue` - 添加分组配置到工具栏
  - `src/components/views/TableView/TableView.vue` - 集成分组展示逻辑
  - `src/components/groups/GroupPanel.vue` - 分组配置面板（已存在，需完善）
  - `src/components/groups/GroupedTableView.vue` - 分组表格视图（已存在，需集成）
  - `src/utils/group.ts` - 分组逻辑工具函数（已存在）
  - `src/db/schema.ts` - ViewEntity 添加 groupBy 配置字段

## ADDED Requirements

### Requirement: 分组配置面板
**The system SHALL provide a group configuration panel that allows users to select grouping fields.**

#### Scenario: 打开分组面板
- **WHEN** 用户点击工具栏的"分组"按钮
- **THEN** 系统显示分组配置面板
- **AND** 面板显示可用的分组字段列表

#### Scenario: 添加分组字段
- **GIVEN** 分组面板已打开
- **WHEN** 用户从下拉菜单选择一个字段
- **THEN** 该字段被添加到分组列表
- **AND** 表格视图立即按该字段分组展示数据

#### Scenario: 移除分组字段
- **GIVEN** 已存在分组字段
- **WHEN** 用户点击字段标签上的删除按钮
- **THEN** 该字段从分组列表移除
- **AND** 表格视图更新分组结果

#### Scenario: 调整分组顺序
- **GIVEN** 已存在多个分组字段
- **WHEN** 用户拖拽调整字段顺序
- **THEN** 分组层级按新顺序重新组织
- **AND** 表格视图更新展示

### Requirement: 多级分组展示
**The system SHALL support multi-level grouping with hierarchical display.**

#### Scenario: 单级分组
- **GIVEN** 用户选择了一个分组字段
- **WHEN** 表格渲染数据
- **THEN** 数据按该字段值分组显示
- **AND** 每个分组显示字段值和记录数

#### Scenario: 多级分组
- **GIVEN** 用户选择了多个分组字段（最多3个）
- **WHEN** 表格渲染数据
- **THEN** 数据按字段顺序逐级分组
- **AND** 形成树形层级结构

#### Scenario: 分组展开/折叠
- **GIVEN** 分组已创建
- **WHEN** 用户点击分组标题
- **THEN** 该分组展开/折叠
- **AND** 显示/隐藏分组下的数据或子分组

### Requirement: 分组状态持久化
**The system SHALL persist grouping configuration to the view settings.**

#### Scenario: 保存分组配置
- **GIVEN** 用户配置了分组字段
- **WHEN** 用户保存视图或离开页面
- **THEN** 分组配置保存到视图配置中

#### Scenario: 恢复分组配置
- **GIVEN** 视图已保存分组配置
- **WHEN** 用户重新进入表格视图
- **THEN** 自动应用之前的分组配置
- **AND** 按配置分组展示数据

### Requirement: 响应式分组展示
**The system SHALL ensure grouping functionality works across different screen sizes.**

#### Scenario: 桌面端显示
- **GIVEN** 屏幕宽度大于1024px
- **WHEN** 显示分组面板
- **THEN** 面板以侧边栏形式显示
- **AND** 表格区域正常展示分组数据

#### Scenario: 移动端显示
- **GIVEN** 屏幕宽度小于768px
- **WHEN** 显示分组面板
- **THEN** 面板以抽屉或弹窗形式显示
- **AND** 表格区域自适应屏幕宽度

## MODIFIED Requirements

### Requirement: 视图配置扩展
**The system SHALL extend view configuration to include grouping settings.**

#### Current Behavior
视图配置仅包含筛选、排序、字段显示等配置。

#### New Behavior
视图配置新增 `groupBy` 字段，存储分组字段ID数组。

```typescript
interface ViewEntity {
  // ... existing fields
  config: {
    filters?: FilterCondition[];
    sorts?: SortConfig[];
    groupBy?: string[];  // 新增
    hiddenFields?: string[];
    // ... other config
  };
}
```

## REMOVED Requirements
无移除的需求。

## 技术实现要点

### 1. 分组算法
使用已有的 `src/utils/group.ts` 中的 `groupRecords` 函数进行数据分组。

### 2. 组件集成
- 在 `TableView.vue` 中根据 `groupBy` 配置决定使用普通表格还是分组表格
- 复用已有的 `GroupPanel.vue` 作为分组配置面板
- 复用已有的 `GroupedTableView.vue` 展示分组数据

### 3. 状态管理
- 在 `viewStore` 中添加分组配置的读写方法
- 分组配置变更时自动保存到视图配置

### 4. 交互设计
- 工具栏添加"分组"按钮，点击展开/收起分组面板
- 分组面板支持拖拽排序
- 分组行支持展开/折叠

## 验收标准
1. 用户可以通过分组面板添加/移除/调整分组字段
2. 表格视图按配置的分组字段层级展示数据
3. 分组标题显示字段值和记录数量
4. 点击分组标题可展开/折叠分组
5. 分组配置保存到视图，下次访问自动恢复
6. 在桌面端和移动端均能正常使用分组功能
