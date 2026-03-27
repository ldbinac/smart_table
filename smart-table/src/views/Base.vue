<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useRoute } from "vue-router";
import { useBaseStore } from "@/stores";
import { useViewStore } from "@/stores/viewStore";
import { useTableStore } from "@/stores/tableStore";
import {
  Setting,
  Share,
  Upload,
  ArrowLeft,
  ArrowRight,
} from "@element-plus/icons-vue";
import GroupedTableView from "@/components/groups/GroupedTableView.vue";
import { TableView } from "@/components/views/TableView";
import KanbanView from "@/components/views/KanbanView/KanbanView.vue";
import CalendarView from "@/components/views/CalendarView/CalendarView.vue";
import GanttView from "@/components/views/GanttView/GanttView.vue";
import GalleryView from "@/components/views/GalleryView/GalleryView.vue";
import FormView from "@/components/views/FormView/FormView.vue";
import FormViewConfig from "@/components/views/FormView/FormViewConfig.vue";
import FormShareDialog from "@/components/views/FormView/FormShareDialog.vue";
import ViewSwitcher from "@/components/views/ViewSwitcher.vue";
import Loading from "@/components/common/Loading.vue";
import FieldDialog from "@/components/dialogs/FieldDialog.vue";
import FilterDialog from "@/components/dialogs/FilterDialog.vue";
import SortDialog from "@/components/dialogs/SortDialog.vue";
import GroupDialog from "@/components/dialogs/GroupDialog.vue";
import ExportDialog from "@/components/dialogs/ExportDialog.vue";
import RecordDialog from "@/components/dialogs/RecordDialog.vue";
import AddRecordDialog from "@/components/dialogs/AddRecordDialog.vue";
import ImportDialog from "@/components/dialogs/ImportDialog.vue";
import { ViewType } from "@/types";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FilterCondition, SortConfig } from "@/types/filters";
import type { CellValue } from "@/types";
import type { FieldEntity, RecordEntity } from "@/db/schema";
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
const groupDialogVisible = ref(false);
const exportDialogVisible = ref(false);
const renameTableDialogVisible = ref(false);
const recordDialogVisible = ref(false);
const addRecordDialogVisible = ref(false);
const formConfigDialogVisible = ref(false);
const formShareDialogVisible = ref(false);
const importDialogVisible = ref(false);

// 表单配置
const formConfig = ref({
  title: "数据收集表单",
  description: "",
  submitButtonText: "提交",
  visibleFieldIds: [] as string[],
  successMessage: "提交成功，感谢您的参与！",
  allowMultipleSubmit: true,
});

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
const filterConjunction = ref<"and" | "or">("and");

// 从 viewStore 获取当前排序配置
const activeSorts = computed(() => viewStore.currentSorts);

// 搜索关键词
const tableSearchKeyword = ref("");

// 侧边栏展开/收缩状态
const isSidebarCollapsed = ref(false);

// 切换侧边栏状态
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};

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

// 是否为画册视图
const isGalleryView = computed(
  () => currentViewType.value === ViewType.GALLERY,
);

// 是否为甘特视图
const isGanttView = computed(() => currentViewType.value === ViewType.GANTT);

// 是否为表单视图
const isFormView = computed(() => currentViewType.value === ViewType.FORM);

// 当前分组配置
const currentGroupBys = computed(() => viewStore.currentGroupBys);

// 是否有分组配置
const hasGroupConfig = computed(() => currentGroupBys.value.length > 0);

// 打开分组对话框
function openGroupDialog() {
  groupDialogVisible.value = true;
}

// 处理分组配置应用
async function handleGroupApply(newGroupBy: string[]) {
  if (viewStore.currentView) {
    await viewStore.updateGroupBys(viewStore.currentView.id, newGroupBy);
    ElMessage.success("分组配置已应用");
  }
}

// 处理分组配置清除
async function handleGroupClear() {
  if (viewStore.currentView) {
    await viewStore.updateGroupBys(viewStore.currentView.id, []);
    ElMessage.success("分组已清除");
  }
}

// 表格列表引用（用于拖拽排序）
const tableListRef = ref<HTMLElement | null>(null);
let sortableInstance: Sortable | null = null;

onMounted(async () => {
  console.log("[Base] onMounted");
  const baseId = route.params.id as string;
  if (baseId) {
    await baseStore.loadBase(baseId);
    // 同步视图数据到 viewStore
    if (baseStore.currentTable) {
      console.log("[Base] Loading views for table:", baseStore.currentTable.id);
      await viewStore.loadViews(baseStore.currentTable.id);
      console.log("[Base] Views loaded:", viewStore.views.length);
      // 选择默认视图（这会设置 viewStore.currentView）
      await viewStore.selectDefaultView(baseStore.currentTable.id);
      console.log(
        "[Base] Default view selected:",
        viewStore.currentView?.id,
        viewStore.currentView?.type,
      );
      console.log("[Base] Default view config:", viewStore.currentView?.config);
    }
    initSortable();
  }
});

watch(
  () => route.params.id,
  async (newId) => {
    console.log("[Base] route.params.id changed:", newId);
    if (newId) {
      await baseStore.loadBase(newId as string);
      // 同步视图数据到 viewStore
      if (baseStore.currentTable) {
        await viewStore.loadViews(baseStore.currentTable.id);
        // 选择默认视图（这会设置 viewStore.currentView）
        await viewStore.selectDefaultView(baseStore.currentTable.id);
        console.log(
          "[Base] After route change - currentView:",
          viewStore.currentView?.id,
          viewStore.currentView?.type,
        );
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
  // 选择默认视图（这会设置 viewStore.currentView，并自动加载视图的排序配置）
  await viewStore.selectDefaultView(tableId);
  // 重置筛选
  activeFilters.value = [];
  // 关闭分组弹窗，确保切换数据表时弹窗状态正确
  groupDialogVisible.value = false;
};

const handleViewChange = async (viewId: string) => {
  await viewStore.selectView(viewId);
  // 如果切换到表单视图，加载表单配置
  const selectedView = viewStore.views.find((v) => v.id === viewId);
  if (selectedView?.type === ViewType.FORM) {
    loadFormConfig();
  }
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

// 处理从分组表格添加记录
const handleAddRecordFromGroup = (groupInfo: {
  groupFieldId?: string;
  groupId?: string;
  groupName?: string;
}) => {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }

  // 构建初始值，包含分组字段的值
  const initialValues: Record<string, unknown> = {};
  if (groupInfo.groupFieldId && groupInfo.groupId) {
    initialValues[groupInfo.groupFieldId] = groupInfo.groupId;
  }

  // 保存初始值和分组信息
  addRecordInitialValues.value = initialValues;
  addRecordGroupInfo.value = groupInfo;
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

// 处理表单提交
const handleFormSubmit = async (values: Record<string, CellValue>) => {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }

  try {
    const record = await tableStore.createRecord({
      tableId: baseStore.currentTable.id,
      values,
    });

    if (record) {
      baseStore.records.push(record);
      ElMessage.success("表单提交成功，记录已创建");
    } else {
      ElMessage.error(tableStore.error || "提交失败");
    }
  } catch (error) {
    ElMessage.error("提交失败");
    console.error(error);
  }
};

// 处理表单取消
const handleFormCancel = () => {
  // 切换到表格视图
  const tableView = baseStore.views.find((v) => v.type === ViewType.TABLE);
  if (tableView) {
    viewStore.selectView(tableView.id);
  }
};

// 加载表单配置
const loadFormConfig = () => {
  console.log("[FormConfig] Loading form config...");
  const currentView = viewStore.currentView;
  console.log("[FormConfig] Current view:", currentView?.id, currentView?.type);
  console.log("[FormConfig] Current view config:", currentView?.config);

  const systemFieldTypes = [
    "createdBy",
    "createdTime",
    "updatedBy",
    "updatedTime",
    "autoNumber",
  ];

  // 获取所有非系统字段作为默认可见字段
  const defaultVisibleFieldIds = baseStore.fields
    .filter((f) => !systemFieldTypes.includes(f.type))
    .map((f) => f.id);

  console.log(
    "[FormConfig] Default visible field IDs:",
    defaultVisibleFieldIds,
  );

  if (currentView?.type === ViewType.FORM && currentView.config) {
    const config = currentView.config as {
      title?: string;
      description?: string;
      submitButtonText?: string;
      visibleFieldIds?: string[];
      successMessage?: string;
      allowMultipleSubmit?: boolean;
    };

    // 检查配置中是否明确设置了 visibleFieldIds
    // 如果 config 中有 visibleFieldIds 属性（即使是空数组），使用它
    // 如果没有 visibleFieldIds 属性，使用默认值
    const hasVisibleFieldIdsConfig = "visibleFieldIds" in currentView.config;
    console.log(
      "[FormConfig] Has visibleFieldIds config:",
      hasVisibleFieldIdsConfig,
    );
    console.log("[FormConfig] Config visibleFieldIds:", config.visibleFieldIds);

    formConfig.value = {
      title: config.title ?? "数据收集表单",
      description: config.description ?? "",
      submitButtonText: config.submitButtonText ?? "提交",
      visibleFieldIds: hasVisibleFieldIdsConfig
        ? (config.visibleFieldIds ?? [])
        : defaultVisibleFieldIds,
      successMessage: config.successMessage ?? "提交成功，感谢您的参与！",
      allowMultipleSubmit: config.allowMultipleSubmit ?? true,
    };
  } else {
    console.log("[FormConfig] Using default config");
    // 使用默认配置
    formConfig.value = {
      title: "数据收集表单",
      description: "",
      submitButtonText: "提交",
      visibleFieldIds: defaultVisibleFieldIds,
      successMessage: "提交成功，感谢您的参与！",
      allowMultipleSubmit: true,
    };
  }
  console.log("[FormConfig] Loaded formConfig:", formConfig.value);
};

// 监听当前视图变化，自动加载表单配置
watch(
  () => viewStore.currentView,
  (newView, oldView) => {
    console.log(
      "[Base] viewStore.currentView changed:",
      newView?.id,
      newView?.type,
    );
    console.log("[Base] Old view:", oldView?.id, oldView?.type);
    if (newView?.type === ViewType.FORM && newView?.id !== oldView?.id) {
      console.log("[Base] Loading form config due to view change");
      loadFormConfig();
    }
  },
  { immediate: true },
);

// 打开表单配置对话框
const openFormConfigDialog = () => {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  // 加载当前视图的配置
  loadFormConfig();
  formConfigDialogVisible.value = true;
};

// 保存表单配置
const handleFormConfigSave = async (config: typeof formConfig.value) => {
  console.log("[FormConfig] Saving config:", config);
  formConfig.value = { ...config };

  // 保存到视图配置
  const currentView = viewStore.currentView;
  console.log("[FormConfig] Current view:", currentView?.id, currentView?.type);
  console.log(
    "[FormConfig] Current view config before save:",
    currentView?.config,
  );

  if (currentView && currentView.type === ViewType.FORM) {
    const newConfig = {
      ...currentView.config,
      title: config.title,
      description: config.description,
      submitButtonText: config.submitButtonText,
      visibleFieldIds: config.visibleFieldIds,
      successMessage: config.successMessage,
      allowMultipleSubmit: config.allowMultipleSubmit,
    };
    console.log("[FormConfig] New config to save:", newConfig);

    await viewStore.updateView(currentView.id, {
      config: newConfig,
    });

    console.log(
      "[FormConfig] View after update:",
      viewStore.currentView?.config,
    );
  }

  ElMessage.success("表单配置已保存");
};

// 打开表单分享对话框
const openFormShareDialog = () => {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  formShareDialogVisible.value = true;
};

// 处理编辑记录（用于 GroupedTableView）
const handleEditRecord = (record: RecordEntity) => {
  editingRecord.value = record;
  recordDialogVisible.value = true;
};

// 处理编辑记录（用于其他视图，接收 recordId）
const handleEditRecordById = (recordId: string) => {
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

// 处理字段重排序
function handleFieldsReordered(fieldIds: string[]) {
  // 更新本地字段顺序
  const sortedFields = fieldIds
    .map((id) => baseStore.fields.find((f) => f.id === id))
    .filter((f): f is FieldEntity => f !== undefined);

  // 更新 order 属性
  sortedFields.forEach((field, index) => {
    field.order = index;
  });

  baseStore.fields = sortedFields;
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
async function handleSortApply(sorts: SortConfig[]) {
  if (viewStore.currentView) {
    await viewStore.updateSorts(viewStore.currentView.id, sorts);
    if (sorts.length > 0) {
      ElMessage.success(`已应用 ${sorts.length} 个排序条件`);
    }
  }
}

// 处理排序清除
async function handleSortClear() {
  if (viewStore.currentView) {
    await viewStore.updateSorts(viewStore.currentView.id, []);
    ElMessage.success("排序已清除");
  }
}

// 打开导出对话框
function openExportDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  exportDialogVisible.value = true;
}

// 打开导入对话框
function openImportDialog() {
  if (!baseStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  importDialogVisible.value = true;
}

// 处理导入完成
function handleImported() {
  // 刷新数据
  if (baseStore.currentTable) {
    tableStore.selectTable(baseStore.currentTable.id);
  }
}
</script>

<template>
  <div class="base-page">
    <aside class="sidebar" :class="{ collapsed: isSidebarCollapsed }">
      <div class="sidebar-header">
        <div class="header-content" v-show="!isSidebarCollapsed">
          <el-tooltip
            :content="baseStore.currentBase?.name || '加载中...'"
            placement="bottom"
            :show-after="300"
            :disabled="!baseStore.currentBase?.name">
            <h3>{{ baseStore.currentBase?.name || "加载中..." }}</h3>
          </el-tooltip>
          <el-tooltip
            v-if="baseStore.currentBase?.description"
            :content="baseStore.currentBase.description"
            placement="bottom"
            :show-after="300">
            <p class="base-description">
              {{ baseStore.currentBase.description }}
            </p>
          </el-tooltip>
        </div>
        <button
          class="collapse-btn"
          @click="toggleSidebar"
          :title="isSidebarCollapsed ? '展开' : '收起'">
          <el-icon v-if="isSidebarCollapsed"><ArrowRight /></el-icon>
          <el-icon v-else><ArrowLeft /></el-icon>
        </button>
      </div>

      <!-- 搜索框 -->
      <div v-show="!isSidebarCollapsed" class="sidebar-search">
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
        <template v-for="table in filteredTables" :key="table.id">
          <!-- 收缩状态下的表格项（带Tooltip） -->
          <el-tooltip
            v-if="isSidebarCollapsed"
            :content="table.name"
            placement="right"
            :show-after="300">
            <div
              class="table-item"
              :class="{ active: baseStore.currentTable?.id === table.id }"
              @click="handleTableSelect(table.id)">
              <el-icon class="table-icon"><Document /></el-icon>
            </div>
          </el-tooltip>
          <!-- 展开状态下的表格项 -->
          <div
            v-else
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
                  <el-dropdown-item
                    divided
                    command="delete"
                    class="delete-item">
                    <el-icon><Delete /></el-icon>删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
        <div
          v-if="filteredTables.length === 0 && !isSidebarCollapsed"
          class="empty-tables">
          {{ tableSearchKeyword ? "没有找到匹配的数据表" : "暂无数据表" }}
        </div>
      </div>

      <div class="sidebar-footer">
        <el-button type="primary" text @click="openCreateTableDialog">
          <el-icon><Plus /></el-icon>
          <span v-show="!isSidebarCollapsed">添加数据表</span>
        </el-button>
      </div>
    </aside>
    <main class="main-content">
      <Loading v-if="isLoading" />
      <template v-else-if="baseStore.currentTable">
        <div class="table-container">
          <ViewSwitcher
            :table-id="currentTableId"
            @view-change="handleViewChange" />

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
              <span v-if="hasGroupConfig" class="group-badge">
                <el-tag size="small" type="primary"
                  >分组: {{ currentGroupBys.length }}</el-tag
                >
              </span>
            </div>
            <div class="table-actions">
              <el-button-group>
                <el-button
                  size="small"
                  :type="activeFilters.length > 0 ? 'primary' : 'default'"
                  @click="openFilterDialog">
                  <el-icon><Filter /></el-icon>
                  筛选
                  <el-tag
                    v-if="activeFilters.length > 0"
                    size="small"
                    class="filter-badge">
                    {{ activeFilters.length }}
                  </el-tag>
                </el-button>
                <el-button
                  size="small"
                  :type="activeSorts.length > 0 ? 'primary' : 'default'"
                  @click="openSortDialog">
                  <el-icon><Sort /></el-icon>
                  排序
                  <el-tag
                    v-if="activeSorts.length > 0"
                    size="small"
                    class="sort-badge">
                    {{ activeSorts.length }}
                  </el-tag>
                </el-button>
                <el-button
                  size="small"
                  :type="hasGroupConfig ? 'primary' : 'default'"
                  @click="openGroupDialog">
                  <el-icon><Folder /></el-icon>
                  分组
                  <el-tag
                    v-if="hasGroupConfig"
                    size="small"
                    class="group-badge">
                    {{ currentGroupBys.length }}
                  </el-tag>
                </el-button>
                <el-button size="small" @click="openFieldDialog">
                  <el-icon><Grid /></el-icon>
                  字段
                </el-button>
              </el-button-group>
              <el-button-group v-if="isFormView">
                <el-button size="small" @click="openFormConfigDialog">
                  <el-icon><Setting /></el-icon>
                  配置
                </el-button>
                <el-button size="small" @click="openFormShareDialog">
                  <el-icon><Share /></el-icon>
                  分享
                </el-button>
              </el-button-group>
              <el-button size="small" @click="openImportDialog">
                <el-icon><Upload /></el-icon>
                导入
              </el-button>
              <el-button type="primary" size="small" @click="openExportDialog">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </div>
          </header>

          <div class="table-content">
            <!-- 表格视图 - 分组模式 -->
            <GroupedTableView
              v-if="isTableView && hasGroupConfig"
              :fields="baseStore.fields"
              :records="filteredRecords as any[]"
              :group-by="currentGroupBys"
              @row-click="handleRecordSelect"
              @cell-click="handleEditRecord"
              @add-record="handleAddRecordFromGroup" />

            <!-- 表格视图 - 普通模式 -->
            <TableView
              v-else-if="isTableView"
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
              @editRecord="handleEditRecordById"
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
              @editRecord="handleEditRecordById" />

            <!-- 甘特视图 -->
            <GanttView
              v-else-if="isGanttView"
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              :fields="baseStore.fields"
              @updateRecord="handleSaveRecord"
              @addRecord="handleAddRecord"
              @editRecord="handleEditRecordById"
              @deleteRecord="handleDeleteRecord" />

            <!-- 画册视图 -->
            <GalleryView
              v-else-if="isGalleryView"
              :records="filteredRecords"
              :fields="baseStore.fields"
              @editRecord="handleEditRecordById"
              @deleteRecord="handleDeleteRecord" />

            <!-- 表单视图 -->
            <FormView
              v-else-if="isFormView"
              :fields="baseStore.fields"
              :readonly="false"
              :title="formConfig.title"
              :description="formConfig.description"
              :submit-button-text="formConfig.submitButtonText"
              :visible-field-ids="formConfig.visibleFieldIds"
              @submit="handleFormSubmit"
              @cancel="handleFormCancel" />

            <!-- 其他视图类型占位 -->
            <div v-else class="unsupported-view">
              <el-empty description="该视图类型暂不支持">
                <template #description>
                  <p>该视图类型暂不支持</p>
                  <p class="sub-text">
                    请切换到表格视图、看板视图、日历视图或甘特视图
                  </p>
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
      @field-deleted="handleFieldDeleted"
      @fields-reordered="handleFieldsReordered" />

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

    <!-- 分组对话框 -->
    <GroupDialog
      v-model:visible="groupDialogVisible"
      :fields="baseStore.fields"
      :initial-group-by="currentGroupBys"
      @apply="handleGroupApply"
      @clear="handleGroupClear" />

    <!-- 导出对话框 -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      :fields="baseStore.fields"
      :records="filteredRecords" />

    <!-- 记录编辑对话框 -->
    <RecordDialog
      v-model:visible="recordDialogVisible"
      :record="editingRecord"
      :fields="baseStore.sortedFields"
      @save="handleSaveRecord" />

    <!-- 添加记录对话框 -->
    <AddRecordDialog
      v-model:visible="addRecordDialogVisible"
      :fields="baseStore.sortedFields"
      :initial-values="addRecordInitialValues"
      :group-field-id="addRecordGroupInfo.groupFieldId"
      :group-id="addRecordGroupInfo.groupId"
      :group-name="addRecordGroupInfo.groupName"
      @save="handleSaveNewRecord" />

    <!-- 表单配置对话框 -->
    <FormViewConfig
      v-model:visible="formConfigDialogVisible"
      :fields="baseStore.fields"
      :initial-config="formConfig"
      @save="handleFormConfigSave" />

    <!-- 表单分享对话框 -->
    <FormShareDialog
      v-model:visible="formShareDialogVisible"
      :fields="baseStore.fields"
      :table-name="baseStore.currentTable?.name"
      :table-id="baseStore.currentTable?.id"
      :form-config="{
        title: formConfig.title,
        description: formConfig.description,
        submitButtonText: formConfig.submitButtonText,
        successMessage: formConfig.successMessage,
        visibleFieldIds: formConfig.visibleFieldIds,
        allowMultipleSubmit: formConfig.allowMultipleSubmit,
      }" />

    <!-- 数据导入对话框 -->
    <ImportDialog
      v-model:visible="importDialogVisible"
      :table-id="baseStore.currentTable?.id || ''"
      :fields="baseStore.fields"
      @imported="handleImported" />
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
  margin-right: 5px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid $border-color;
  background: $surface-color;
  transition: width $transition-normal;
  overflow: hidden;
  flex-shrink: 0;

  &.collapsed {
    width: $sidebar-collapsed-width;

    .sidebar-header {
      justify-content: center;
      padding: $spacing-md $spacing-sm;

      h3 {
        display: none;
      }
    }

    .sidebar-search {
      display: none;
    }

    .table-list {
      padding: $spacing-sm 0;
    }

    .table-item {
      justify-content: center;
      padding: $spacing-md $spacing-sm;
      gap: 0;

      .drag-handle,
      .table-name,
      .star-icon,
      .more-icon {
        display: none;
      }

      .table-icon {
        margin: 0;
      }

      &.active {
        background-color: rgba($primary-color, 0.15);
      }
    }

    .empty-tables {
      display: none;
    }

    .sidebar-footer {
      padding: $spacing-sm;

      .el-button {
        padding: $spacing-sm;
        justify-content: center;

        span:not(.el-icon) {
          display: none;
        }
      }
    }
  }
}

.sidebar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: $spacing-lg;
  border-bottom: 1px solid $border-color;
  min-height: 56px;
  gap: $spacing-sm;

  .header-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
  }

  h3 {
    margin: 0;
    font-size: $font-size-lg;
    font-weight: 600;
    color: $text-primary;
    @include text-ellipsis;
    line-height: 1.4;
  }

  .base-description {
    margin: 0;
    font-size: $font-size-xs;
    color: $text-secondary;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: default;
  }
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: $border-radius-sm;
  color: $text-secondary;
  cursor: pointer;
  transition: all $transition-fast;
  flex-shrink: 0;

  &:hover {
    background-color: $bg-color;
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
  .sort-badge,
  .group-badge {
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
