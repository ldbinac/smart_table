# 表单配置数据持久化修复计划

## 问题分析

### 当前问题
1. 表单配置存储在 `Base.vue` 的 `formConfig` ref 中，仅存在于内存
2. 页面刷新后配置丢失
3. 分享链接页面无法获取配置

### 根本原因
- 表单配置没有保存到数据库
- 表单视图（ViewEntity）的 config 字段未被使用来存储表单特定配置

## 解决方案

### 方案：使用 ViewEntity.config 存储表单配置

将表单配置存储在视图配置中，因为表单视图本身就是一个视图类型，其配置信息应该存储在 ViewEntity 的 config 字段中。

## 实施步骤

### 步骤 1: 定义表单配置类型

**文件**: `src/types/views.ts`

添加表单视图配置类型定义：
```typescript
export interface FormViewConfig {
  title: string;
  description: string;
  submitButtonText: string;
  visibleFieldIds: string[];
  successMessage: string;
  allowMultipleSubmit: boolean;
}
```

### 步骤 2: 修改 Base.vue 加载和保存配置

**文件**: `src/views/Base.vue`

**加载配置**:
- 当切换到表单视图时，从当前视图的 config 中读取表单配置
- 如果 config 为空，使用默认配置

**保存配置**:
- 当用户保存表单配置时，更新当前视图的 config
- 调用 viewStore 更新视图配置

### 步骤 3: 修改 FormShare.vue 读取配置

**文件**: `src/views/FormShare.vue`

- 从 localStorage 加载表单配置（分享链接场景）
- 或者从 URL 参数中获取 tableId，然后加载对应视图的配置

### 步骤 4: 修改 FormShareDialog 保存配置

**文件**: `src/components/views/FormView/FormShareDialog.vue`

- 生成分享链接时，将表单配置保存到 localStorage
- 或者将配置编码到 URL 中

## 详细实现

### 1. 类型定义

```typescript
// src/types/views.ts
export interface FormViewConfig {
  title: string;
  description: string;
  submitButtonText: string;
  visibleFieldIds: string[];
  successMessage: string;
  allowMultipleSubmit: boolean;
}

// 默认配置
export const defaultFormConfig: FormViewConfig = {
  title: '数据收集表单',
  description: '',
  submitButtonText: '提交',
  visibleFieldIds: [],
  successMessage: '提交成功，感谢您的参与！',
  allowMultipleSubmit: true
};
```

### 2. Base.vue 修改

```typescript
// 加载表单配置
const loadFormConfig = () => {
  const currentView = viewStore.currentView;
  if (currentView?.type === ViewType.FORM && currentView.config) {
    const config = currentView.config as FormViewConfig;
    formConfig.value = { ...defaultFormConfig, ...config };
  } else {
    formConfig.value = { ...defaultFormConfig };
    // 初始化 visibleFieldIds
    const systemFieldTypes = ['createdBy', 'createdTime', 'updatedBy', 'updatedTime', 'autoNumber'];
    formConfig.value.visibleFieldIds = baseStore.fields
      .filter(f => !systemFieldTypes.includes(f.type))
      .map(f => f.id);
  }
};

// 保存表单配置
const handleFormConfigSave = async (config: FormViewConfig) => {
  formConfig.value = { ...config };
  
  // 保存到视图配置
  const currentView = viewStore.currentView;
  if (currentView && currentView.type === ViewType.FORM) {
    await viewStore.updateView(currentView.id, {
      config: { ...config }
    });
  }
  
  ElMessage.success("表单配置已保存");
};

// 监听视图切换
watch(() => viewStore.currentView, () => {
  if (viewStore.currentView?.type === ViewType.FORM) {
    loadFormConfig();
  }
}, { immediate: true });
```

### 3. FormShare.vue 修改

```typescript
// 加载表单配置
const loadFormConfig = () => {
  // 从 localStorage 加载
  const storedConfig = localStorage.getItem(`form_config_${tableId.value}`);
  if (storedConfig) {
    const config = JSON.parse(storedConfig);
    formConfig.value = { ...defaultFormConfig, ...config };
  }
};
```

### 4. FormShareDialog.vue 修改

```typescript
// 生成分享链接时保存配置
const generateShareLink = () => {
  // ... 生成 formId
  
  // 保存配置到 localStorage
  localStorage.setItem(`form_config_${props.tableId}`, JSON.stringify({
    title: props.formConfig?.title,
    description: props.formConfig?.description,
    submitButtonText: props.formConfig?.submitButtonText,
    successMessage: props.formConfig?.successMessage,
    visibleFieldIds: props.fields.map(f => f.id)
  }));
  
  // ... 生成链接
};
```

## 数据流

```
用户配置表单
    ↓
Base.vue 保存配置
    ↓
ViewEntity.config (IndexedDB)
    ↓
页面刷新后自动加载

分享表单
    ↓
FormShareDialog 保存配置到 localStorage
    ↓
FormShare.vue 从 localStorage 加载配置
```

## 测试计划

1. **配置保存测试**:
   - 配置表单 → 刷新页面 → 验证配置是否保留
   - 切换视图 → 切换回表单视图 → 验证配置是否保留

2. **分享链接测试**:
   - 配置表单 → 生成分享链接 → 在新窗口打开 → 验证配置是否正确显示

3. **边界测试**:
   - 无配置时的默认行为
   - 配置部分字段时的行为
   - 删除视图后配置的处理

## 时间安排

| 任务 | 预计时间 | 实际时间 |
|-----|---------|---------|
| 添加类型定义 | 0.5h | - |
| 修改 Base.vue | 1.5h | - |
| 修改 FormShare.vue | 1h | - |
| 修改 FormShareDialog.vue | 0.5h | - |
| 测试验证 | 1h | - |
| **总计** | **4.5h** | - |
