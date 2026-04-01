# 字段必填校验功能实施计划

## 一、需求概述

在字段管理功能模块中，针对已配置为必填项的字段，需在所有视图的数据弹窗和数据表格的录入场景中实施严格的必填校验机制。

## 二、现状分析

### 2.1 字段必填配置
- 字段实体 `FieldEntity` 已包含 `isRequired: boolean` 属性
- 字段配置存储在 `options` 中也可设置 `required: boolean`

### 2.2 现有验证工具
- `src/utils/validation.ts` 已存在 `DataValidator` 类
- 支持 required、unique、format、custom 等验证规则
- 但当前实现依赖 `options.validation` 数组，未直接使用 `field.isRequired`

### 2.3 数据录入场景
1. **数据弹窗录入**
   - `RecordDialog.vue` - 编辑记录弹窗
   - `AddRecordDialog.vue` - 添加记录弹窗
   - 使用 Element Plus 的 `ElForm` 组件
   - 已显示 `:required` 标记，但无实际校验逻辑

2. **数据表格行内编辑**
   - `TableView/TableCell.vue` - 单元格编辑
   - `TableView/TableView.vue` - 表格视图
   - 行内编辑后直接触发保存，无校验拦截

## 三、设计方案

### 3.1 校验规则

#### 必填字段判定
```typescript
function isFieldRequired(field: FieldEntity): boolean {
  // 优先使用 field.isRequired，其次检查 options.required
  return field.isRequired === true || field.options?.required === true;
}
```

#### 空值判定
```typescript
function isValueEmpty(value: CellValue): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string" && value.trim() === "") return true;
  if (Array.isArray(value) && value.length === 0) return true;
  return false;
}
```

### 3.2 校验函数设计

在 `src/utils/validation.ts` 中新增：

```typescript
export interface RequiredValidationResult {
  valid: boolean;
  errors: Array<{
    fieldId: string;
    fieldName: string;
    message: string;
  }>;
}

/**
 * 验证必填字段
 * @param fields 字段列表
 * @param values 字段值
 * @returns 验证结果
 */
export function validateRequiredFields(
  fields: FieldEntity[],
  values: Record<string, CellValue>,
): RequiredValidationResult;

/**
 * 检查单个字段是否为空
 */
export function checkFieldEmpty(field: FieldEntity, value: CellValue): boolean;
```

### 3.3 错误提示规范
- 格式：`请填写必填字段：[字段名称]`
- 多字段未填写时：`请填写以下必填字段：字段A、字段B、字段C`

## 四、实施步骤

### 步骤1：完善验证工具函数

**文件**: `src/utils/validation.ts`

**修改内容**:
1. 新增 `validateRequiredFields` 函数
2. 新增 `isFieldRequired` 辅助函数
3. 新增 `isValueEmpty` 辅助函数
4. 更新 `DataValidator.isRequired` 方法以支持 `field.isRequired`

### 步骤2：数据弹窗必填校验

#### 2.1 RecordDialog.vue（编辑记录）

**修改内容**:
1. 导入验证函数
2. 在 `handleSave` 中添加校验逻辑
3. 显示错误提示

```typescript
const handleSave = async () => {
  // 1. 验证必填字段
  const validation = validateRequiredFields(
    visibleFields.value,
    formData.value as Record<string, CellValue>
  );
  
  if (!validation.valid) {
    const fieldNames = validation.errors.map(e => e.fieldName).join('、');
    ElMessage.error(`请填写必填字段：${fieldNames}`);
    return;
  }
  
  // 2. 保存记录
  // ...
};
```

#### 2.2 AddRecordDialog.vue（添加记录）

**修改内容**:
1. 导入验证函数
2. 在 `handleSave` 中添加校验逻辑
3. 显示错误提示

### 步骤3：表格行内编辑必填校验

#### 3.1 TableCell.vue

**修改内容**:
1. 接收 `required` 属性
2. 在 `finishEdit` 中检查必填字段
3. 如果为空值，阻止保存并显示提示

```typescript
const finishEdit = () => {
  if (!isEditing.value) return;
  
  // 检查必填字段
  if (props.field.isRequired && isValueEmpty(editValue.value)) {
    ElMessage.error(`请填写必填字段：${props.field.name}`);
    cancelEdit();
    return;
  }
  
  // 保存编辑
  // ...
};
```

#### 3.2 TableView.vue

**修改内容**:
1. 在 `handleCellUpdate` 中添加校验
2. 如果校验失败，阻止更新

```typescript
const handleCellUpdate = async (
  record: RecordEntity,
  fieldId: string,
  value: CellValue,
) => {
  const field = fields.value.find(f => f.id === fieldId);
  
  // 检查必填字段
  if (field?.isRequired && isValueEmpty(value)) {
    ElMessage.error(`请填写必填字段：${field.name}`);
    return;
  }
  
  // 更新记录
  // ...
};
```

### 步骤4：表单视图校验

#### 4.1 FormView.vue

**文件**: `src/components/views/FormView/FormView.vue`

**修改内容**:
1. 导入验证函数
2. 在提交表单时添加校验逻辑
3. 显示错误提示

### 步骤5：其他视图校验

检查并更新以下视图组件：
- `CalendarView.vue` - 日历视图
- `KanbanView.vue` - 看板视图
- `GanttView.vue` - 甘特图视图
- `GalleryView.vue` - 画廊视图

## 五、实施优先级

### 高优先级（核心功能）
1. ✅ 完善 `validation.ts` 验证工具
2. ✅ `RecordDialog.vue` 编辑记录弹窗校验
3. ✅ `AddRecordDialog.vue` 添加记录弹窗校验
4. ✅ `TableCell.vue` 表格行内编辑校验

### 中优先级（扩展功能）
5. `FormView.vue` 表单视图校验
6. `TableView.vue` 表格视图批量校验

### 低优先级（其他视图）
7. 日历、看板、甘特图、画廊等视图校验

## 六、错误提示样式

使用 Element Plus 的 `ElMessage` 组件显示错误：

```typescript
// 单个字段未填写
ElMessage.error("请填写必填字段：客户名称");

// 多个字段未填写
ElMessage.error("请填写以下必填字段：客户名称、联系电话、邮箱地址");
```

## 七、测试验证点

1. **弹窗编辑场景**
   - [ ] 编辑记录时，必填字段为空阻止保存
   - [ ] 添加记录时，必填字段为空阻止保存
   - [ ] 错误提示显示正确的字段名称
   - [ ] 填写完整后可以正常保存

2. **行内编辑场景**
   - [ ] 表格单元格编辑时，必填字段清空阻止保存
   - [ ] 错误提示显示正确的字段名称
   - [ ] 填写完整后可以正常保存

3. **表单视图场景**
   - [ ] 表单提交时，必填字段为空阻止提交
   - [ ] 错误提示显示正确的字段名称

4. **边界情况**
   - [ ] 字符串仅包含空格视为空
   - [ ] 空数组视为空
   - [ ] null/undefined 视为空
   - [ ] 0 和 false 不视为空

## 八、注意事项

1. **保持向后兼容** - 不影响现有非必填字段的功能
2. **错误提示友好** - 明确告知用户哪些字段需要填写
3. **校验时机恰当** - 在保存/提交前进行校验，避免过早提示
4. **性能考虑** - 校验逻辑轻量，不影响用户体验
