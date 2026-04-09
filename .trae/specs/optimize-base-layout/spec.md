# 多维表格页面布局优化规格文档

## Why
当前多维表格页面（Base.vue）的布局存在以下问题：
1. 首页点击表格后在当前页面跳转，用户无法同时查看多个表格
2. 左侧导航菜单和顶部导航栏占用过多空间，且与多维表格功能关联不大
3. 搜索框和添加按钮位置不够直观，影响用户操作效率
4. 仪表盘创建入口较深，用户发现和使用成本高

通过优化页面布局，提升多维表格的使用体验和操作效率。

## What Changes
- **新窗口打开表格**：首页点击多维表格时，在新窗口/标签页打开
- **移除左侧导航菜单**：完全移除 AppSidebar 组件在 Base 页面的显示
- **移除顶部导航按钮**：移除"首页"和"设置"按钮
- **顶部显示表格信息**：在顶部导航栏显示当前多维表格名称和描述
- **搜索框位置调整**：将搜索框从侧边栏移至原表格名称位置
- **添加仪表盘按钮**：在"添加数据表"按钮下方新增"添加仪表盘"按钮
- **仪表盘列表集成**：新建的仪表盘显示在左侧数据表列表区域

## Impact
- **Affected specs**: 首页导航、Base页面布局、仪表盘管理
- **Affected code**:
  - `src/views/Home.vue` - 修改表格打开方式
  - `src/views/Base.vue` - 页面布局重构
  - `src/layouts/MainLayout.vue` - 移除Base页面的侧边导航
  - `src/components/common/AppSidebar.vue` - 可能需调整显示逻辑

## ADDED Requirements

### Requirement: 新窗口打开多维表格
**The system SHALL open multidimensional tables in a new window/tab when clicked from the home page.**

#### Scenario: 首页点击表格
- **GIVEN** 用户在首页
- **WHEN** 用户点击某个多维表格
- **THEN** 系统在新浏览器窗口/标签页打开该表格
- **AND** 原首页保持当前状态不变

### Requirement: 添加仪表盘按钮
**The system SHALL provide an "Add Dashboard" button below the "Add Table" button.**

#### Scenario: 显示添加仪表盘按钮
- **GIVEN** 用户在Base页面
- **THEN** 在"+添加数据表"按钮正下方显示"+添加仪表盘"按钮

#### Scenario: 点击添加仪表盘按钮
- **WHEN** 用户点击"添加仪表盘"按钮
- **THEN** 弹出仪表盘创建对话框
- **AND** 创建成功后仪表盘显示在左侧列表中

### Requirement: 仪表盘列表集成
**The system SHALL display dashboards in the same list area as tables.**

#### Scenario: 仪表盘显示在左侧列表
- **GIVEN** 用户已创建仪表盘
- **WHEN** 查看左侧数据表列表区域
- **THEN** 仪表盘与数据表一起显示
- **AND** 仪表盘使用不同图标区分

## MODIFIED Requirements

### Requirement: 移除左侧导航菜单
**The system SHALL remove the left navigation menu from the Base page.**

#### Current Behavior
Base页面左侧显示AppSidebar导航菜单，包含首页、设置等链接。

#### New Behavior
Base页面不再显示左侧导航菜单，侧边栏仅保留数据表/仪表盘列表。

### Requirement: 顶部导航栏调整
**The system SHALL modify the top navigation bar to show table info instead of navigation buttons.**

#### Current Behavior
顶部导航栏显示"首页"和"设置"按钮。

#### New Behavior
- 移除"首页"和"设置"按钮
- 在相同位置显示当前多维表格名称和描述
- 表格名称使用 Tooltip 支持完整名称显示

### Requirement: 搜索框位置调整
**The system SHALL move the search box to the sidebar header area.**

#### Current Behavior
搜索框位于侧边栏表格列表上方。

#### New Behavior
- 在原表格名称位置显示"搜索数据表"搜索框
- 移除现有的侧边栏搜索框组件
- 搜索功能保持不变

### Requirement: 侧边栏头部信息移除
**The system SHALL remove the table name and description from the sidebar header.**

#### Current Behavior
侧边栏头部显示多维表格名称和描述（带Tooltip）。

#### New Behavior
侧边栏头部仅显示搜索框，名称和描述移至顶部导航栏。

## REMOVED Requirements

### Requirement: 首页和设置按钮
**Reason**: 功能已整合到顶部导航栏的表格信息展示中
**Migration**: 用户可通过浏览器返回首页，设置功能后续可通过其他入口访问

## 技术实现要点

### 1. 新窗口打开
使用 `window.open()` 方法在新窗口打开表格：
```typescript
window.open(`/base/${table.id}`, '_blank')
```

### 2. 布局调整
- Base.vue 移除对 AppSidebar 的引用
- 调整 sidebar 样式，移除导航相关样式
- 顶部导航栏使用 flex 布局展示表格信息

### 3. 组件位置变更
- 搜索框组件从 sidebar-search 移至 sidebar-header
- 添加仪表盘按钮添加在 sidebar-footer 的添加数据表按钮下方

### 4. 数据流
- 仪表盘列表与数据表列表合并展示
- 使用不同图标区分数据表和仪表盘
- 点击仪表盘切换到仪表盘视图

## 验收标准
1. 首页点击表格在新窗口打开
2. Base页面不显示左侧导航菜单
3. 顶部导航栏显示表格名称和描述
4. 搜索框位于侧边栏头部
5. "添加仪表盘"按钮显示在"添加数据表"按钮下方
6. 新建的仪表盘显示在左侧列表中
7. 页面布局美观，交互流畅
8. 与现有功能兼容，无回归问题
