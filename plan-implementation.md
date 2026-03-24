# 多维表格功能实现计划

## 项目概述
基于 Vue 3 + TypeScript + Pinia + Dexie (IndexedDB) 的智能表格系统

## 需要实现的功能

### SubTask 2.1.3: 实现多维表格重命名功能
**状态**: 服务端已支持，需要完善 UI

**实现步骤**:
1. 在 Base.vue 的侧边栏表格列表中添加右键菜单
2. 添加重命名对话框或内联编辑功能
3. 调用 tableStore.updateTable() 更新表格名称

**涉及文件**:
- `src/views/Base.vue` - 添加重命名 UI
- `src/stores/tableStore.ts` - 已有 updateTable 方法

---

### SubTask 2.1.4: 实现多维表格删除功能
**状态**: 服务端已支持，需要完善 UI

**实现步骤**:
1. 在 Base.vue 的侧边栏表格列表中添加删除选项
2. 添加确认对话框
3. 调用 tableStore.deleteTable() 删除表格

**涉及文件**:
- `src/views/Base.vue` - 添加删除 UI 和确认对话框
- `src/stores/tableStore.ts` - 已有 deleteTable 方法

---

### SubTask 2.1.5: 实现多维表格收藏功能
**状态**: 需要添加 isStarred 字段到 TableEntity

**实现步骤**:
1. 修改数据库 schema，为 TableEntity 添加 isStarred 字段
2. 更新 tableService，添加 toggleStarTable 方法
3. 更新 tableStore，添加 toggleStarTable action
4. 在 Base.vue 中添加收藏/取消收藏 UI
5. 添加排序功能：收藏的表格排在前面

**涉及文件**:
- `src/db/schema.ts` - 添加 isStarred 字段
- `src/db/services/tableService.ts` - 添加 toggleStarTable 方法
- `src/stores/tableStore.ts` - 添加 toggleStarTable action
- `src/stores/baseStore.ts` - 更新 sortedTables 计算属性
- `src/views/Base.vue` - 添加收藏 UI

---

### SubTask 2.1.6: 实现多维表格搜索功能
**状态**: 需要全新实现

**实现步骤**:
1. 在 Base.vue 侧边栏添加搜索输入框
2. 添加搜索逻辑，根据表格名称过滤
3. 实时显示搜索结果

**涉及文件**:
- `src/views/Base.vue` - 添加搜索输入框和过滤逻辑

---

### SubTask 2.2.6: 实现数据表拖拽排序
**状态**: 服务端已支持，需要完善 UI

**实现步骤**:
1. 在 Base.vue 的侧边栏表格列表中集成 sortablejs
2. 监听拖拽结束事件
3. 调用 tableStore.reorderTables() 更新排序

**涉及文件**:
- `src/views/Base.vue` - 添加拖拽排序功能
- `src/stores/tableStore.ts` - 已有 reorderTables 方法

---

## 数据库变更

### TableEntity 添加 isStarred 字段
```typescript
export interface TableEntity {
  id: string;
  baseId: string;
  name: string;
  description?: string;
  primaryFieldId: string;
  recordCount: number;
  order: number;
  isStarred: boolean;  // 新增字段
  createdAt: number;
  updatedAt: number;
}
```

### 数据库索引更新
```typescript
tableEntities: 'id, baseId, name, order, updatedAt, isStarred'
```

---

## UI 设计

### 侧边栏表格列表改进
1. **搜索框**: 在表格列表顶部添加搜索输入框
2. **右键菜单**: 为每个表格项添加右键菜单（重命名、删除、收藏）
3. **拖拽手柄**: 在表格项左侧添加拖拽手柄
4. **收藏图标**: 在表格项右侧显示收藏状态（星标）

### 确认对话框
- 删除表格前显示确认对话框，提示用户该操作将删除所有相关数据

---

## 实现顺序

1. **SubTask 2.1.3** - 表格重命名（最简单，已有基础）
2. **SubTask 2.1.4** - 表格删除（已有基础）
3. **SubTask 2.2.6** - 拖拽排序（已有基础）
4. **SubTask 2.1.6** - 表格搜索（纯 UI）
5. **SubTask 2.1.5** - 表格收藏（需要数据库变更）
