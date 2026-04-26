<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBaseStore } from "@/stores";
import { useViewStore } from "@/stores/viewStore";
import { useTableStore } from "@/stores/tableStore";
import {
  Setting,
  Share,
  Upload,
  Document,
  User,
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
import RecordDetailDrawer from "@/components/dialogs/RecordDetailDrawer.vue";
import AddRecordDrawer from "@/components/dialogs/AddRecordDrawer.vue";
import ImportDialog from "@/components/dialogs/ImportDialog.vue";
import ExcelImportCreateDialog from "@/components/dialogs/ExcelImportCreateDialog.vue";
import MemberManagementDialog from "@/components/dialogs/MemberManagementDialog.vue";
import BaseShareDialog from "@/components/dialogs/BaseShareDialog.vue";
import { ViewType } from "@/types";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FilterCondition, SortConfig } from "@/types/filters";
import type { CellValue } from "@/types";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import { applyFilters, applySorts } from "@/utils";
import Sortable from "sortablejs";
import { dashboardService } from "@/db/services/dashboardService";
import { tableService } from "@/db/services/tableService";
import BaseSidebar from "@/components/common/BaseSidebar.vue";
import DashboardView from "@/views/Dashboard.vue";
import { useEntityOperations } from "@/composables/useEntityOperations";
import { useRealtimeCollaboration } from "@/composables/useRealtimeCollaboration";
import OnlineUsers from "@/components/collaboration/OnlineUsers.vue";
import ConnectionStatusBar from "@/components/collaboration/ConnectionStatusBar.vue";
import CollaborationToast from "@/components/collaboration/CollaborationToast.vue";
import ConflictDialog from "@/components/collaboration/ConflictDialog.vue";
import { useCollaborationStore } from "@/stores/collaborationStore";

const route = useRoute();
const router = useRouter();
const baseStore = useBaseStore();
const viewStore = useViewStore();
const tableStore = useTableStore();
const collaborationStore = useCollaborationStore();

const baseId = route.params.id as string;
const realtimeCollab = baseId ? useRealtimeCollaboration(baseId) : null;

// 初始化实体操作
const {
  renameTable,
  deleteTable,
  toggleStarTable,
  renameDashboard,
  deleteDashboard,
  toggleStarDashboard,
} = useEntityOperations();

const isLoading = computed(
  () => baseStore.loading || viewStore.loading || tableStore.loading,
);
const currentTableId = computed(() => tableStore.currentTable?.id || "");

// 权限控制计算属性
const canEdit = computed(() => baseStore.canEdit);
const canManage = computed(() => baseStore.canManage);
const isOwner = computed(() => baseStore.isOwner);
const currentUserRole = computed(() => baseStore.currentUserRole);

// 使用 tableStore.fields 计算可见字段，确保状态同步
const visibleFields = computed(() => {
  const fields = tableStore.fields;
  // 首先过滤掉 isVisible 为 false 的字段（全局隐藏）
  let result = fields.filter((field) => (field as any).isVisible !== false);
  // 再根据当前视图的 hiddenFields 进行过滤（视图级隐藏）
  if (viewStore.currentView) {
    result = result.filter(
      (field) => !viewStore.currentView!.hiddenFields.includes(field.id),
    );
  }
  return result;
});

// 创建数据表对话框显示状态
const createTableDialogVisible = ref(false);

// 数据表管理对话框显示状态
const showTableManager = ref(false);

// 创建仪表盘对话框显示状态
const createDashboardDialogVisible = ref(false);

// 成员管理对话框显示状态
const showMemberManagement = ref(false);

// Base 分享对话框显示状态
const showBaseShare = ref(false);

// 创建仪表盘表单数据
const createDashboardForm = reactive({
  name: "",
  description: "",
});

// 仪表盘表单引用
const createDashboardFormRef = ref<FormInstance>();

// 仪表盘表单验证规则
const createDashboardFormRules: FormRules = {
  name: [
    { required: true, message: "请输入仪表盘名称", trigger: "blur" },
    { min: 1, max: 50, message: "名称长度在 1 到 50 个字符", trigger: "blur" },
  ],
};

// 重命名仪表盘对话框显示状态
const renameDashboardDialogVisible = ref(false);

// 重命名仪表盘表单数据
const renameDashboardForm = reactive({
  id: "",
  name: "",
  description: "",
});

// 重命名仪表盘表单引用
const renameDashboardFormRef = ref<FormInstance>();

// 重命名仪表盘表单验证规则
const renameDashboardFormRules: FormRules = {
  name: [
    { required: true, message: "请输入仪表盘名称", trigger: "blur" },
    { min: 1, max: 50, message: "名称长度在 1 到 50 个字符", trigger: "blur" },
  ],
};

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
const excelImportCreateDialogVisible = ref(false);

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

// 当前编辑的字段ID（用于字段管理对话框）
const editingFieldId = ref<string | null>(null);

// Drawer 抽屉大小（响应式）
const drawerSize = computed(() => {
  const width = window.innerWidth;
  if (width < 768) return "100%";
  if (width < 1024) return "70%";
  if (width < 1440) return "50%";
  return "600px";
});

// 添加记录的初始值（用于日历视图等预填充数据）
const addRecordInitialValues = ref<Record<string, unknown>>({});

// 添加记录的分组信息（用于看板视图）
const addRecordGroupInfo = ref<{
  groupFieldId?: string;
  groupId?: string;
  groupName?: string;
  groupLevels?: Array<{
    fieldId: string;
    fieldName: string;
    value: string;
    valueId?: string;
  }>;
}>({});

// 重命名表单
const renameTableForm = reactive({
  id: "",
  name: "",
  description: "",
});
const renameTableFormRef = ref<FormInstance>();
const renameTableFormRules: FormRules = {
  name: [
    { required: true, message: "请输入数据表名称", trigger: "blur" },
    { min: 1, max: 50, message: "名称长度在 1 到 50 个字符", trigger: "blur" },
  ],
};

// 筛选和排序状态
// 从 viewStore 获取当前筛选和排序配置
const activeFilters = computed(() => viewStore.currentFilters);
const filterConjunction = ref<"and" | "or">("and");

// 从 viewStore 获取当前排序配置
const activeSorts = computed(() => viewStore.currentSorts);

// 侧边栏引用
const sidebarRef = ref<InstanceType<typeof BaseSidebar> | null>(null);

// 过滤和排序后的记录
const filteredRecords = computed(() => {
  let records = [...tableStore.records];

  // 应用筛选
  if (activeFilters.value.length > 0) {
    records = applyFilters(
      records,
      activeFilters.value,
      tableStore.fields,
      filterConjunction.value,
    );
  }

  // 应用排序
  if (activeSorts.value.length > 0) {
    records = applySorts(records, activeSorts.value, tableStore.fields);
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
  const currentBaseId = route.params.id as string;
  if (currentBaseId) {
    const shareInfo = localStorage.getItem(`share_permission_${currentBaseId}`);
    if (shareInfo) {
      try {
        const info = JSON.parse(shareInfo);
        if (info && info.share_token && typeof info.share_token === "string") {
          await baseStore.fetchBase(currentBaseId, info.share_token);
        } else {
          localStorage.removeItem(`share_permission_${currentBaseId}`);
          await baseStore.fetchBase(currentBaseId);
        }
      } catch (e) {
        localStorage.removeItem(`share_permission_${currentBaseId}`);
        await baseStore.fetchBase(currentBaseId);
      }
    } else {
      await baseStore.fetchBase(currentBaseId);
    }
    await baseStore.fetchMembers(currentBaseId);
    await tableStore.loadTables(currentBaseId);

    // 如果有表格且当前没有选择表格，自动选择第一个表格
    if (tableStore.tables.length > 0 && !tableStore.currentTable) {
      const firstTable = tableStore.tables[0];
      await tableStore.selectTable(firstTable.id);
      // 同步视图数据到 viewStore
      await viewStore.loadViews(firstTable.id);
      // 选择默认视图（这会设置 viewStore.currentView）
      await viewStore.selectDefaultView(firstTable.id);

      // 如果默认视图是表单视图，加载表单配置
      if (viewStore.currentView?.type === ViewType.FORM) {
        loadFormConfig();
      }
    } else if (tableStore.currentTable) {
      // 如果已经有选中的表格，同步视图数据
      await viewStore.loadViews(tableStore.currentTable.id);
      // 选择默认视图（这会设置 viewStore.currentView）
      await viewStore.selectDefaultView(tableStore.currentTable.id);

      // 如果默认视图是表单视图，加载表单配置
      if (viewStore.currentView?.type === ViewType.FORM) {
        loadFormConfig();
      }
    }
    initSortable();
  }

  tableStore.setupRealtimeListeners();
  viewStore.setupRealtimeListeners();

  // 监听来自 AppHeader 的分享和成员按钮点击事件
  window.addEventListener("open-base-share", handleOpenBaseShare);
  window.addEventListener("open-member-management", handleOpenMemberManagement);
});

onUnmounted(() => {
  tableStore.cleanupRealtimeListeners();
  viewStore.cleanupRealtimeListeners();
  window.removeEventListener("open-base-share", handleOpenBaseShare);
  window.removeEventListener(
    "open-member-management",
    handleOpenMemberManagement,
  );
});

// 处理打开分享对话框
const handleOpenBaseShare = () => {
  if (canManage.value) {
    showBaseShare.value = true;
  }
};

// 处理打开成员管理对话框
const handleOpenMemberManagement = () => {
  if (canManage.value) {
    showMemberManagement.value = true;
  }
};

watch(
  () => route.params.id,
  async (newId) => {
    if (newId) {
      await baseStore.fetchBase(newId as string);
      await tableStore.loadTables(newId as string);

      // 如果有表格且当前没有选择表格，自动选择第一个表格
      if (tableStore.tables.length > 0 && !tableStore.currentTable) {
        const firstTable = tableStore.tables[0];
        await tableStore.selectTable(firstTable.id);
        // 同步视图数据到 viewStore
        await viewStore.loadViews(firstTable.id);
        // 选择默认视图（这会设置 viewStore.currentView）
        await viewStore.selectDefaultView(firstTable.id);

        // 如果默认视图是表单视图，加载表单配置
        if (viewStore.currentView?.type === ViewType.FORM) {
          loadFormConfig();
        }
      } else if (tableStore.currentTable) {
        // 如果已经有选中的表格，同步视图数据
        await viewStore.loadViews(tableStore.currentTable.id);
        // 选择默认视图（这会设置 viewStore.currentView）
        await viewStore.selectDefaultView(tableStore.currentTable.id);

        // 如果默认视图是表单视图，加载表单配置
        if (viewStore.currentView?.type === ViewType.FORM) {
          loadFormConfig();
        }
      }
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

  const tableIds = tableStore.tables.map((t) => t.id);
  const [movedId] = tableIds.splice(evt.oldIndex!, 1);
  tableIds.splice(evt.newIndex!, 0, movedId);

  if (baseStore.currentBase) {
    await tableStore.reorderTables(baseStore.currentBase.id, tableIds);
    // 刷新表格列表
    await tableStore.loadTables(baseStore.currentBase.id);
  }
}

const handleTableSelect = async (tableId: string) => {
  await tableStore.selectTable(tableId);
  // 同步视图数据到 viewStore
  await viewStore.loadViews(tableId);
  // 选择默认视图（这会设置 viewStore.currentView，并自动加载视图的排序配置）
  await viewStore.selectDefaultView(tableId);
  // 重置筛选
  activeFilters.value = [];
  // 关闭分组弹窗，确保切换数据表时弹窗状态正确
  groupDialogVisible.value = false;
};

// 处理点击仪表盘
const handleDashboardClick = (dashboardId: string) => {
  // 使用正确的路由格式：/base/:id/dashboard/:dashboardId
  const baseId = route.params.id as string;
  router.push(`/base/${baseId}/dashboard/${dashboardId}`);
};

const handleViewChange = async (viewId: string) => {
  await viewStore.selectView(viewId);
  // 如果切换到表单视图，加载表单配置
  const selectedView = viewStore.views.find((v) => v.id === viewId);
  if (selectedView?.type === ViewType.FORM) {
    loadFormConfig();
  }
};

const handleRecordSelect = (_record: any) => {
  // 记录选择处理
};

const handleRecordsSelect = (_records: any[]) => {
  // 多记录选择处理
};

// 处理添加记录（来自看板视图和日历视图）
const handleAddRecord = (
  values: Record<string, unknown> = {},
  groupInfo?: { groupFieldId?: string; groupId?: string; groupName?: string },
) => {
  if (!tableStore.currentTable) {
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
  groupLevels?: Array<{
    fieldId: string;
    fieldName: string;
    value: string;
    valueId?: string;
  }>;
}) => {
  if (!tableStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }

  // 构建初始值，包含所有层级分组字段的值
  const initialValues: Record<string, unknown> = {};

  // 优先使用 groupLevels（多层分组信息）
  if (groupInfo.groupLevels && groupInfo.groupLevels.length > 0) {
    for (const level of groupInfo.groupLevels) {
      if (level.fieldId && level.valueId) {
        initialValues[level.fieldId] = level.valueId;
      }
    }
  } else if (groupInfo.groupFieldId && groupInfo.groupId) {
    // 兼容旧版单层分组
    initialValues[groupInfo.groupFieldId] = groupInfo.groupId;
  }

  // 保存初始值和分组信息
  addRecordInitialValues.value = initialValues;
  addRecordGroupInfo.value = groupInfo;
  addRecordDialogVisible.value = true;
};

// 处理保存新记录
const handleSaveNewRecord = async (values: Record<string, unknown>) => {
  if (!tableStore.currentTable) return;

  try {
    const record = await tableStore.createRecord({
      tableId: tableStore.currentTable.id,
      values: values as Record<string, CellValue>,
    });

    if (record) {
      // tableStore.createRecord 已经内部添加了记录，不需要手动 push
      ElMessage.success("记录创建成功");
      addRecordDialogVisible.value = false;
    } else {
      ElMessage.error(tableStore.error || "创建记录失败");
    }
  } catch (error) {
    ElMessage.error("创建记录失败");
  }
};

// 处理表单提交
const handleFormSubmit = async (values: Record<string, CellValue>) => {
  if (!tableStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }

  try {
    const record = await tableStore.createRecord({
      tableId: tableStore.currentTable.id,
      values,
    });

    if (record) {
      // tableStore.createRecord 已经内部添加了记录，不需要手动 push
      ElMessage.success("表单提交成功，记录已创建");
    } else {
      ElMessage.error(tableStore.error || "提交失败");
    }
  } catch (error) {
    ElMessage.error("提交失败");
  }
};

// 处理表单取消
const handleFormCancel = () => {
  // 切换到表格视图
  const tableView = tableStore.views.find((v) => v.type === ViewType.TABLE);
  if (tableView) {
    viewStore.selectView(tableView.id);
  }
};

// 加载表单配置
const loadFormConfig = () => {
  const currentView = viewStore.currentView;

  const systemFieldTypes = [
    "createdBy",
    "createdTime",
    "updatedBy",
    "updatedTime",
    "autoNumber",
  ];

  // 获取所有非系统字段作为默认可见字段
  const defaultVisibleFieldIds = tableStore.fields
    .filter((f) => !systemFieldTypes.includes(f.type))
    .map((f) => f.id);

  if (currentView?.type === ViewType.FORM) {
    // 从 config 字段加载表单配置（后端会将 form_config 以 config 形式返回）
    const configData = currentView.config as {
      title?: string;
      description?: string;
      submitButtonText?: string;
      visibleFieldIds?: string[];
      successMessage?: string;
      allowMultipleSubmit?: boolean;
    };

    // 检查配置中是否明确设置了 visibleFieldIds
    // 如果 configData 中有 visibleFieldIds 属性（即使是空数组），使用它
    // 如果没有 visibleFieldIds 属性，使用默认值
    const hasVisibleFieldIdsConfig = configData?.visibleFieldIds !== undefined;

    formConfig.value = {
      title: configData?.title || "数据收集表单",
      description: configData?.description || "",
      submitButtonText: configData?.submitButtonText || "提交",
      visibleFieldIds: hasVisibleFieldIdsConfig
        ? configData!.visibleFieldIds || []
        : defaultVisibleFieldIds,
      successMessage: configData?.successMessage || "提交成功，感谢您的参与！",
      allowMultipleSubmit: configData?.allowMultipleSubmit !== false,
    };
  } else {
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
};

// 监听当前视图变化，自动加载表单配置
watch(
  () => viewStore.currentView,
  (newView, oldView) => {
    if (newView?.type === ViewType.FORM && newView?.id !== oldView?.id) {
      loadFormConfig();
    }
  },
  { immediate: true },
);

// 打开表单配置对话框
const openFormConfigDialog = () => {
  if (!tableStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  // 加载当前视图的配置
  loadFormConfig();
  formConfigDialogVisible.value = true;
};

// 保存表单配置
const handleFormConfigSave = async (config: typeof formConfig.value) => {
  formConfig.value = { ...config };

  // 保存到视图配置
  const currentView = viewStore.currentView;

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

    await viewStore.updateView(currentView.id, {
      config: newConfig,
    });
  }

  ElMessage.success("表单配置已保存");
};

// 打开表单分享对话框
const openFormShareDialog = () => {
  if (!tableStore.currentTable) {
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
  const record = tableStore.records.find((r) => r.id === recordId);
  if (record) {
    editingRecord.value = record;
    recordDialogVisible.value = true;
  }
};

// 处理放大查看记录（用于 GroupedTableView）
const handleExpandRecord = (record: RecordEntity) => {
  editingRecord.value = record;
  recordDialogVisible.value = true;
};

// 处理分组视图的排序
const handleSortFromGroup = async (
  fieldId: string,
  direction: "asc" | "desc",
) => {
  if (!viewStore.currentView) return;

  const currentSorts = viewStore.currentSorts as SortConfig[];
  const existingSortIndex = currentSorts.findIndex(
    (s) => s.fieldId === fieldId,
  );
  const newSorts = [...currentSorts];

  if (existingSortIndex > -1) {
    newSorts[existingSortIndex] = { fieldId, direction };
  } else {
    newSorts.push({ fieldId, direction });
  }

  await viewStore.updateSorts(
    viewStore.currentView.id,
    newSorts as SortConfig[],
  );
  ElMessage.success(
    `已按字段 ${props.fields.find((f) => f.id === fieldId)?.name || ""} ${direction === "asc" ? "升序" : "降序"}排列`,
  );
};

// 处理分组视图的冻结列
const handleFreezeFieldFromGroup = async (fieldId: string) => {
  if (!viewStore.currentView) return;

  const newFrozen = [...viewStore.currentView.frozenFields, fieldId];
  await viewStore.updateFrozenFields(viewStore.currentView.id, newFrozen);
  ElMessage.success("已冻结列");
};

// 处理分组视图的取消冻结列
const handleUnfreezeFieldFromGroup = async (fieldId: string) => {
  if (!viewStore.currentView) return;

  const newFrozen = viewStore.currentView.frozenFields.filter(
    (fid) => fid !== fieldId,
  );
  await viewStore.updateFrozenFields(viewStore.currentView.id, newFrozen);
  ElMessage.success("已取消冻结列");
};

// 处理分组视图的隐藏字段
const handleHideFieldFromGroup = async (fieldId: string) => {
  if (!viewStore.currentView) return;

  if (viewStore.currentView.hiddenFields.includes(fieldId)) {
    ElMessage.warning("该字段已经是隐藏状态");
    return;
  }

  const newHidden = [...viewStore.currentView.hiddenFields, fieldId];
  await viewStore.updateHiddenFields(viewStore.currentView.id, newHidden);
  ElMessage.success("已隐藏字段");
};

// 处理分组视图的编辑字段
const handleEditFieldFromGroup = (fieldId: string) => {
  editingFieldId.value = fieldId;
  fieldDialogVisible.value = true;
};

// 处理分组视图的删除记录
const handleDeleteRecordsFromGroup = async (records: RecordEntity[]) => {
  if (records.length === 0) return;

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${records.length} 条记录吗？`,
      "确认删除",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    // 批量删除记录
    for (const record of records) {
      await tableStore.deleteRecord(record.id);
      const index = tableStore.records.findIndex((r) => r.id === record.id);
      if (index > -1) {
        tableStore.records.splice(index, 1);
      }
    }

    ElMessage.success(`已删除 ${records.length} 条记录`);
  } catch (error) {
    // 用户取消删除
  }
};

// 处理分组视图的复制记录
const handleDuplicateRecordFromGroup = async (record: RecordEntity) => {
  if (!tableStore.currentTable) return;

  try {
    // 创建新记录，复制原记录的值
    // tableStore.createRecord 不再手动添加记录，而是通过实时事件监听添加
    const newRecord = await tableStore.createRecord({
      tableId: tableStore.currentTable.id,
      values: { ...record.values },
    });

    if (newRecord) {
      // 不再手动 push，因为实时事件会添加记录
      // 但为了立即打开编辑对话框，我们需要使用返回的记录
      ElMessage.success("记录复制成功");
      // 打开新记录的编辑对话框
      editingRecord.value = newRecord;
      recordDialogVisible.value = true;
    }
  } catch (error) {
    ElMessage.error("复制记录失败");
    console.error("复制记录失败:", error);
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
    const index = tableStore.records.findIndex((r) => r.id === recordId);
    if (index !== -1) {
      tableStore.records[index] = {
        ...tableStore.records[index],
        values: { ...tableStore.records[index].values, ...typedValues },
        updatedAt: Date.now(),
      };
    }
    ElMessage.success("记录更新成功");
  } catch (error) {
    ElMessage.error("更新记录失败");
  }
};

// 处理删除记录
const handleDeleteRecord = async (recordId: string) => {
  if (!tableStore.currentTable) {
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
    const index = tableStore.records.findIndex((r) => r.id === recordId);
    if (index !== -1) {
      tableStore.records.splice(index, 1);
    }

    ElMessage.success("记录删除成功");
  } catch (error) {
    // 用户取消删除时不显示错误
    if (error !== "cancel") {
      ElMessage.error("删除记录失败");
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

// 打开创建仪表盘对话框
function openCreateDashboardDialog() {
  if (!baseStore.currentBase) {
    ElMessage.warning("请先选择一个 Base");
    return;
  }
  createDashboardDialogVisible.value = true;
  createDashboardForm.name = "";
  createDashboardForm.description = "";
}

// 关闭创建仪表盘对话框
function closeCreateDashboardDialog() {
  createDashboardDialogVisible.value = false;
  createDashboardFormRef.value?.resetFields();
}

// 处理创建仪表盘
async function handleCreateDashboard() {
  if (!createDashboardFormRef.value) return;
  if (!baseStore.currentBase) {
    ElMessage.error("请先选择一个 Base");
    return;
  }

  await createDashboardFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const { dashboardService } =
          await import("@/db/services/dashboardService");
        const dashboard = await dashboardService.createDashboard({
          baseId: baseStore.currentBase!.id,
          name: createDashboardForm.name.trim(),
          description: createDashboardForm.description || undefined,
          widgets: [],
        });

        if (dashboard) {
          ElMessage.success("仪表盘创建成功");
          closeCreateDashboardDialog();
          // 刷新仪表盘列表
          sidebarRef.value?.refreshDashboards();
          // 跳转到仪表盘页面
          const baseId = route.params.id as string;
          router.push(`/base/${baseId}/dashboard/${dashboard.id}`);
        } else {
          ElMessage.error("创建失败");
        }
      } catch (error) {
        ElMessage.error("创建仪表盘失败");
      }
    }
  });
}

// 关闭创建数据表对话框
function closeCreateTableDialog() {
  createTableDialogVisible.value = false;
  createTableFormRef.value?.resetFields();
}

// 打开重命名仪表盘对话框
function openRenameDashboardDialog(dashboard: {
  id: string;
  name: string;
  description?: string;
}) {
  renameDashboardForm.id = dashboard.id;
  renameDashboardForm.name = dashboard.name;
  renameDashboardForm.description = dashboard.description || "";
  renameDashboardDialogVisible.value = true;
}

// 关闭重命名仪表盘对话框
function closeRenameDashboardDialog() {
  renameDashboardDialogVisible.value = false;
  renameDashboardFormRef.value?.resetFields();
}

// 处理重命名仪表盘
async function handleRenameDashboard() {
  if (!renameDashboardFormRef.value) return;

  await renameDashboardFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        // 使用通用操作模块
        await renameDashboard(
          {
            id: renameDashboardForm.id,
            name: renameDashboardForm.name,
            description: renameDashboardForm.description,
          } as Dashboard,
          renameDashboardForm.name,
          renameDashboardForm.description,
        );
        closeRenameDashboardDialog();
        // 刷新仪表盘列表
        sidebarRef.value?.refreshDashboards();
      } catch (error) {
        // 错误已经在通用模块中处理
      }
    }
  });
}

// 处理删除仪表盘
async function handleDeleteDashboard(dashboard: { id: string; name: string }) {
  try {
    // 使用通用操作模块
    await deleteDashboard(dashboard as Dashboard, () => {
      // 刷新仪表盘列表
      sidebarRef.value?.refreshDashboards();
      // 如果当前正在查看该仪表盘，跳转到 base 首页
      if (route.params.dashboardId === dashboard.id) {
        const baseId = route.params.id as string;
        router.push(`/base/${baseId}`);
      }
    });
  } catch (error: any) {
    // 错误已经在通用模块中处理
  }
}

// 处理切换仪表盘收藏状态
async function handleToggleStarDashboard(dashboard: {
  id: string;
  isStarred: boolean;
}) {
  try {
    // 使用通用操作模块
    await toggleStarDashboard(dashboard as Dashboard);
    // 刷新仪表盘列表
    sidebarRef.value?.refreshDashboards();
  } catch (error) {
    // 错误已经在通用模块中处理
  }
}

// 处理仪表盘排序
async function handleReorderDashboards(dashboardIds: string[]) {
  try {
    if (!baseStore.currentBase) return;
    await dashboardService.reorderDashboards(
      baseStore.currentBase.id,
      dashboardIds,
    );
    // 刷新仪表盘列表
    sidebarRef.value?.refreshDashboards();
  } catch (error) {
    ElMessage.error("排序失败");
  }
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
        await tableStore.loadTables(baseStore.currentBase!.id);
        await tableStore.selectTable(table.id);
      } else {
        ElMessage.error(tableStore.error || "创建失败");
      }
    }
  });
}

// 打开重命名对话框
function openRenameTableDialog(table: {
  id: string;
  name: string;
  description?: string;
}) {
  renameTableForm.id = table.id;
  renameTableForm.name = table.name;
  renameTableForm.description = table.description || "";
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
      try {
        // 使用通用操作模块
        await renameTable(
          {
            id: renameTableForm.id,
            name: renameTableForm.name,
            description: renameTableForm.description,
            isStarred: false,
          } as TableEntity,
          renameTableForm.name,
          renameTableForm.description,
        );
        // 同步更新 tableStore 中的表格信息
        const tableIndex = tableStore.tables.findIndex(
          (t) => t.id === renameTableForm.id,
        );
        if (tableIndex !== -1) {
          tableStore.tables[tableIndex].name = renameTableForm.name;
          tableStore.tables[tableIndex].description =
            renameTableForm.description;
        }
        if (tableStore.currentTable?.id === renameTableForm.id) {
          tableStore.currentTable.name = renameTableForm.name;
          tableStore.currentTable.description = renameTableForm.description;
        }
        closeRenameTableDialog();
      } catch (error) {
        // 错误已经在通用模块中处理
      }
    }
  });
}

// 处理删除表格
async function handleDeleteTable(table: { id: string; name: string }) {
  try {
    // 使用通用操作模块
    await deleteTable(table as TableEntity, async () => {
      // 刷新表格列表
      await refreshTables();
      if (tableStore.currentTable?.id === table.id) {
        tableStore.currentTable = null;
        tableStore.fields = [];
        tableStore.records = [];
        tableStore.views = [];
        // 如果有其他表格，选中第一个
        if (tableStore.tables.length > 0) {
          await tableStore.selectTable(tableStore.tables[0].id);
        }
      }
    });
  } catch (error) {
    // 错误已经在通用模块中处理
  }
}

// 处理收藏/取消收藏表格
async function handleToggleStarTable(table: {
  id: string;
  isStarred?: boolean;
}) {
  try {
    // 使用通用操作模块
    await toggleStarTable(table as TableEntity);
    // 刷新表格列表
    await refreshTables();
  } catch (error) {
    // 错误已经在通用模块中处理
  }
}

// 处理复制数据表
async function duplicateTable(table: { id: string; name: string }) {
  try {
    await tableService.duplicateTable(table.id);
    // 刷新表格列表
    await refreshTables();
    ElMessage.success("数据表复制成功");
  } catch (error: any) {
    console.error("复制数据表失败:", error);
    ElMessage.error("复制失败，请稍后重试");
  }
}

// 刷新数据表列表
async function refreshTables() {
  if (baseStore.currentBase) {
    tableStore.tables = await tableService.getTablesByBase(
      baseStore.currentBase.id,
    );
  }
}

// 打开字段对话框
function openFieldDialog() {
  if (!tableStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  fieldDialogVisible.value = true;
}

// 处理字段创建
function handleFieldCreated(field: any) {
  tableStore.fields.push(field);
  ElMessage.success(`字段 "${field.name}" 创建成功`);
}

// 处理字段更新
function handleFieldUpdated(field: any) {
  const index = tableStore.fields.findIndex((f) => f.id === field.id);
  if (index !== -1) {
    // 使用 Object.assign 保留响应式，并触发更新
    Object.assign(tableStore.fields[index], field);
  }
  ElMessage.success(`字段 "${field.name}" 更新成功`);
}

// 处理字段删除
function handleFieldDeleted(fieldId: string) {
  const index = tableStore.fields.findIndex((f) => f.id === fieldId);
  if (index !== -1) {
    const fieldName = tableStore.fields[index].name;
    tableStore.fields.splice(index, 1);
    ElMessage.success(`字段 "${fieldName}" 删除成功`);
  }
}

// 处理字段重排序
function handleFieldsReordered(fieldIds: string[]) {
  // 更新本地字段顺序
  const sortedFields = fieldIds
    .map((id) => tableStore.fields.find((f) => f.id === id))
    .filter((f): f is FieldEntity => f !== undefined);

  // 更新 order 属性
  sortedFields.forEach((field, index) => {
    field.order = index;
  });

  tableStore.fields = sortedFields;
}

// 处理字段可见性变化（视图级隐藏/显示）
async function handleFieldVisibilityChanged(
  fieldId: string,
  isVisible: boolean,
) {
  if (!viewStore.currentView) return;

  let newHiddenFields: string[];
  if (isVisible) {
    // 从隐藏列表中移除
    newHiddenFields = viewStore.currentView.hiddenFields.filter(
      (id) => id !== fieldId,
    );
  } else {
    // 添加到隐藏列表
    newHiddenFields = [...viewStore.currentView.hiddenFields, fieldId];
  }

  await viewStore.updateHiddenFields(viewStore.currentView.id, newHiddenFields);
}

// 打开筛选对话框
function openFilterDialog() {
  if (!tableStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  filterDialogVisible.value = true;
}

// 处理筛选应用
async function handleFilterApply(
  filters: FilterCondition[],
  conjunction: "and" | "or",
) {
  filterConjunction.value = conjunction;
  // 同步到后端数据库
  if (viewStore.currentView) {
    await viewStore.updateFilters(viewStore.currentView.id, filters);
  }
  if (filters.length > 0) {
    ElMessage.success(`已应用 ${filters.length} 个筛选条件`);
  }
}

// 处理筛选清除
async function handleFilterClear() {
  // 同步到后端数据库
  if (viewStore.currentView) {
    await viewStore.updateFilters(viewStore.currentView.id, []);
  }
  ElMessage.success("筛选已清除");
}

// 打开排序对话框
function openSortDialog() {
  if (!tableStore.currentTable) {
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
  if (!tableStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  exportDialogVisible.value = true;
}

// 打开导入对话框
function openImportDialog() {
  if (!tableStore.currentTable) {
    ElMessage.warning("请先选择一个数据表");
    return;
  }
  importDialogVisible.value = true;
}

// 打开Excel导入创建对话框
function openExcelImportCreateDialog() {
  if (!baseStore.currentBase) {
    ElMessage.warning("请先选择一个Base");
    return;
  }
  excelImportCreateDialogVisible.value = true;
}

// 处理Excel导入创建完成
async function handleExcelImportCreated(tableId: string) {
  // 刷新表格列表
  if (baseStore.currentBase) {
    await tableStore.loadTables(baseStore.currentBase.id);
    // 自动选中新创建的表格
    await tableStore.selectTable(tableId);
    // 加载视图
    await viewStore.loadViews(tableId);
    await viewStore.selectDefaultView(tableId);
  }
}

// 处理导入完成
function handleImported() {
  // 刷新数据
  if (tableStore.currentTable) {
    tableStore.selectTable(tableStore.currentTable.id);
  }
}

// 处理成员变更
function handleMemberChanged() {
  console.log("成员发生变更，刷新相关数据");
  // TODO: 刷新 Base 成员列表和权限
}

// 处理分享变更
function handleShareChanged() {
  console.log("分享发生变更，刷新相关数据");
  // TODO: 刷新 Base 分享列表
}
</script>

<template>
  <div class="base-page">
    <BaseSidebar
      ref="sidebarRef"
      :current-table-id="tableStore.currentTable?.id"
      :show-tables="true"
      :show-dashboards="true"
      :can-edit="canEdit"
      @select-table="handleTableSelect"
      @select-dashboard="handleDashboardClick"
      @add-table="openCreateTableDialog"
      @add-dashboard="openCreateDashboardDialog"
      @excel-import-create="openExcelImportCreateDialog"
      @rename-table="openRenameTableDialog"
      @delete-table="handleDeleteTable"
      @toggle-star="handleToggleStarTable"
      @rename-dashboard="openRenameDashboardDialog"
      @delete-dashboard="handleDeleteDashboard"
      @toggle-star-dashboard="handleToggleStarDashboard"
      @reorder-dashboards="handleReorderDashboards"
      @manage-tables="showTableManager = true" />

    <!-- 仪表盘视图 -->
    <template v-if="route.path.includes('/dashboard/')">
      <div class="dashboard-container">
        <DashboardView :dashboard-id="route.params.dashboardId as string" />
      </div>
    </template>
    <!-- 数据表视图 -->
    <main v-else class="main-content">
      <Loading v-if="isLoading" />
      <template v-else-if="tableStore.currentTable">
        <div class="table-container">
          <ViewSwitcher
            :table-id="currentTableId"
            :readonly="!canEdit"
            @view-change="handleViewChange" />

          <header
            class="table-header"
            :class="{
              'gantt-header': isGanttView,
              'kanban-header': isKanbanView,
              'calendar-header': isCalendarView,
              'gallery-header': isGalleryView,
            }">
            <div
              v-if="
                !isGanttView &&
                !isKanbanView &&
                !isCalendarView &&
                !isGalleryView
              "
              class="table-info">
              <ConnectionStatusBar v-if="collaborationStore.isRealtimeAvailable" />
              <OnlineUsers v-if="collaborationStore.isRealtimeAvailable" />
            </div>
            <div
              class="table-actions"
              :class="{ 'gantt-actions': isGanttView }">
              <!-- 表格视图：显示所有常规操作按钮 -->
              <template v-if="isTableView">
                <el-button-group>
                  <el-button
                    size="medium"
                    :type="activeFilters.length > 0 ? 'primary' : 'default'"
                    @click="openFilterDialog">
                    <el-icon><Filter /></el-icon>
                    筛选
                    <el-tag
                      v-if="activeFilters.length > 0"
                      size="medium"
                      class="filter-badge">
                      {{ activeFilters.length }}
                    </el-tag>
                  </el-button>
                  <el-button
                    size="medium"
                    :type="activeSorts.length > 0 ? 'primary' : 'default'"
                    @click="openSortDialog">
                    <el-icon><Sort /></el-icon>
                    排序
                    <el-tag
                      v-if="activeSorts.length > 0"
                      size="medium"
                      class="sort-badge">
                      {{ activeSorts.length }}
                    </el-tag>
                  </el-button>
                  <el-button
                    size="medium"
                    :type="hasGroupConfig ? 'primary' : 'default'"
                    @click="openGroupDialog">
                    <el-icon><Folder /></el-icon>
                    分组
                    <el-tag
                      v-if="hasGroupConfig"
                      size="medium"
                      class="group-badge">
                      {{ currentGroupBys.length }}
                    </el-tag>
                  </el-button>
                  <el-button
                    v-if="canEdit"
                    size="medium"
                    @click="openFieldDialog">
                    <el-icon><Grid /></el-icon>
                    字段
                  </el-button>
                </el-button-group>
                <el-button
                  v-if="canEdit"
                  size="medium"
                  @click="openImportDialog">
                  <el-icon><Upload /></el-icon>
                  导入
                </el-button>
                <el-button size="medium" @click="openExportDialog">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </template>

              <!-- 表单视图：显示配置和分享按钮 -->
              <template v-if="isFormView">
                <el-button-group>
                  <el-button
                    v-if="canManage"
                    size="medium"
                    @click="openFormConfigDialog">
                    <el-icon><Setting /></el-icon>
                    配置
                  </el-button>
                  <el-button
                    v-if="canManage"
                    size="medium"
                    @click="openFormShareDialog">
                    <el-icon><Share /></el-icon>
                    分享
                  </el-button>
                </el-button-group>
              </template>
            </div>
          </header>

          <div class="table-content">
            <!-- 表格视图 - 分组模式 -->
            <GroupedTableView
              v-if="isTableView && hasGroupConfig"
              :fields="visibleFields"
              :records="filteredRecords as any[]"
              :group-by="currentGroupBys"
              :frozen-fields="viewStore.currentView?.frozenFields || []"
              :readonly="!canEdit"
              @row-click="handleRecordSelect"
              @cell-click="handleEditRecord"
              @add-record="handleAddRecordFromGroup"
              @expand-record="handleExpandRecord"
              @duplicate-record="handleDuplicateRecordFromGroup"
              @delete-records="handleDeleteRecordsFromGroup"
              @sort="handleSortFromGroup"
              @freeze-field="handleFreezeFieldFromGroup"
              @unfreeze-field="handleUnfreezeFieldFromGroup"
              @hide-field="handleHideFieldFromGroup"
              @edit-field="handleEditFieldFromGroup" />

            <!-- 表格视图 - 普通模式 -->
            <TableView
              v-else-if="isTableView"
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              :readonly="!canEdit"
              @record-select="handleRecordSelect"
              @records-select="handleRecordsSelect"
              @add-record="handleAddRecord" />

            <!-- 看板视图 -->
            <KanbanView
              v-else-if="isKanbanView"
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              :fields="visibleFields"
              :readonly="!canEdit"
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
              :fields="visibleFields"
              :readonly="!canEdit"
              @record-select="handleRecordSelect"
              @addRecord="handleAddRecord"
              @editRecord="handleEditRecordById" />

            <!-- 甘特视图 -->
            <GanttView
              v-else-if="isGanttView"
              :table-id="currentTableId"
              :view-id="viewStore.currentView?.id || ''"
              :records="filteredRecords"
              :fields="visibleFields"
              :readonly="!canEdit"
              @updateRecord="handleSaveRecord"
              @addRecord="handleAddRecord"
              @editRecord="handleEditRecordById"
              @deleteRecord="handleDeleteRecord" />

            <!-- 画册视图 -->
            <GalleryView
              v-else-if="isGalleryView"
              :records="filteredRecords"
              :fields="visibleFields"
              :readonly="!canEdit"
              @editRecord="handleEditRecordById"
              @deleteRecord="handleDeleteRecord" />

            <!-- 表单视图 -->
            <FormView
              v-else-if="isFormView"
              :fields="tableStore.fields"
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

          <!-- 底部统计信息栏 -->
          <div
            v-if="
              !isGanttView &&
              !isKanbanView &&
              !isCalendarView &&
              !isGalleryView &&
              !isFormView
            "
            class="table-footer-stats">
            <span class="record-count">
              {{ filteredRecords.length }} 条记录
            </span>
            <span v-if="activeFilters.length > 0" class="filter-badge">
              <el-tag size="small" type="warning">筛选: {{ activeFilters.length }}</el-tag>
            </span>
            <span v-if="activeSorts.length > 0" class="sort-badge">
              <el-tag size="small" type="success">排序: {{ activeSorts.length }}</el-tag>
            </span>
            <span v-if="hasGroupConfig" class="group-badge">
              <el-tag size="small" type="primary">分组: {{ currentGroupBys.length }}</el-tag>
            </span>
          </div>
        </div>
      </template>
      <div v-else class="empty-state">
        <el-empty description="请选择或创建一个数据表">
          <el-button
            v-if="canEdit"
            type="primary"
            @click="openCreateTableDialog"
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

    <!-- 创建仪表盘对话框 -->
    <el-dialog
      v-model="createDashboardDialogVisible"
      title="创建仪表盘"
      width="500px"
      :close-on-click-modal="false">
      <el-form
        ref="createDashboardFormRef"
        :model="createDashboardForm"
        :rules="createDashboardFormRules"
        label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="createDashboardForm.name"
            placeholder="请输入仪表盘名称"
            maxlength="50"
            show-word-limit />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="createDashboardForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeCreateDashboardDialog">取消</el-button>
          <el-button type="primary" @click="handleCreateDashboard"
            >确定</el-button
          >
        </span>
      </template>
    </el-dialog>

    <!-- 重命名数据表对话框 -->
    <el-dialog
      v-model="renameTableDialogVisible"
      title="编辑数据表"
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
        <el-form-item label="描述">
          <el-input
            v-model="renameTableForm.description"
            placeholder="请输入数据表描述"
            maxlength="200"
            show-word-limit
            type="textarea"
            :rows="3" />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeRenameTableDialog">取消</el-button>
          <el-button type="primary" @click="handleRenameTable">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 数据表管理对话框 -->
    <el-dialog
      v-model="showTableManager"
      title="数据表管理"
      width="680px"
      destroy-on-close
      class="table-manager-dialog">
      <div class="table-manager">
        <div class="manager-header">
          <el-button
            type="primary"
            class="create-btn"
            @click="
              openCreateTableDialog();
              showTableManager = false;
            ">
            <el-icon><Plus /></el-icon>
            新建数据表
          </el-button>
        </div>

        <el-table
          :data="tableStore.tables"
          style="width: 100%"
          class="manager-table">
          <el-table-column prop="name" label="名称" min-width="160">
            <template #default="{ row }">
              <div class="table-name-cell">
                <div class="table-icon">
                  <el-icon><Document /></el-icon>
                </div>
                <span>{{ row.name }}</span>
                <el-tag
                  v-if="row.id === tableStore.currentTable?.id"
                  size="small"
                  type="primary"
                  effect="light"
                  >当前</el-tag
                >
                <el-tag
                  v-if="row.isStarred"
                  size="small"
                  type="warning"
                  effect="plain"
                  class="star-tag"
                  >已收藏</el-tag
                >
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="description"
            label="描述"
            min-width="180"
            show-overflow-tooltip />
          <el-table-column prop="updatedAt" label="更新时间" width="140">
            <template #default="{ row }">
              {{ new Date(row.updatedAt).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                @click="
                  handleTableSelect(row.id);
                  showTableManager = false;
                ">
                打开
              </el-button>
              <el-button link @click="openRenameTableDialog(row)"
                >编辑</el-button
              >
              <el-button link @click="duplicateTable(row)">复制</el-button>
              <el-button link type="danger" @click="handleDeleteTable(row)"
                >删除</el-button
              >
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 字段管理对话框 -->
    <FieldDialog
      v-model:visible="fieldDialogVisible"
      :table-id="currentTableId"
      :fields="tableStore.fields"
      :edit-field-id="editingFieldId || undefined"
      @field-created="handleFieldCreated"
      @field-updated="handleFieldUpdated"
      @field-deleted="handleFieldDeleted"
      @fields-reordered="handleFieldsReordered"
      @field-visibility-changed="handleFieldVisibilityChanged"
      @update:visible="
        (val) => {
          if (!val) editingFieldId = null;
        }
      " />

    <!-- 筛选对话框 -->
    <FilterDialog
      v-model:visible="filterDialogVisible"
      :fields="visibleFields"
      :initial-filters="activeFilters"
      :initial-conjunction="filterConjunction"
      @apply="handleFilterApply"
      @clear="handleFilterClear" />

    <!-- 排序对话框 -->
    <SortDialog
      v-model:visible="sortDialogVisible"
      :fields="visibleFields"
      :initial-sorts="activeSorts"
      @apply="handleSortApply"
      @clear="handleSortClear" />

    <!-- 分组对话框 -->
    <GroupDialog
      v-model:visible="groupDialogVisible"
      :fields="visibleFields"
      :initial-group-by="currentGroupBys"
      @apply="handleGroupApply"
      @clear="handleGroupClear" />

    <!-- 导出对话框 -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      :fields="visibleFields"
      :records="filteredRecords" />

    <!-- 记录编辑对话框 -->
    <RecordDetailDrawer
      v-model:visible="recordDialogVisible"
      :record="editingRecord"
      :fields="tableStore.fields"
      :size="drawerSize"
      :readonly="!canEdit"
      @save="handleSaveRecord" />

    <!-- 添加记录抽屉 -->
    <AddRecordDrawer
      v-model:visible="addRecordDialogVisible"
      :fields="tableStore.fields"
      :initial-values="addRecordInitialValues"
      :group-field-id="addRecordGroupInfo.groupFieldId"
      :group-id="addRecordGroupInfo.groupId"
      :group-name="addRecordGroupInfo.groupName"
      :group-levels="addRecordGroupInfo.groupLevels"
      :size="drawerSize"
      @save="handleSaveNewRecord" />

    <!-- 表单配置对话框 -->
    <FormViewConfig
      v-model:visible="formConfigDialogVisible"
      :fields="tableStore.fields"
      :initial-config="formConfig"
      @save="handleFormConfigSave" />

    <!-- 表单分享对话框 -->
    <FormShareDialog
      v-model:visible="formShareDialogVisible"
      :fields="tableStore.fields"
      :table-name="tableStore.currentTable?.name"
      :table-id="tableStore.currentTable?.id"
      :view-id="viewStore.currentView?.id"
      :form-config="formConfig" />

    <!-- 数据导入对话框 -->
    <ImportDialog
      v-model:visible="importDialogVisible"
      :table-id="tableStore.currentTable?.id || ''"
      :fields="tableStore.fields"
      @imported="handleImported" />

    <!-- Excel导入创建数据表对话框 -->
    <ExcelImportCreateDialog
      v-model:visible="excelImportCreateDialogVisible"
      :base-id="baseStore.currentBase?.id || ''"
      @created="handleExcelImportCreated" />

    <!-- 成员管理对话框 -->
    <MemberManagementDialog
      v-model:visible="showMemberManagement"
      :base-id="baseStore.currentBase?.id || ''"
      @member-changed="handleMemberChanged" />

    <!-- Base 分享对话框 -->
    <BaseShareDialog
      v-model:visible="showBaseShare"
      :base-id="baseStore.currentBase?.id || ''"
      @share-changed="handleShareChanged" />

    <!-- 重命名仪表盘对话框 -->
    <el-dialog
      v-model="renameDashboardDialogVisible"
      title="编辑仪表盘"
      width="500px"
      :close-on-click-modal="false">
      <el-form
        ref="renameDashboardFormRef"
        :model="renameDashboardForm"
        :rules="renameDashboardFormRules"
        label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="renameDashboardForm.name"
            placeholder="请输入仪表盘名称"
            maxlength="50"
            show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="renameDashboardForm.description"
            placeholder="请输入仪表盘描述"
            maxlength="200"
            show-word-limit
            type="textarea"
            :rows="3" />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeRenameDashboardDialog">取消</el-button>
          <el-button type="primary" @click="handleRenameDashboard"
            >确定</el-button
          >
        </span>
      </template>
    </el-dialog>
    <CollaborationToast v-if="collaborationStore.isRealtimeAvailable" />
    <ConflictDialog
      v-if="collaborationStore.isRealtimeAvailable && realtimeCollab"
      :visible="realtimeCollab.conflictVisible.value"
      :conflict="realtimeCollab.currentConflict.value"
      @resolve="realtimeCollab.resolveConflict"
    />
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.base-page {
  display: flex;
  height: calc(100vh - 56px);
  background-color: $gray-50;
}

.sidebar {
  width: $sidebar-width;
  display: flex;
  flex-direction: column;
  border-right: 1px solid $gray-200;
  background: $surface-color;
  transition: width $transition-normal;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: $shadow-md;

  &.collapsed {
    width: $sidebar-collapsed-width;

    .sidebar-header {
      justify-content: center;
      padding: $spacing-md $spacing-sm;

      .header-content {
        display: none;
      }
    }

    .section-title,
    .section-divider {
      display: none;
    }

    .dashboard-list {
      padding: $spacing-sm 0;
    }

    .dashboard-item {
      justify-content: center;
      padding: $spacing-md $spacing-sm;
      gap: 0;

      .dashboard-name {
        display: none;
      }

      .dashboard-icon {
        margin: 0;
      }
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
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-color;
  min-height: 56px;
  gap: $spacing-sm;

  .header-content {
    flex: 1;
    min-width: 0;

    :deep(.el-input) {
      width: 100%;
    }
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

.section-title {
  padding: $spacing-sm $spacing-lg;
  font-size: $font-size-xs;
  color: $text-secondary;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-divider {
  height: 1px;
  background-color: $border-color;
  margin: $spacing-sm $spacing-lg;
}

.dashboard-section {
  flex-shrink: 0;
}

.dashboard-list {
  padding: $spacing-sm 0;
}

.dashboard-item {
  display: flex;
  align-items: center;
  padding: $spacing-sm $spacing-lg;
  cursor: pointer;
  transition: all $transition-fast;
  gap: $spacing-sm;

  &:hover {
    background-color: $bg-color;
  }
}

.dashboard-icon {
  color: $text-secondary;
  flex-shrink: 0;
}

.dashboard-name {
  flex: 1;
  font-size: $font-size-sm;
  color: $text-primary;
  @include text-ellipsis;
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
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;

  .el-button {
    width: 100%;
    justify-content: flex-start;
  }
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dashboard-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $surface-color;
  border-radius: $border-radius-xl;
  margin-right: $spacing-xs;
  box-shadow: $shadow-card;
  overflow: hidden;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-sm $spacing-xl;
  background: $surface-color;
  border-bottom: 1px solid $gray-200;
  gap: $spacing-lg;
}

.table-header.gantt-header,
.table-header.kanban-header,
.table-header.calendar-header,
.table-header.gallery-header {
  padding: 0;
  min-height: 0;
  height: auto;
  border-bottom: none;
}

.table-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  flex-wrap: wrap;

  h2 {
    margin: 0;
    font-size: $font-size-lg;
    font-weight: 600;
    color: $text-primary;
    letter-spacing: -0.2px;
  }

  .record-count {
    font-size: $font-size-sm;
    color: $text-secondary;
    background-color: $gray-100;
    padding: $spacing-xs $spacing-sm;
    border-radius: $border-radius-md;
  }

  .filter-badge,
  .sort-badge,
  .group-badge {
    margin-left: $spacing-xs;

    :deep(.el-tag) {
      border-radius: $border-radius-md;
      font-weight: 500;
    }
  }
}

.table-actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-wrap: wrap;

  &.gantt-actions {
    flex: 1;
    justify-content: flex-start;
  }

  // 按钮组样式优化
  :deep(.el-button-group) {
    .el-button {
      border-radius: 0;

      &:first-child {
        border-top-left-radius: $border-radius-md;
        border-bottom-left-radius: $border-radius-md;
      }

      &:last-child {
        border-top-right-radius: $border-radius-md;
        border-bottom-right-radius: $border-radius-md;
      }

      &:hover {
        transform: translateY(-1px);
      }

      &:active {
        transform: translateY(0);
      }
    }
  }

  // 主要操作按钮样式
  :deep(.el-button--primary) {
    @include gradient-primary;
    border: none;
    border-radius: $border-radius-md;
    font-weight: 500;
    @include button-fresh;

    &:hover {
      box-shadow:
        $shadow-button,
        0 4px 8px rgba($primary-color, 0.3);
    }

    &:active {
      box-shadow: $shadow-button;
    }
  }

  // 默认按钮样式
  :deep(.el-button--default) {
    border-radius: $border-radius-md;
    transition: all $transition-fast;

    &:hover {
      background-color: $gray-100;
      border-color: $gray-300;
      transform: translateY(-1px);
      box-shadow: $shadow-sm;
    }

    &:active {
      transform: translateY(0);
    }
  }

  // 按钮内标签样式
  :deep(.el-button) {
    .el-tag {
      margin-left: $spacing-xs;
      border-radius: $border-radius-sm;
    }
  }
}

.table-content {
  flex: 1;
  overflow-y: auto;
}

// 底部统计信息栏
.table-footer-stats {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm $spacing-xl;
  background: $surface-color;
  border-top: 1px solid $gray-200;
  font-size: $font-size-sm;

  .record-count {
    color: $text-secondary;
    background-color: $gray-100;
    padding: $spacing-xs $spacing-sm;
    border-radius: $border-radius-md;
  }

  .filter-badge,
  .sort-badge,
  .group-badge {
    :deep(.el-tag) {
      border-radius: $border-radius-md;
      font-weight: 500;
    }
  }
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: $spacing-xl;

  :deep(.el-empty) {
    padding: $spacing-2xl;
    background-color: $surface-color;
    border-radius: $border-radius-xl;
    box-shadow: $shadow-card;
  }

  :deep(.el-button--primary) {
    @include gradient-primary;
    border: none;
    border-radius: $border-radius-md;
    font-weight: 500;
    @include button-fresh;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.delete-item) {
  color: $error-color;
}

// 数据表管理对话框样式
.table-manager-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 24px 16px;
    border-bottom: 1px solid $gray-100;

    .el-dialog__title {
      font-size: 17px;
      font-weight: 600;
      color: $gray-800;
    }
  }

  :deep(.el-dialog__body) {
    padding: 20px 24px;
  }
}

.table-manager {
  .manager-header {
    margin-bottom: 20px;

    .create-btn {
      padding: 0 16px;
      border-radius: 10px;
      font-weight: 500;
      background: linear-gradient(135deg, $primary-color 0%, #6366f1 100%);
      border: none;
      box-shadow: 0 4px 14px rgba($primary-color, 0.35);
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba($primary-color, 0.45);
      }

      .el-icon {
        margin-right: 6px;
      }
    }
  }
}

.manager-table {
  :deep(th) {
    font-weight: 600;
    color: $gray-600;
    background: $gray-50;
  }

  :deep(td) {
    padding: 12px 0;
  }
}

.table-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;

  .table-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $primary-light;
    border-radius: 8px;
    color: $primary-color;
  }

  .el-tag {
    margin-left: 6px;
  }

  .star-tag {
    color: #f7ba2a;
    border-color: #f7ba2a;
  }
}
</style>
