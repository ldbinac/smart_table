# 修复"创建数据表"按钮点击无效问题计划

## 问题分析

### 问题定位
在 `Base.vue` 文件中发现两处"创建数据表"按钮存在问题：

1. **侧边栏底部按钮**（第70行）：
   ```vue
   <el-button type="primary" text @click="() => {}">
   ```
   - 点击事件绑定了一个空函数 `() => {}`
   - 没有任何实际功能

2. **空状态按钮**（第124行）：
   ```vue
   <el-button type="primary">创建数据表</el-button>
   ```
   - 完全没有绑定点击事件

### 根本原因
- 按钮的点击事件没有正确绑定到实际的处理函数
- 缺少创建数据表的对话框组件
- 缺少表单验证和提交逻辑
- 缺少与 tableStore 的集成

## 解决方案

### 1. 修改 Base.vue 添加创建数据表功能

#### 1.1 添加导入
- 导入 `ref`, `reactive` 用于响应式数据
- 导入 `useTableStore` 用于创建表格
- 导入 `FormInstance`, `FormRules` 用于表单验证
- 导入 `ElMessage` 用于消息提示

#### 1.2 添加响应式数据
```typescript
// 创建对话框显示状态
const createTableDialogVisible = ref(false);

// 创建表单数据
const createTableForm = reactive({
  name: '',
  description: ''
});

// 表单引用
const createTableFormRef = ref<FormInstance>();
```

#### 1.3 添加表单验证规则
```typescript
const createTableFormRules: FormRules = {
  name: [
    { required: true, message: '请输入数据表名称', trigger: 'blur' },
    { min: 1, max: 50, message: '名称长度在 1 到 50 个字符', trigger: 'blur' }
  ]
};
```

#### 1.4 添加方法
```typescript
// 打开创建对话框
function openCreateTableDialog() {
  createTableDialogVisible.value = true;
  createTableForm.name = '';
  createTableForm.description = '';
}

// 关闭创建对话框
function closeCreateTableDialog() {
  createTableDialogVisible.value = false;
  createTableFormRef.value?.resetFields();
}

// 处理创建数据表
async function handleCreateTable() {
  if (!createTableFormRef.value) return;
  if (!baseStore.currentBase) {
    ElMessage.error('请先选择一个 Base');
    return;
  }
  
  await createTableFormRef.value.validate(async (valid) => {
    if (valid) {
      const table = await tableStore.createTable({
        baseId: baseStore.currentBase!.id,
        name: createTableForm.name,
        description: createTableForm.description || undefined
      });
      
      if (table) {
        ElMessage.success('数据表创建成功');
        closeCreateTableDialog();
        // 自动选中新创建的表格
        await baseStore.loadTable(table.id);
      } else {
        ElMessage.error(tableStore.error || '创建失败');
      }
    }
  });
}
```

#### 1.5 修改模板

**侧边栏按钮修改：**
```vue
<el-button type="primary" text @click="openCreateTableDialog">
  <el-icon><Plus /></el-icon>
  添加数据表
</el-button>
```

**空状态按钮修改：**
```vue
<el-button type="primary" @click="openCreateTableDialog">创建数据表</el-button>
```

#### 1.6 添加创建对话框
```vue
<el-dialog
  v-model="createTableDialogVisible"
  title="创建数据表"
  width="500px"
  :close-on-click-modal="false"
>
  <el-form
    ref="createTableFormRef"
    :model="createTableForm"
    :rules="createTableFormRules"
    label-width="80px"
  >
    <el-form-item label="名称" prop="name">
      <el-input
        v-model="createTableForm.name"
        placeholder="请输入数据表名称"
        maxlength="50"
        show-word-limit
      />
    </el-form-item>

    <el-form-item label="描述">
      <el-input
        v-model="createTableForm.description"
        type="textarea"
        :rows="3"
        placeholder="请输入描述（可选）"
        maxlength="200"
        show-word-limit
      />
    </el-form-item>
  </el-form>

  <template #footer>
    <span class="dialog-footer">
      <el-button @click="closeCreateTableDialog">取消</el-button>
      <el-button type="primary" @click="handleCreateTable">确定</el-button>
    </span>
  </template>
</el-dialog>
```

## 实施步骤

### 步骤 1: 修改 Base.vue 脚本部分
1. 添加必要的导入语句
2. 添加响应式数据（createTableDialogVisible, createTableForm, createTableFormRef）
3. 添加表单验证规则
4. 添加 openCreateTableDialog, closeCreateTableDialog, handleCreateTable 方法

### 步骤 2: 修改 Base.vue 模板部分
1. 修改侧边栏底部按钮的 @click 事件
2. 修改空状态按钮的 @click 事件
3. 添加创建数据表对话框

### 步骤 3: 添加样式
1. 添加对话框底部按钮样式

## 预期结果

1. 点击侧边栏的"添加数据表"按钮会弹出创建对话框
2. 点击空状态的"创建数据表"按钮也会弹出创建对话框
3. 对话框包含名称（必填）和描述（可选）字段
4. 表单验证确保名称不为空
5. 创建成功后显示成功消息，自动刷新表格列表并选中新表格
6. 创建失败显示错误消息

## 代码变更文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/views/Base.vue` | 修改 | 添加创建数据表功能 |
