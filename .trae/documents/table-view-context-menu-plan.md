# 表格视图列头右键菜单功能优化计划

## 概述

本计划旨在优化表格视图的列头右键菜单功能，实现以下三个核心功能：
1. **冻结列功能** - 允许用户通过右键菜单选择冻结指定列
2. **隐藏字段功能** - 支持用户通过右键菜单选择隐藏特定字段列
3. **编辑字段属性功能** - 提供字段属性编辑界面，允许用户修改字段相关属性

## 现状分析

### 已有功能基础

根据代码分析，当前系统已具备以下基础：

1. **右键菜单框架** (`ContextMenu.vue`)
   - 已支持自定义菜单项
   - 支持图标、分隔线、禁用状态、危险操作样式
   - 已实现点击外部关闭、ESC键关闭等交互

2. **表格视图** (`TableView.vue`)
   - 已实现列头右键事件监听 (`handleHeaderContextMenu`)
   - 已实现冻结列功能逻辑 (`freeze`/`unfreeze`)
   - 已实现隐藏字段功能逻辑 (`hide-field`)
   - 已集成视图状态管理 (`viewStore`)

3. **视图状态管理** (`viewStore.ts`)
   - 已提供 `updateFrozenFields` 方法更新冻结列
   - 已提供 `updateHiddenFields` 方法更新隐藏字段
   - 视图数据包含 `frozenFields` 和 `hiddenFields` 数组

4. **字段管理对话框** (`FieldDialog.vue`)
   - 已实现完整的字段属性编辑功能
   - 支持字段创建、编辑、删除、排序
   - 支持字段可见性切换 (`toggleFieldVisibility`)
   - 支持各种字段类型的配置（文本、数字、日期、选项、公式、附件等）

5. **字段服务** (`fieldService.ts`)
   - 已提供 `updateField` 方法更新字段属性
   - 已提供 `updateFieldVisibility` 方法切换字段可见性

### 当前右键菜单项

在 `TableView.vue` 中，列头右键菜单当前包含：
- 升序排列 / 降序排列
- 冻结列 / 取消冻结
- 隐藏字段
- 编辑字段属性

## 功能实现细节

### 1. 冻结列功能

#### 当前实现状态
- ✅ 右键菜单已显示"冻结列"/"取消冻结"选项
- ✅ 点击事件已处理 (`handleContextMenuSelect` 中的 `freeze`/`unfreeze` case)
- ✅ 视图状态更新逻辑已实现
- ✅ 冻结列视觉样式已实现 (`is-frozen` 类)

#### 需要优化的地方
- 冻结列的视觉效果需要增强，添加冻结指示器
- 多列冻结时的位置计算需要确保正确

### 2. 隐藏字段功能

#### 当前实现状态
- ✅ 右键菜单已显示"隐藏字段"选项
- ✅ 点击事件已处理 (`hide-field` case)
- ✅ 视图级隐藏逻辑已实现 (`updateHiddenFields`)

#### 需要优化的地方
- 当前实现是视图级隐藏（存储在 view.hiddenFields 中）
- 需要与"字段管理"中的全局隐藏（field.isVisible）保持一致性
- 建议统一使用视图级隐藏，更符合用户预期

### 3. 编辑字段属性功能

#### 当前实现状态
- ✅ 右键菜单已显示"编辑字段属性"选项
- ✅ `FieldDialog.vue` 已实现完整的字段编辑功能

#### 需要实现的功能
- 点击"编辑字段属性"后打开 `FieldDialog`
- 传递当前字段数据到对话框
- 编辑完成后刷新表格视图

## 实现步骤

### 步骤1: 完善编辑字段属性功能

**目标**: 实现从右键菜单打开字段编辑对话框

**修改文件**: `TableView.vue`

**具体修改**:

1. 添加字段编辑对话框的引用和状态
```typescript
// 添加导入
import FieldDialog from "@/components/dialogs/FieldDialog.vue";

// 添加状态
const fieldDialogVisible = ref(false);
const editingField = ref<FieldEntity | null>(null);
```

2. 修改 `handleContextMenuSelect` 方法，添加 `edit-field` case
```typescript
case "edit-field":
  if (contextMenuField.value) {
    editingField.value = contextMenuField.value;
    fieldDialogVisible.value = true;
  }
  break;
```

3. 在模板中添加 `FieldDialog` 组件
```vue
<FieldDialog
  v-model:visible="fieldDialogVisible"
  :table-id="baseStore.currentTable?.id || ''"
  :fields="fields"
  @field-updated="handleFieldUpdated"
/>
```

4. 添加字段更新后的处理函数
```typescript
const handleFieldUpdated = async (updatedField: FieldEntity) => {
  // 刷新字段列表
  if (baseStore.currentTable) {
    await baseStore.loadTable(baseStore.currentTable.id);
  }
  ElMessage.success("字段更新成功");
};
```

### 步骤2: 优化 FieldDialog 以支持直接编辑指定字段

**目标**: 允许 `FieldDialog` 直接打开到指定字段的编辑界面

**修改文件**: `FieldDialog.vue`

**具体修改**:

1. 添加新的 prop 用于指定要编辑的字段
```typescript
const props = defineProps<{
  visible: boolean;
  tableId: string;
  fields: FieldEntity[];
  editFieldId?: string; // 新增：指定要编辑的字段ID
}>();
```

2. 监听 `visible` 变化时，如果指定了 `editFieldId`，自动切换到编辑模式
```typescript
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      if (props.editFieldId) {
        const field = props.fields.find(f => f.id === props.editFieldId);
        if (field) {
          openEditField(field);
          return;
        }
      }
      activeTab.value = "list";
      nextTick(() => {
        initSortable();
      });
    } else {
      destroySortable();
    }
  },
);
```

### 步骤3: 优化冻结列的视觉效果

**目标**: 增强冻结列的视觉指示

**修改文件**: `TableHeader.vue`, `TableView.vue`

**具体修改**:

1. 在 `TableHeader.vue` 中优化冻结指示器样式
```scss
.frozen-indicator {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  color: $primary-color;
  display: flex;
  align-items: center;
  gap: 2px;
  
  &::after {
    content: "已冻结";
    font-size: 10px;
    font-weight: 500;
  }
}
```

2. 在 `TableView.vue` 中确保冻结列的阴影效果正确显示
```scss
.header-cell.is-frozen,
.table-cell-wrapper.is-frozen {
  position: sticky;
  left: 70px;
  z-index: 5;
  background-color: $gray-50;
  box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
}
```

### 步骤4: 优化右键菜单的图标显示

**目标**: 为右键菜单项添加合适的图标

**修改文件**: `ContextMenu.vue`, `TableView.vue`

**具体修改**:

1. 在 `ContextMenu.vue` 中添加更多图标支持
```typescript
// 添加 sort 图标
<svg v-else-if="item.icon === 'sort'" ...>...</svg>

// 添加 freeze 图标
<svg v-else-if="item.icon === 'freeze'" ...>...</svg>

// 添加 hide 图标
<svg v-else-if="item.icon === 'hide'" ...>...</svg>

// 添加 settings/edit 图标（用于编辑字段属性）
<svg v-else-if="item.icon === 'settings'" ...>...</svg>
```

2. 在 `TableView.vue` 的 `contextMenuItems` 中为菜单项添加图标
```typescript
{ id: "sort-asc", label: "升序排列", icon: "sort" },
{ id: "sort-desc", label: "降序排列", icon: "sort" },
{ id: "freeze", label: "冻结列", icon: "freeze" },
{ id: "unfreeze", label: "取消冻结", icon: "freeze" },
{ id: "hide-field", label: "隐藏字段", icon: "hide" },
{ id: "edit-field", label: "编辑字段属性", icon: "settings" },
```

### 步骤5: 添加操作反馈提示

**目标**: 为各操作添加适当的反馈提示

**修改文件**: `TableView.vue`

**具体修改**:

在 `handleContextMenuSelect` 中为各操作添加成功提示：
```typescript
case "freeze":
  // ... 原有逻辑
  ElMessage.success(`已冻结列：${contextMenuField.value?.name}`);
  break;

case "unfreeze":
  // ... 原有逻辑
  ElMessage.success(`已取消冻结列：${contextMenuField.value?.name}`);
  break;

case "hide-field":
  // ... 原有逻辑
  ElMessage.success(`已隐藏字段：${contextMenuField.value?.name}`);
  break;
```

## 数据流图

```
用户右键点击列头
    ↓
TableView.handleHeaderContextMenu(field, event)
    ↓
显示 ContextMenu，设置 contextMenuField = field
    ↓
用户选择菜单项
    ↓
TableView.handleContextMenuSelect(item)
    ↓
根据 item.id 执行不同操作：
    ├── freeze/unfreeze → viewStore.updateFrozenFields() → 更新视图状态 → 重新渲染表格
    ├── hide-field → viewStore.updateHiddenFields() → 更新视图状态 → 重新渲染表格
    └── edit-field → 打开 FieldDialog → 编辑字段 → fieldService.updateField() → 刷新表格数据
```

## 界面交互设计

### 右键菜单样式

```
┌─────────────────────────┐
│  📊 升序排列             │
│  📊 降序排列             │
│  ─────────────────────  │
│  ❄️ 冻结列               │  (或 "❄️ 取消冻结" 如果已冻结)
│  ─────────────────────  │
│  👁️ 隐藏字段             │
│  ⚙️ 编辑字段属性         │
└─────────────────────────┘
```

### 冻结列视觉效果

- 冻结列右侧显示阴影效果 `box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05)`
- 冻结列头显示冻结图标和"已冻结"文字标签
- 冻结列在水平滚动时保持固定位置

### 字段编辑对话框

- 从右键菜单打开时直接进入指定字段的编辑界面
- 支持修改字段名称、类型、必填状态、描述等属性
- 根据字段类型显示对应的配置选项（如选项字段的选项列表）

## 测试计划

### 功能测试

1. **冻结列功能测试**
   - [ ] 右键点击列头，显示"冻结列"选项
   - [ ] 点击"冻结列"后，该列固定在左侧
   - [ ] 水平滚动时，冻结列保持可见
   - [ ] 再次右键点击已冻结列，显示"取消冻结"选项
   - [ ] 点击"取消冻结"后，该列恢复正常滚动
   - [ ] 冻结多列时，各列位置正确

2. **隐藏字段功能测试**
   - [ ] 右键点击列头，显示"隐藏字段"选项
   - [ ] 点击"隐藏字段"后，该列从表格中消失
   - [ ] 被隐藏的字段在"字段管理"中显示为隐藏状态
   - [ ] 从"字段管理"中恢复显示后，字段重新出现在表格中

3. **编辑字段属性功能测试**
   - [ ] 右键点击列头，显示"编辑字段属性"选项
   - [ ] 点击后打开字段编辑对话框
   - [ ] 对话框中显示当前字段的属性
   - [ ] 修改字段名称后保存，表格列头同步更新
   - [ ] 修改字段类型后保存，数据正确转换
   - [ ] 修改选项字段的选项后保存，单元格下拉选项同步更新

### 兼容性测试

1. **不同视图模式测试**
   - [ ] 在表格视图中功能正常
   - [ ] 切换视图后，冻结/隐藏设置保持正确

2. **多表切换测试**
   - [ ] 切换数据表后，右键菜单功能正常
   - [ ] 各表的字段设置相互独立

3. **边界情况测试**
   - [ ] 表格无字段时的处理
   - [ ] 冻结最后一列时的处理
   - [ ] 隐藏所有字段时的处理
   - [ ] 系统字段的编辑限制

### 性能测试

- [ ] 大数据量表格（1000+行）下右键菜单响应速度
- [ ] 频繁冻结/解冻操作的性能
- [ ] 字段编辑后的刷新性能

## 风险与注意事项

1. **数据一致性**
   - 视图级隐藏与全局隐藏的区别需要明确
   - 建议统一使用视图级隐藏，避免混淆

2. **冻结列数量限制**
   - 建议限制最大冻结列数（如最多3列），避免占用过多屏幕空间
   - 超过限制时显示提示信息

3. **系统字段保护**
   - 系统字段（如创建时间、创建人等）不应允许编辑或删除
   - 右键菜单中相应选项应禁用或隐藏

4. **并发操作**
   - 字段编辑期间，其他用户对同一字段的操作需要处理
   - 建议添加乐观锁或版本控制

## 实施时间表

| 步骤 | 任务 | 预计时间 |
|------|------|----------|
| 1 | 完善编辑字段属性功能 | 2小时 |
| 2 | 优化 FieldDialog 支持直接编辑 | 1小时 |
| 3 | 优化冻结列视觉效果 | 1小时 |
| 4 | 优化右键菜单图标 | 1小时 |
| 5 | 添加操作反馈提示 | 30分钟 |
| 6 | 功能测试与调试 | 2小时 |
| **总计** | | **约7.5小时** |
