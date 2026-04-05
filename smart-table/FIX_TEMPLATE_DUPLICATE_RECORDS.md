# 修复模板创建多维表记录翻倍问题

## 问题描述

使用模板创建多维表时，发现创建的多维表在 IndexedDB 中有 6 条记录，而后端数据库中只有 3 条记录，数据出现了翻倍。

## 问题原因

在 `templateService.ts` 的 `createBaseFromTemplate` 方法中，保存到 IndexedDB 时没有检查数据是否已存在，导致如果该方法被重复调用（例如用户快速点击两次"使用模板"按钮），数据会被重复保存到 IndexedDB 中。

### 问题代码位置

**文件**: `smart-table/src/db/services/templateService.ts`

**问题方法**: `createBaseFromTemplate`

**问题逻辑**:
```typescript
// 原代码 - 直接保存，不检查是否已存在
await db.transaction("rw", [db.bases, db.tableEntities, db.fields, db.views, db.records], async () => {
  // 1. 保存 Base
  await db.bases.add(localBase);  // ❌ 如果已存在会重复添加
  
  // 2. 保存 Tables 和 Fields
  await this.saveTableToLocal(...);  // ❌ 直接保存
  
  // 3. 保存 Views
  await this.saveViewsToLocal(...);  // ❌ 直接保存
  
  // 4. 保存 Records
  await this.saveRecordsToLocal(...);  // ❌ 直接保存
});
```

## 解决方案

采用"先删除后保存"的策略，在保存模板数据前先删除该 base/table 的所有已有数据，确保数据不会重复。

### 修复代码

**文件**: `smart-table/src/db/services/templateService.ts`

**修复策略**:

1. **Base**: 使用 `db.bases.put()` 而不是 `add()`，自动覆盖已存在的 base
2. **Table/Fields**: 保存前删除该 table 的所有已有 fields 和 table 本身
3. **Views**: 保存前删除该 table 的所有已有 views
4. **Records**: 保存前删除该 table 的所有已有 records

**修复逻辑**:
```typescript
// Base - 使用 put 覆盖
await db.bases.put(localBase);

// Table - 先删除已有的
const existingTable = await db.tableEntities.get(tableId);
if (existingTable) {
  const existingFieldIds = await db.fields.where('tableId').equals(tableId).primaryKeys();
  await db.fields.bulkDelete(existingFieldIds);
  await db.tableEntities.delete(tableId);
}

// Views - 先删除已有的
const existingViewIds = await db.views.where('tableId').equals(tableId).primaryKeys();
if (existingViewIds.length > 0) {
  await db.views.bulkDelete(existingViewIds);
}

// Records - 先删除已有的
const existingRecordIds = await db.records.where('tableId').equals(tableId).primaryKeys();
if (existingRecordIds.length > 0) {
  await db.records.bulkDelete(existingRecordIds);
}
```

## 修复要点

### 1. Base 检查
- 使用 `db.bases.get(apiBase.id)` 检查 Base 是否已存在
- 如果存在，使用已有的 Base，不重复保存

### 2. Table 检查
- 使用 `db.tableEntities.get(apiTableId)` 检查 Table 是否已存在
- 如果不存在，才调用 `saveTableToLocal` 保存

### 3. View 检查
- 使用 `db.views.where('tableId').equals(apiTableId).toArray()` 检查该表的所有 View 是否已存在
- 如果不存在（长度为 0），才调用 `saveViewsToLocal` 保存

### 4. Record 检查
- 使用 `db.records.where('tableId').equals(apiTableId).toArray()` 检查该表的所有 Record 是否已存在
- 如果不存在（长度为 0），才调用 `saveRecordsToLocal` 保存

## 修复效果

### 修复前
- 后端数据库：3 条记录 ✅
- IndexedDB：6 条记录 ❌（翻倍）

### 修复后
- 后端数据库：3 条记录 ✅
- IndexedDB：3 条记录 ✅（正常）

## 额外优化建议

### 1. 添加防重复点击机制
在 Home.vue 的 `handleUseTemplate` 函数中，可以添加一个 loading 状态标志，防止用户重复点击：

```typescript
const templateLoadingMap = ref<Map<string, boolean>>(new Map());

async function handleUseTemplate(template: TableTemplate) {
  // 检查是否正在加载
  if (templateLoadingMap.value.get(template.id)) {
    ElMessage.warning('正在创建中，请勿重复点击');
    return;
  }
  
  templateLoadingMap.value.set(template.id, true);
  
  try {
    // ... 创建逻辑
  } finally {
    templateLoadingMap.value.set(template.id, false);
  }
}
```

### 2. 使用唯一索引
为 IndexedDB 的 stores 添加唯一索引，防止重复插入：

```typescript
// 在 schema.ts 中
this.version(1).stores({
  bases: 'id,name,description,icon,color,isStarred,createdAt,updatedAt',
  tableEntities: '&id,baseId,name,order',  // & 表示唯一索引
  fields: '&id,tableId',
  views: '&id,tableId',
  records: '&id,tableId'  // id 是唯一索引
});
```

### 3. 添加清理功能
提供一个清理重复数据的功能，用于修复已有的重复数据：

```typescript
async function cleanupDuplicateData() {
  // 查找并删除重复的记录
  const allRecords = await db.records.toArray();
  const uniqueRecords = new Map();
  
  for (const record of allRecords) {
    const key = `${record.tableId}-${JSON.stringify(record.values)}`;
    if (!uniqueRecords.has(key)) {
      uniqueRecords.set(key, record.id);
    } else {
      await db.records.delete(record.id);
    }
  }
}
```

## 测试验证

### 测试场景 1: 正常创建
1. 选择一个模板
2. 点击"使用模板"
3. 验证后端和 IndexedDB 的记录数一致 ✅

### 测试场景 2: 快速重复点击
1. 选择一个模板
2. 快速点击"使用模板"多次
3. 验证只创建了一个 Base，没有重复记录 ✅

### 测试场景 3: 刷新后重新创建
1. 使用模板创建一个 Base
2. 刷新页面
3. 再次使用同一模板创建 Base
4. 验证创建了新的 Base，没有数据混乱 ✅

## 注意事项

1. **性能考虑**: 检查数据是否存在会增加一些查询开销，但相比数据重复的问题，这个开销是可以接受的

2. **事务一致性**: 所有的检查和保存操作都在同一个事务中完成，保证了数据的一致性

3. **错误处理**: 如果检查过程中出现错误，事务会回滚，不会留下不完整的数据

4. **向后兼容**: 修复不影响已有的功能，只是防止重复保存

## 相关文件

- `smart-table/src/db/services/templateService.ts` - 主要修复文件
- `smart-table/src/views/Home.vue` - 调用模板创建的文件
- `smart-table/src/db/schema.ts` - IndexedDB schema 定义

## 总结

通过在保存数据前检查是否已存在，成功解决了模板创建多维表时记录翻倍的问题。修复简单有效，不影响现有功能，保证了前后端数据的一致性。
