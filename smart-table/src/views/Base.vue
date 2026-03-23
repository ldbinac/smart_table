<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useBaseStore } from '@/stores';
import { useViewStore } from '@/stores/viewStore';
import { useTableStore } from '@/stores/tableStore';
import { TableView } from '@/components/views/TableView';
import ViewSwitcher from '@/components/views/ViewSwitcher.vue';
import Loading from '@/components/common/Loading.vue';
import FieldDialog from '@/components/dialogs/FieldDialog.vue';
import FilterDialog from '@/components/dialogs/FilterDialog.vue';
import SortDialog from '@/components/dialogs/SortDialog.vue';
import ExportDialog from '@/components/dialogs/ExportDialog.vue';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import type { FilterCondition, SortConfig } from '@/types/filters';
import { applyFilters, applySorts } from '@/utils';

const route = useRoute();
const baseStore = useBaseStore();
const viewStore = useViewStore();
const tableStore = useTableStore();

const isLoading = computed(() => baseStore.loading || viewStore.loading);
const currentTableId = computed(() => baseStore.currentTable?.id || '');

// 创建数据表对话框显示状态
const createTableDialogVisible = ref(false);

// 创建数据表表单数据
const createTableForm = reactive({
  name: '',
  description: ''
});

// 表单引用
const createTableFormRef = ref<FormInstance>();

// 表单验证规则
const createTableFormRules: FormRules = {
  name: [
    { required: true, message: '请输入数据表名称', trigger: 'blur' },
    { min: 1, max: 50, message: '名称长度在 1 到 50 个字符', trigger: 'blur' }
  ]
};

// 对话框显示状态
const fieldDialogVisible = ref(false);
const filterDialogVisible = ref(false);
const sortDialogVisible = ref(false);
const exportDialogVisible = ref(false);

// 筛选和排序状态
const activeFilters = ref<FilterCondition[]>([]);
const activeSorts = ref<SortConfig[]>([]);
const filterConjunction = ref<'and' | 'or'>('and');

// 过滤和排序后的记录
const filteredRecords = computed(() => {
  let records = [...baseStore.records];
  
  // 应用筛选
  if (activeFilters.value.length > 0) {
    records = applyFilters(records, activeFilters.value, baseStore.fields, filterConjunction.value);
  }
  
  // 应用排序
  if (activeSorts.value.length > 0) {
    records = applySorts(records, activeSorts.value, baseStore.fields);
  }
  
  return records;
});

onMounted(async () => {
  const baseId = route.params.id as string;
  if (baseId) {
    await baseStore.loadBase(baseId);
  }
});

watch(
  () => route.params.id,
  async (newId) => {
    if (newId) {
      await baseStore.loadBase(newId as string);
    }
  }
);

const handleTableSelect = async (tableId: string) => {
  await baseStore.loadTable(tableId);
  // 重置筛选和排序
  activeFilters.value = [];
  activeSorts.value = [];
};

const handleViewChange = async (viewId: string) => {
  await viewStore.selectView(viewId);
};

const handleRecordSelect = (record: any) => {
  console.log('Selected record:', record);
};

const handleRecordsSelect = (records: any[]) => {
  console.log('Selected records:', records);
};

// 打开创建数据表对话框
function openCreateTableDialog() {
  if (!baseStore.currentBase) {
    ElMessage.warning('请先选择一个 Base');
    return;
  }
  createTableDialogVisible.value = true;
  createTableForm.name = '';
  createTableForm.description = '';
}

// 关闭创建数据表对话框
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
        // 刷新当前 base 的表格列表并选中新创建的表格
        await baseStore.loadBase(baseStore.currentBase!.id);
        await baseStore.loadTable(table.id);
      } else {
        ElMessage.error(tableStore.error || '创建失败');
      }
    }
  });
}

// 打开字段对话框
function openFieldDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning('请先选择一个数据表');
    return;
  }
  fieldDialogVisible.value = true;
}

// 处理字段创建
function handleFieldCreated(field: any) {
  baseStore.fields.push(field);
  ElMessage.success(`字段 "${field.name}" 创建成功`);
}

// 处理字段更新
function handleFieldUpdated(field: any) {
  const index = baseStore.fields.findIndex(f => f.id === field.id);
  if (index !== -1) {
    baseStore.fields[index] = field;
  }
  ElMessage.success(`字段 "${field.name}" 更新成功`);
}

// 处理字段删除
function handleFieldDeleted(fieldId: string) {
  const index = baseStore.fields.findIndex(f => f.id === fieldId);
  if (index !== -1) {
    const fieldName = baseStore.fields[index].name;
    baseStore.fields.splice(index, 1);
    ElMessage.success(`字段 "${fieldName}" 删除成功`);
  }
}

// 打开筛选对话框
function openFilterDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning('请先选择一个数据表');
    return;
  }
  filterDialogVisible.value = true;
}

// 处理筛选应用
function handleFilterApply(filters: FilterCondition[], conjunction: 'and' | 'or') {
  activeFilters.value = filters;
  filterConjunction.value = conjunction;
  if (filters.length > 0) {
    ElMessage.success(`已应用 ${filters.length} 个筛选条件`);
  }
}

// 处理筛选清除
function handleFilterClear() {
  activeFilters.value = [];
  ElMessage.success('筛选已清除');
}

// 打开排序对话框
function openSortDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning('请先选择一个数据表');
    return;
  }
  sortDialogVisible.value = true;
}

// 处理排序应用
function handleSortApply(sorts: SortConfig[]) {
  activeSorts.value = sorts;
  if (sorts.length > 0) {
    ElMessage.success(`已应用 ${sorts.length} 个排序条件`);
  }
}

// 处理排序清除
function handleSortClear() {
  activeSorts.value = [];
  ElMessage.success('排序已清除');
}

// 打开导出对话框
function openExportDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning('请先选择一个数据表');
    return;
  }
  exportDialogVisible.value = true;
}
</script>

<template>
  <div class="base-page">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h3>{{ baseStore.currentBase?.name || '加载中...' }}</h3>
      </div>
      <el-menu
        :default-active="baseStore.currentTable?.id || ''"
        @select="handleTableSelect"
      >
        <el-menu-item
          v-for="table in baseStore.sortedTables"
          :key="table.id"
          :index="table.id"
        >
          <el-icon><Document /></el-icon>
          <span>{{ table.name }}</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <el-button type="primary" text @click="openCreateTableDialog">
          <el-icon><Plus /></el-icon>
          添加数据表
        </el-button>
      </div>
    </aside>
    <main class="main-content">
      <Loading v-if="isLoading" />
      <template v-else-if="baseStore.currentTable">
        <div class="table-container">
          <header class="table-header">
            <div class="table-info">
              <h2>{{ baseStore.currentTable.name }}</h2>
              <span class="record-count">{{ filteredRecords.length }} 条记录</span>
              <span v-if="activeFilters.length > 0" class="filter-badge">
                <el-tag size="small" type="warning">筛选: {{ activeFilters.length }}</el-tag>
              </span>
              <span v-if="activeSorts.length > 0" class="sort-badge">
                <el-tag size="small" type="success">排序: {{ activeSorts.length }}</el-tag>
              </span>
            </div>
            <div class="table-actions">
              <el-button-group>
                <el-button size="small" @click="openFilterDialog">
                  <el-icon><Filter /></el-icon>
                  筛选
                </el-button>
                <el-button size="small" @click="openSortDialog">
                  <el-icon><Sort /></el-icon>
                  排序
                </el-button>
                <el-button size="small" @click="openFieldDialog">
                  <el-icon><Grid /></el-icon>
                  字段
                </el-button>
              </el-button-group>
              <el-button type="primary" size="small" @click="openExportDialog">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </div>
          </header>

          <ViewSwitcher
            :table-id="currentTableId"
            @view-change="handleViewChange"
          />

          <div class="table-content">
            <TableView
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              @record-select="handleRecordSelect"
              @records-select="handleRecordsSelect"
            />
          </div>
        </div>
      </template>
      <div v-else class="empty-state">
        <el-empty description="请选择或创建一个数据表">
          <el-button type="primary" @click="openCreateTableDialog">创建数据表</el-button>
        </el-empty>
      </div>
    </main>

    <!-- 创建数据表对话框 -->
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

    <!-- 字段管理对话框 -->
    <FieldDialog
      v-model:visible="fieldDialogVisible"
      :table-id="currentTableId"
      :fields="baseStore.fields"
      @field-created="handleFieldCreated"
      @field-updated="handleFieldUpdated"
      @field-deleted="handleFieldDeleted"
    />

    <!-- 筛选对话框 -->
    <FilterDialog
      v-model:visible="filterDialogVisible"
      :fields="baseStore.fields"
      :initial-filters="activeFilters"
      :initial-conjunction="filterConjunction"
      @apply="handleFilterApply"
      @clear="handleFilterClear"
    />

    <!-- 排序对话框 -->
    <SortDialog
      v-model:visible="sortDialogVisible"
      :fields="baseStore.fields"
      :initial-sorts="activeSorts"
      @apply="handleSortApply"
      @clear="handleSortClear"
    />

    <!-- 导出对话框 -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      :fields="baseStore.fields"
      :records="filteredRecords"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.base-page {
  display: flex;
  height: 100vh;
  background-color: $bg-color;
}

.sidebar {
  width: $sidebar-width;
  display: flex;
  flex-direction: column;
  border-right: 1px solid $border-color;
  background: $surface-color;
}

.sidebar-header {
  padding: $spacing-lg;
  border-bottom: 1px solid $border-color;

  h3 {
    margin: 0;
    font-size: $font-size-lg;
    font-weight: 600;
    color: $text-primary;
  }
}

.sidebar-footer {
  padding: $spacing-md;
  border-top: 1px solid $border-color;
  margin-top: auto;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-lg;
  background: $surface-color;
  border-bottom: 1px solid $border-color;
}

.table-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  h2 {
    margin: 0;
    font-size: $font-size-xl;
    font-weight: 600;
    color: $text-primary;
  }

  .record-count {
    font-size: $font-size-sm;
    color: $text-secondary;
  }

  .filter-badge,
  .sort-badge {
    margin-left: 8px;
  }
}

.table-actions {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.table-content {
  flex: 1;
  overflow: hidden;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
