<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useRoute } from "vue-router";
import { useBaseStore } from "@/stores";
import { useViewStore } from "@/stores/viewStore";
import { useTableStore } from "@/stores/tableStore";
import { TableView } from "@/components/views/TableView";
import KanbanView from "@/components/views/KanbanView/KanbanView.vue";
import CalendarView from "@/components/views/CalendarView/CalendarView.vue";
import ViewSwitcher from "@/components/views/ViewSwitcher.vue";
import Loading from "@/components/common/Loading.vue";
import FieldDialog from "@/components/dialogs/FieldDialog.vue";
import FilterDialog from "@/components/dialogs/FilterDialog.vue";
import SortDialog from "@/components/dialogs/SortDialog.vue";
import ExportDialog from "@/components/dialogs/ExportDialog.vue";
import RecordDialog from "@/components/dialogs/RecordDialog.vue";
import AddRecordDialog from "@/components/dialogs/AddRecordDialog.vue";
import { ViewType } from "@/types";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FilterCondition, SortConfig } from "@/types/filters";
import type { CellValue } from "@/types";
import { applyFilters, applySorts } from "@/utils";
import Sortable from "sortablejs";

const route = useRoute();
const baseStore = useBaseStore();
const viewStore = useViewStore();
const tableStore = useTableStore();

const isLoading = computed(() => baseStore.loading || viewStore.loading);
const currentTableId = computed(() => baseStore.currentTable?.id || "");

// 创建数据表对话框显示状态
const createTableDialogVisible = ref(false);

// 创建数据表表单数据
const createTableForm = reactive({
  name: "",
  description: "",
});

// 表单引用
const createTableFormRef = ref<FormInstance>();

// 表单验证规则
const createTableFormRules: FormRules = {
  name: [
    { required: true, message: "请输入数据表名称", trigger: "blur" },
    { min: 1, max: 50, message: "名称长度在 1 到 50 个字符", trigger: "blur" },
  ],
};

// 对话框显示状态
const fieldDialogVisible = ref(false);
const filterDialogVisible = ref(false);
const sortDialogVisible = ref(false);
const exportDialogVisible = ref(false);
const renameTableDialogVisible = ref(false);
const recordDialogVisible = ref(false);
const addRecordDialogVisible = ref(false);

// 当前编辑的记录
const editingRecord = ref<any>(null);

// 添加记录的初始值（用于日历视图等预填充数据）
const addRecordInitialValues = ref<Record<string, unknown>>({});

// 添加记录的分组信息（用于看板视图）
const addRecordGroupInfo = ref<{
  groupFieldId?: string;
  groupId?: string;
  groupName?: string;
}>({});

// 重命名表单
const renameTableForm = reactive({
  id: "",
  name: "",
});
const renameTableFormRef = ref<FormInstance>();
const renameTableFormRules: FormRules = {
  name: [
    { required: true, message: "请输入数据表名称", trigger: "blur" },
    { min: 1, max: 50, message: "名称长度在 1 到 50 个字符", trigger: "blur" },
  ],
};

// 筛选和排序状态
const activeFilters = ref<FilterCondition[]>([]);
const activeSorts = ref<SortConfig[]>([]);
const filterConjunction = ref<"and" | "or">("and");

// 搜索关键词
const tableSearchKeyword = ref("");

// 过滤后的表格列表
const filteredTables = computed(() => {
  if (!tableSearchKeyword.value.trim()) {
    return baseStore.sortedTables;
  }
  const keyword = tableSearchKeyword.value.toLowerCase();
  return baseStore.sortedTables.filter((table) =>
    table.name.toLowerCase().includes(keyword),
  );
});

// 过滤和排序后的记录
const filteredRecords = computed(() => {
  let records = [...baseStore.records];

  // 应用筛选
  if (activeFilters.value.length > 0) {
    records = applyFilters(
      records,
      activeFilters.value,
      baseStore.fields,
      filterConjunction.value,
    );
  }

  // 应用排序
  if (activeSorts.value.length > 0) {
    records = applySorts(records, activeSorts.value, baseStore.fields);
  }

  return records;
});

// 当前视图类型
const currentViewType = computed(() => {
  return viewStore.currentView?.type || ViewType.TABLE;
});

// 是否为表格视图
const isTableView = computed(() => currentViewType.value === ViewType.TABLE);

// 是否为看板视图
const isKanbanView = computed(() => currentViewType.value === ViewType.KANBAN);

// 是否为日历视图
const isCalendarView = computed(
  () => currentViewType.value === ViewType.CALENDAR,
);

// 表格列表引用（用于拖拽排序）
const tableListRef = ref<HTMLElement | null>(null);
let sortableInstance: Sortable | null = null;

onMounted(async () => {
  const baseId = route.params.id as string;
  if (baseId) {
    await baseStore.loadBase(baseId);
    // 同步视图数据到 viewStore
    if (baseStore.currentTable) {
      await viewStore.loadViews(baseStore.currentTable.id);
    }
    initSortable();
  }
});

watch(
  () => route.params.id,
  async (newId) => {
    if (newId) {
      await baseStore.loadBase(newId as string);
      // 同步视图数据到 viewStore
      if (baseStore.currentTable) {
        await viewStore.loadViews(baseStore.currentTable.id);
      }
      initSortable();
    }
  },
);

// 初始化拖拽排序
function initSortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
  }

  if (tableListRef.value) {
    sortableInstance = new Sortable(tableListRef.value, {
      handle: ".drag-handle",
      animation: 150,
      onEnd: handleTableDragEnd,
    });
  }
}

// 处理表格拖拽结束
async function handleTableDragEnd(evt: Sortable.SortableEvent) {
  if (evt.oldIndex === evt.newIndex) return;

  const tableIds = filteredTables.value.map((t) => t.id);
  const [movedId] = tableIds.splice(evt.oldIndex!, 1);
  tableIds.splice(evt.newIndex!, 0, movedId);

  if (baseStore.currentBase) {
    await tableStore.reorderTables(baseStore.currentBase.id, tableIds);
    // 刷新表格列表
    baseStore.tables = await tableStore.loadTables(baseStore.currentBase.id);
  }
}

const handleTableSelect = async (tableId: string) => {
  await baseStore.loadTable(tableId);
  // 同步视图数据到 viewStore
  await viewStore.loadViews(tableId);
  // 重置筛选和排序
  activeFilters.value = [];
  activeSorts.value = [];
};

const handleViewChange = async (viewId: string) => {
  await viewStore.selectView(viewId);
};

const handleRecordSelect = (record: any) => {
  console.log("Selected record:", record);
};

const handleRecordsSelect = (records: any[]) => {
  console.log("Selected records:", records);
};

// 处理添加记录（来自看板视图和日历视图）
const handleAddRecord = (
  values: Record<string, unknown> = {},
  groupInfo?: { groupFieldId?: string; groupId?: string; groupName?: string },
) => {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }

  // 保存初始值和分组信息
  addRecordInitialValues.value = values;
  addRecordGroupInfo.value = groupInfo || {};
  addRecordDialogVisible.value = true;
};

// 处理保存新记录
const handleSaveNewRecord = async (values: Record<string, unknown>) => {
  if (!baseStore.currentTable) return;

  try {
    const record = await tableStore.createRecord({
      tableId: baseStore.currentTable.id,
      values: values as Record<string, CellValue>,
    });

    if (record) {
      baseStore.records.push(record);
      ElMessage.success("记录创建成功");
      addRecordDialogVisible.value = false;
    } else {
      ElMessage.error(tableStore.error || "创建记录失败");
    }
  } catch (error) {
    ElMessage.error("创建记录失败");
    console.error(error);
  }
};

// 处理编辑记录
const handleEditRecord = (recordId: string) => {
  const record = baseStore.records.find((r) => r.id === recordId);
  if (record) {
    editingRecord.value = record;
    recordDialogVisible.value = true;
  }
};

// 处理保存记录
const handleSaveRecord = async (
  recordId: string,
  values: Record<string, unknown>,
) => {
  try {
    const typedValues: Record<string, CellValue> = {};
    Object.keys(values).forEach((key) => {
      typedValues[key] = values[key] as CellValue;
    });
    await tableStore.updateRecord(recordId, typedValues);
    // 更新本地记录
    const index = baseStore.records.findIndex((r) => r.id === recordId);
    if (index !== -1) {
      baseStore.records[index] = {
        ...baseStore.records[index],
        values: { ...baseStore.records[index].values, ...typedValues },
        updatedAt: Date.now(),
      };
    }
    ElMessage.success("记录更新成功");
  } catch (error) {
    ElMessage.error("更新记录失败");
    console.error(error);
  }
};

// 处理删除记录
const handleDeleteRecord = async (recordId: string) => {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }

  try {
    // 显示确认对话框
    await ElMessageBox.confirm(
      "确定要删除这条记录吗？此操作无法恢复。",
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );

    // 执行删除
    await tableStore.deleteRecord(recordId);

    // 从本地记录列表中移除
    const index = baseStore.records.findIndex((r) => r.id === recordId);
    if (index !== -1) {
      baseStore.records.splice(index, 1);
    }

    ElMessage.success("记录删除成功");
  } catch (error) {
    // 用户取消删除时不显示错误
    if (error !== "cancel") {
      ElMessage.error("删除记录失败");
      console.error(error);
    }
  }
};

// 打开创建数据表对话框
function openCreateTableDialog() {
  if (!baseStore.currentBase) {
    ElMessage.warning("请先选择一个 Base");
    return;
  }
  createTableDialogVisible.value = true;
  createTableForm.name = "";
  createTableForm.description = "";
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
    ElMessage.error("请先选择一个 Base");
    return;
  }

  await createTableFormRef.value.validate(async (valid) => {
    if (valid) {
      const table = await tableStore.createTable({
        baseId: baseStore.currentBase!.id,
        name: createTableForm.name,
        description: createTableForm.description || undefined,
      });

      if (table) {
        ElMessage.success("数据表创建成功");
        closeCreateTableDialog();
        // 刷新当前 base 的表格列表并选中新创建的表格
        await baseStore.loadBase(baseStore.currentBase!.id);
        await baseStore.loadTable(table.id);
      } else {
        ElMessage.error(tableStore.error || "创建失败");
      }
    }
  });
}

// 打开重命名对话框
function openRenameTableDialog(table: { id: string; name: string }) {
  renameTableForm.id = table.id;
  renameTableForm.name = table.name;
  renameTableDialogVisible.value = true;
}

// 关闭重命名对话框
function closeRenameTableDialog() {
  renameTableDialogVisible.value = false;
  renameTableFormRef.value?.resetFields();
}

// 处理重命名表格
async function handleRenameTable() {
  if (!renameTableFormRef.value) return;

  await renameTableFormRef.value.validate(async (valid) => {
    if (valid) {
      await tableStore.updateTable(renameTableForm.id, {
        name: renameTableForm.name,
      });
      // 同步更新 baseStore 中的表格名称
      const tableIndex = baseStore.tables.findIndex(
        (t) => t.id === renameTableForm.id,
      );
      if (tableIndex !== -1) {
        baseStore.tables[tableIndex].name = renameTableForm.name;
      }
      if (baseStore.currentTable?.id === renameTableForm.id) {
        baseStore.currentTable.name = renameTableForm.name;
      }
      ElMessage.success("重命名成功");
      closeRenameTableDialog();
    }
  });
}

// 处理删除表格
async function handleDeleteTable(table: { id: string; name: string }) {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据表 "${table.name}" 吗？此操作将删除该表中的所有数据，包括字段、记录和视图，且无法恢复。`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );

    await tableStore.deleteTable(table.id);
    // 从 baseStore 中移除
    baseStore.tables = baseStore.tables.filter((t) => t.id !== table.id);
    if (baseStore.currentTable?.id === table.id) {
      baseStore.currentTable = null;
      baseStore.fields = [];
      baseStore.records = [];
      baseStore.views = [];
      baseStore.currentView = null;
      // 如果有其他表格，选中第一个
      if (baseStore.tables.length > 0) {
        await baseStore.loadTable(baseStore.tables[0].id);
      }
    }
    ElMessage.success("删除成功");
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
    }
  }
}

// 处理收藏/取消收藏表格
async function handleToggleStarTable(table: {
  id: string;
  isStarred?: boolean;
}) {
  await tableStore.toggleStarTable(table.id);
  // 同步更新本地状态
  const tableIndex = baseStore.tables.findIndex((t) => t.id === table.id);
  if (tableIndex !== -1) {
    baseStore.tables[tableIndex].isStarred = !table.isStarred;
  }
  if (baseStore.currentTable?.id === table.id) {
    baseStore.currentTable.isStarred = !table.isStarred;
  }
  ElMessage.success(table.isStarred ? "已收藏" : "已取消收藏");
}

// 打开字段对话框
function openFieldDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
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
  const index = baseStore.fields.findIndex((f) => f.id === field.id);
  if (index !== -1) {
    baseStore.fields[index] = field;
  }
  ElMessage.success(`字段 "${field.name}" 更新成功`);
}

// 处理字段删除
function handleFieldDeleted(fieldId: string) {
  const index = baseStore.fields.findIndex((f) => f.id === fieldId);
  if (index !== -1) {
    const fieldName = baseStore.fields[index].name;
    baseStore.fields.splice(index, 1);
    ElMessage.success(`字段 "${fieldName}" 删除成功`);
  }
}

// 打开筛选对话框
function openFilterDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  filterDialogVisible.value = true;
}

// 处理筛选应用
function handleFilterApply(
  filters: FilterCondition[],
  conjunction: "and" | "or",
) {
  activeFilters.value = filters;
  filterConjunction.value = conjunction;
  if (filters.length > 0) {
    ElMessage.success(`已应用 ${filters.length} 个筛选条件`);
  }
}

// 处理筛选清除
function handleFilterClear() {
  activeFilters.value = [];
  ElMessage.success("筛选已清除");
}

// 打开排序对话框
function openSortDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
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
  ElMessage.success("排序已清除");
}

// 打开导出对话框
function openExportDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  exportDialogVisible.value = true;
}
</script>

<template>
  <div class="base-page">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h3>{{ baseStore.currentBase?.name || "加载中..." }}</h3>
      </div>

      <!-- 搜索框 -->
      <div class="sidebar-search">
        <el-input
          v-model="tableSearchKeyword"
          placeholder="搜索数据表"
          clearable
          size="small">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 表格列表 -->
      <div ref="tableListRef" class="table-list">
        <div
          v-for="table in filteredTables"
          :key="table.id"
          class="table-item"
          :class="{ active: baseStore.currentTable?.id === table.id }"
          @click="handleTableSelect(table.id)">
          <span class="drag-handle" @click.stop>
            <el-icon><Rank /></el-icon>
          </span>
          <el-icon class="table-icon"><Document /></el-icon>
          <span class="table-name">{{ table.name }}</span>
          <span v-if="table.isStarred" class="star-icon">
            <el-icon><StarFilled /></el-icon>
          </span>
          <el-dropdown
            trigger="click"
            @command="
              (cmd) => {
                if (cmd === 'rename') openRenameTableDialog(table);
                else if (cmd === 'delete') handleDeleteTable(table);
                else if (cmd === 'star') handleToggleStarTable(table);
              }
            "
            @click.stop>
            <span class="more-icon" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename">
                  <el-icon><Edit /></el-icon>重命名
                </el-dropdown-item>
                <el-dropdown-item command="star">
                  <el-icon
                    ><component :is="table.isStarred ? 'Star' : 'StarFilled'"
                  /></el-icon>
                  {{ table.isStarred ? "取消收藏" : "收藏" }}
                </el-dropdown-item>
                <el-dropdown-item divided command="delete" class="delete-item">
                  <el-icon><Delete /></el-icon>删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div v-if="filteredTables.length === 0" class="empty-tables">
          {{ tableSearchKeyword ? "没有找到匹配的数据表" : "暂无数据表" }}
        </div>
      </div>

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
              <span class="record-count"
                >{{ filteredRecords.length }} 条记录</span
              >
              <span v-if="activeFilters.length > 0" class="filter-badge">
                <el-tag size="small" type="warning"
                  >筛选: {{ activeFilters.length }}</el-tag
                >
              </span>
              <span v-if="activeSorts.length > 0" class="sort-badge">
                <el-tag size="small" type="success"
                  >排序: {{ activeSorts.length }}</el-tag
                >
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
            @view-change="handleViewChange" />

          <div class="table-content">
            <!-- 表格视图 -->
            <TableView
              v-if="isTableView"
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              @record-select="handleRecordSelect"
              @records-select="handleRecordsSelect" />

            <!-- 看板视图 -->
            <KanbanView
              v-else-if="isKanbanView"
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              :fields="baseStore.fields"
              @record-select="handleRecordSelect"
              @addRecord="handleAddRecord"
              @editRecord="handleEditRecord"
              @deleteRecord="handleDeleteRecord" />

            <!-- 日历视图 -->
            <CalendarView
              v-else-if="isCalendarView"
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              :fields="baseStore.fields"
              @record-select="handleRecordSelect"
              @addRecord="handleAddRecord"
              @editRecord="handleEditRecord" />

            <!-- 其他视图类型占位 -->
            <div v-else class="unsupported-view">
              <el-empty description="该视图类型暂不支持">
                <template #description>
                  <p>该视图类型暂不支持</p>
                  <p class="sub-text">请切换到表格视图、看板视图或日历视图</p>
                </template>
              </el-empty>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-state">
        <el-empty description="请选择或创建一个数据表">
          <el-button type="primary" @click="openCreateTableDialog"
            >创建数据表</el-button
          >
        </el-empty>
      </div>
    </main>

    <!-- 创建数据表对话框 -->
    <el-dialog
      v-model="createTableDialogVisible"
      title="创建数据表"
      width="500px"
      :close-on-click-modal="false">
      <el-form
        ref="createTableFormRef"
        :model="createTableForm"
        :rules="createTableFormRules"
        label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="createTableForm.name"
            placeholder="请输入数据表名称"
            maxlength="50"
            show-word-limit />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="createTableForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeCreateTableDialog">取消</el-button>
          <el-button type="primary" @click="handleCreateTable">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 重命名数据表对话框 -->
    <el-dialog
      v-model="renameTableDialogVisible"
      title="重命名数据表"
      width="500px"
      :close-on-click-modal="false">
      <el-form
        ref="renameTableFormRef"
        :model="renameTableForm"
        :rules="renameTableFormRules"
        label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="renameTableForm.name"
            placeholder="请输入数据表名称"
            maxlength="50"
            show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeRenameTableDialog">取消</el-button>
          <el-button type="primary" @click="handleRenameTable">确定</el-button>
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
      @field-deleted="handleFieldDeleted" />

    <!-- 筛选对话框 -->
    <FilterDialog
      v-model:visible="filterDialogVisible"
      :fields="baseStore.fields"
      :initial-filters="activeFilters"
      :initial-conjunction="filterConjunction"
      @apply="handleFilterApply"
      @clear="handleFilterClear" />

    <!-- 排序对话框 -->
    <SortDialog
      v-model:visible="sortDialogVisible"
      :fields="baseStore.fields"
      :initial-sorts="activeSorts"
      @apply="handleSortApply"
      @clear="handleSortClear" />

    <!-- 导出对话框 -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      :fields="baseStore.fields"
      :records="filteredRecords" />

    <!-- 记录编辑对话框 -->
    <RecordDialog
      v-model:visible="recordDialogVisible"
      :record="editingRecord"
      :fields="baseStore.fields"
      @save="handleSaveRecord" />

    <!-- 添加记录对话框 -->
    <AddRecordDialog
      v-model:visible="addRecordDialogVisible"
      :fields="baseStore.fields"
      :initial-values="addRecordInitialValues"
      :group-field-id="addRecordGroupInfo.groupFieldId"
      :group-id="addRecordGroupInfo.groupId"
      :group-name="addRecordGroupInfo.groupName"
      @save="handleSaveNewRecord" />
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.base-page {
  display: flex;
  height: calc(100vh - 56px);
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

.sidebar-search {
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-color;
}

.table-list {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-sm 0;
}

.table-item {
  display: flex;
  align-items: center;
  padding: $spacing-sm $spacing-lg;
  cursor: pointer;
  transition: all $transition-fast;
  gap: $spacing-sm;

  &:hover {
    background-color: $bg-color;

    .drag-handle,
    .more-icon {
      opacity: 1;
    }
  }

  &.active {
    background-color: rgba($primary-color, 0.1);
    color: $primary-color;

    .table-name {
      color: $primary-color;
      font-weight: 500;
    }
  }
}

.drag-handle {
  opacity: 0;
  cursor: grab;
  color: $text-secondary;
  transition: opacity $transition-fast;

  &:active {
    cursor: grabbing;
  }
}

.table-icon {
  color: $text-secondary;
  flex-shrink: 0;
}

.table-name {
  flex: 1;
  font-size: $font-size-sm;
  color: $text-primary;
  @include text-ellipsis;
}

.star-icon {
  color: #f7ba2a;
  flex-shrink: 0;
}

.more-icon {
  opacity: 0;
  cursor: pointer;
  color: $text-secondary;
  transition: opacity $transition-fast;
  padding: $spacing-xs;
  border-radius: $border-radius-sm;

  &:hover {
    background-color: rgba($text-secondary, 0.1);
  }
}

.empty-tables {
  padding: $spacing-lg;
  text-align: center;
  color: $text-secondary;
  font-size: $font-size-sm;
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

:deep(.delete-item) {
  color: $error-color;
}
</style>
