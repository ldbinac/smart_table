# SmartTable 项目运行修复计划

## 问题概述

当前项目存在19个TypeScript编译错误，需要修复后才能正常运行。

## 错误分类

### 1. 未使用的变量/导入 (TS6133) - 10个
- `src/components/views/CalendarView/CalendarView.vue:84` - `months` 未使用
- `src/components/views/KanbanView/KanbanCard.vue:4` - `FieldType` 未使用
- `src/components/views/KanbanView/KanbanView.vue:2` - `watch`, `nextTick` 未使用
- `src/components/views/KanbanView/KanbanView.vue:6` - `Sortable` 未使用
- `src/components/views/KanbanView/KanbanView.vue:21` - `baseStore` 未使用
- `src/components/views/KanbanView/KanbanView.vue:25` - `kanbanRef` 未使用
- `src/utils/formula/engine.ts:68` - `match` 未使用
- `src/utils/formula/functions.ts:29` - `decimals` 未使用
- `src/views/Dashboard.vue:2` - `computed` 未使用
- `src/views/Dashboard.vue:8` - `FieldType` 未使用

### 2. 变量重复声明 (TS2451) - 2个
- `src/utils/export/index.ts:63` 和 `:78` - `data` 变量重复声明

### 3. 类型错误 (TS2345, TS2740, TS2339, TS2304, TS18047) - 7个
- `src/utils/export/index.ts:82` - 类型不匹配
- `src/utils/export/index.ts:118, 124` - `name` 属性不存在
- `src/utils/formula/engine.ts:115` - 类型不匹配
- `src/utils/formula/functions.ts:31` - `decals` 变量名拼写错误
- `src/views/Dashboard.vue:367` - 可能为null

## 修复步骤

### 步骤1: 修复未使用的导入和变量
删除或注释掉所有未使用的导入和变量声明。

### 步骤2: 修复变量重复声明
重命名重复声明的变量，使用不同的变量名。

### 步骤3: 修复类型错误
- 添加类型断言或类型守卫
- 修正变量名拼写错误
- 添加null检查

### 步骤4: 验证构建
运行 `npm run build` 确认所有错误已修复。

### 步骤5: 启动开发服务器
运行 `npm run dev` 启动项目。

## 预期结果
- 项目构建成功，无TypeScript错误
- 开发服务器正常启动
- 应用可在浏览器中访问
