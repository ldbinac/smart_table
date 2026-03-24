# 表单视图功能实施计划

## 概述

根据产品规划文档和开发任务清单，实现并完善表单视图（Form View）功能。表单视图用于数据收集和问卷调查场景。

## 需求分析

### 来自产品规划文档
- **表单视图**: 数据收集表单，用于信息收集和问卷调查
- 属于 Phase 3: 高级视图开发 (第7-9周)

### 来自开发任务清单 (3.5 表单视图)
| 序号 | 任务 | 优先级 | 预计工时 | 状态 |
|-----|------|--------|---------|------|
| 3.5.1 | 创建 FormView 表单视图组件 | P1 | 6h | 🔵 待开始 |
| 3.5.2 | 实现表单字段渲染 | P1 | 4h | 🔵 待开始 |
| 3.5.3 | 实现表单验证 | P1 | 4h | 🔵 待开始 |
| 3.5.4 | 实现表单提交 | P1 | 2h | 🔵 待开始 |
| 3.5.5 | 实现表单分享 (导出) | P2 | 4h | 🔵 待开始 |

## 当前状态分析

### 已完成
1. ✅ FormView.vue 组件已存在，基础结构已完成
2. ✅ 支持所有 18 种字段类型的渲染（通过 FieldComponentFactory）
3. ✅ 基础表单验证（必填、邮箱、电话、URL）
4. ✅ 表单提交和取消功能
5. ✅ ViewType.FORM 已定义在 types/views.ts
6. ✅ ViewSwitcher 已支持表单视图类型

### 需要完善
1. ❌ Base.vue 中未集成 FormView 组件
2. ❌ 表单视图配置支持（如选择显示哪些字段）
3. ❌ 表单分享/导出功能
4. ❌ 表单提交成功后的反馈
5. ❌ 只读模式下的表单展示优化

## 实施步骤

### 步骤 1: 在 Base.vue 中集成 FormView 组件

**文件**: `src/views/Base.vue`

**修改内容**:
1. 导入 FormView 组件
2. 添加 `isFormView` 计算属性
3. 在模板中添加 FormView 的渲染条件
4. 处理表单提交事件，创建新记录

**代码变更**:
```typescript
// 导入
import FormView from "@/components/views/FormView/FormView.vue";

// 计算属性
const isFormView = computed(() => currentViewType.value === ViewType.FORM);

// 处理表单提交
const handleFormSubmit = async (values: Record<string, CellValue>) => {
  // 创建新记录
};
```

### 步骤 2: 完善 FormView 组件功能

**文件**: `src/components/views/FormView/FormView.vue`

**增强功能**:
1. 添加表单提交成功提示
2. 支持表单配置（显示/隐藏字段）
3. 优化只读模式显示
4. 添加表单重置确认

### 步骤 3: 实现表单分享/导出功能

**文件**: 新建 `src/components/views/FormView/FormShareDialog.vue`

**功能**:
1. 生成表单分享链接（模拟）
2. 导出表单为 HTML 文件
3. 复制表单配置

### 步骤 4: 添加表单视图配置支持

**文件**: `src/components/views/FormView/FormViewConfig.vue`

**配置项**:
1. 选择要在表单中显示的字段
2. 设置提交按钮文本
3. 设置表单标题和描述

## 详细实现

### 1. Base.vue 集成

在 `table-content` div 中添加：

```vue
<!-- 表单视图 -->
<FormView
  v-else-if="isFormView"
  :fields="baseStore.fields"
  :readonly="false"
  @submit="handleFormSubmit"
  @cancel="handleFormCancel" />
```

添加处理函数：

```typescript
const handleFormSubmit = async (values: Record<string, CellValue>) => {
  if (!baseStore.currentTable) return;
  
  try {
    const record = await tableStore.createRecord({
      tableId: baseStore.currentTable.id,
      values
    });
    
    if (record) {
      baseStore.records.push(record);
      ElMessage.success("记录提交成功");
    }
  } catch (error) {
    ElMessage.error("提交失败");
  }
};

const handleFormCancel = () => {
  // 可选：返回表格视图或清空表单
};
```

### 2. FormView 增强

增强验证功能：
- 数字字段范围验证
- 文本字段长度验证
- 自定义验证规则支持

添加配置支持：
```typescript
interface FormConfig {
  title?: string;
  description?: string;
  submitButtonText?: string;
  visibleFieldIds?: string[];
}
```

### 3. 表单分享功能

创建分享对话框：
- 生成表单预览链接
- 导出为独立 HTML 文件
- 复制表单嵌入代码

## 测试计划

1. **功能测试**:
   - 切换至表单视图
   - 填写各类型字段
   - 验证必填字段
   - 提交表单创建记录
   - 验证记录是否正确创建

2. **边界测试**:
   - 空表单的显示
   - 大量字段的表单
   - 各种验证失败场景

3. **兼容性测试**:
   - 不同字段类型的渲染
   - 只读模式显示

## 时间安排

| 任务 | 预计时间 | 实际时间 |
|-----|---------|---------|
| Base.vue 集成 | 1h | - |
| FormView 增强 | 2h | - |
| 分享功能实现 | 2h | - |
| 测试与调试 | 1h | - |
| **总计** | **6h** | - |
