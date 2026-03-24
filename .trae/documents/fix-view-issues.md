# 视图功能问题修复计划

## 问题概述

用户报告了三个关键问题需要解决：
1. 日历视图下，无法在日期中正常显示数据内容
2. 看板视图下，点击对应分组中的"添加记录"按钮时没有任何响应
3. 创建的视图未能保存，刷新页面后已创建的视图消失

## 问题分析与修复方案

### 问题1: 日历视图无法显示数据内容

**根本原因分析**:
- CalendarView.vue 组件只接收 `fields` 和 `records` 作为 props
- 但 Base.vue 中传递的是 `:table-id`、`:view-id`、`:records`、`:fields`
- CalendarView 组件没有正确接收 `tableId` 和 `viewId` props
- 事件处理也没有正确传递，导致无法添加记录

**修复方案**:
1. 修改 CalendarView.vue 组件，添加 `tableId` 和 `viewId` props
2. 确保事件处理正确传递
3. 检查日期字段解析逻辑，确保能正确识别日期值

### 问题2: 看板视图"添加记录"按钮无响应

**根本原因分析**:
- KanbanView.vue 中 `handleAddRecord` 函数正确 emit 了 `addRecord` 事件
- 但 Base.vue 中没有监听 `addRecord` 事件
- Base.vue 中只监听了 `@record-select` 事件

**修复方案**:
1. 在 Base.vue 中添加对 `addRecord` 事件的监听
2. 实现 `handleAddRecord` 函数来创建新记录
3. 确保看板视图的分组字段值正确传递给新记录

### 问题3: 视图创建后未保存，刷新后消失

**根本原因分析**:
- viewStore 中有 `createView` 方法，会调用 `viewService.createView`
- 但 Base.vue 中没有实现创建视图的功能
- ViewSwitcher 组件可能有创建视图的UI，但没有正确调用 viewStore
- 需要检查 viewService 是否正确持久化到 IndexedDB

**修复方案**:
1. 检查 ViewSwitcher 组件，确保创建视图时调用 viewStore.createView
2. 在 Base.vue 中添加创建视图的功能
3. 确保视图数据正确保存到 IndexedDB
4. 页面加载时正确加载视图列表

## 修复步骤

### 步骤1: 修复日历视图

**文件**: `src/components/views/CalendarView/CalendarView.vue`

修改内容:
1. 添加 `tableId` 和 `viewId` props
2. 确保 `addRecord` 事件正确 emit
3. 检查日期字段值解析逻辑

### 步骤2: 修复看板视图添加记录

**文件**: `src/views/Base.vue`

修改内容:
1. 添加 `handleAddRecord` 函数
2. 在 KanbanView 组件上监听 `@addRecord` 事件
3. 调用 recordService 创建新记录

### 步骤3: 修复视图保存功能

**文件**: `src/views/Base.vue` 和 `src/components/views/ViewSwitcher.vue`

修改内容:
1. 在 ViewSwitcher 中添加创建视图的UI和逻辑
2. 调用 viewStore.createView 保存视图
3. 确保页面加载时调用 viewStore.loadViews

### 步骤4: 全面测试

测试内容:
1. 日历视图能正确显示记录
2. 点击日期能添加记录
3. 看板视图能添加记录到对应分组
4. 创建视图后刷新页面，视图仍然存在
5. 视图切换正常

## 依赖文件

- `src/views/Base.vue` - 主页面，需要添加事件处理
- `src/components/views/CalendarView/CalendarView.vue` - 日历视图组件
- `src/components/views/KanbanView/KanbanView.vue` - 看板视图组件
- `src/components/views/ViewSwitcher.vue` - 视图切换组件
- `src/stores/viewStore.ts` - 视图状态管理
- `src/db/services/viewService.ts` - 视图服务

## 预计工作量

- 步骤1（修复日历视图）: 20分钟
- 步骤2（修复看板视图添加记录）: 20分钟
- 步骤3（修复视图保存）: 30分钟
- 步骤4（全面测试）: 15分钟

总计约 1.5 小时
