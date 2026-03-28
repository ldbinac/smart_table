<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBaseStore } from "@/stores";
import {
  dashboardService,
  type WidgetConfig,
} from "@/db/services/dashboardService";
import {
  dashboardShareService,
  type DashboardShare,
} from "@/db/services/dashboardShareService";
import { recordService } from "@/db/services/recordService";
import { fieldService } from "@/db/services/fieldService";
import { tableService } from "@/db/services/tableService";
import type {
  RecordEntity,
  FieldEntity,
  TableEntity,
  Dashboard,
} from "@/db/schema";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import {
  processChartData,
  getChartColors,
  formatLargeNumber,
  validateAggregation,
  getFieldValueDisplay,
  getOptionInfo,
} from "@/utils/dashboardDataProcessor";
import { FieldType } from "@/types";
import { ElMessage, ElMessageBox } from "element-plus";
import BaseSidebar from "@/components/common/BaseSidebar.vue";

const baseStore = useBaseStore();
const route = useRoute();
const router = useRouter();

// 仪表盘状态
const dashboards = ref<Dashboard[]>([]);
const currentDashboard = ref<Dashboard | null>(null);
const showDashboardManager = ref(false);
const isEditingDashboard = ref(false);
const isCreatingDashboard = ref(false); // 区分新建/编辑模式
const dashboardForm = ref({
  name: "",
  description: "",
});

// 加载状态
const isLoading = ref(false);
const loadingText = ref("加载中...");

// 数据状态
const tables = ref<TableEntity[]>([]);
const fields = ref<FieldEntity[]>([]);
const records = ref<RecordEntity[]>([]);
const widgets = ref<WidgetConfig[]>([]);
const selectedWidget = ref<WidgetConfig | null>(null);
const chartRefs = ref<Map<string, echarts.ECharts>>(new Map());
const chartContainers = ref<Map<string, HTMLElement>>(new Map());

// 拖拽调整大小状态
const resizingWidget = ref<string | null>(null);
const resizeStart = ref({ x: 0, y: 0, w: 0, h: 0 });

// 分享功能状态
const showShareDialog = ref(false);
const shareForm = ref({
  expiresInHours: 168, // 默认7天
  maxAccessCount: undefined as number | undefined,
  requireAccessCode: false,
  permission: "view" as "view" | "edit",
});
const currentShare = ref<DashboardShare | null>(null);
const shareUrl = ref("");
const isCreatingShare = ref(false);
const existingShares = ref<DashboardShare[]>([]);

// 组件类型定义
const widgetTypes = [
  {
    value: "bar",
    label: "柱状图",
    icon: "BarChart",
    description: "展示分类数据的对比",
  },
  {
    value: "line",
    label: "折线图",
    icon: "TrendCharts",
    description: "展示数据随时间的变化趋势",
  },
  {
    value: "area",
    label: "面积图",
    icon: "Histogram",
    description: "强调数量随时间变化的程度",
  },
  {
    value: "pie",
    label: "饼图",
    icon: "PieChart",
    description: "展示各部分占整体的比例",
  },
  {
    value: "scatter",
    label: "散点图",
    icon: "CircleCheck",
    description: "展示两个变量之间的关系",
  },
  {
    value: "number",
    label: "数字卡片",
    icon: "DataAnalysis",
    description: "突出显示关键指标",
  },
  {
    value: "table",
    label: "数据表格",
    icon: "Grid",
    description: "以表格形式展示详细数据",
  },
];

const aggregationTypes = [
  { value: "count", label: "计数", description: "统计记录数量" },
  {
    value: "countDistinct",
    label: "去重计数",
    description: "统计不重复值的数量",
  },
  { value: "sum", label: "求和", description: "对数值字段求和" },
  { value: "avg", label: "平均值", description: "计算数值字段的平均值" },
  { value: "max", label: "最大值", description: "获取数值字段的最大值" },
  { value: "min", label: "最小值", description: "获取数值字段的最小值" },
];

// 计算属性
const canUseNumericAggregation = computed(() => {
  if (!selectedWidget.value?.fieldId) return false;
  const field = fields.value.find(
    (f) => f.id === selectedWidget.value!.fieldId,
  );
  if (!field) return false;
  const numericTypes = [
    FieldType.NUMBER,
    FieldType.RATING,
    FieldType.PROGRESS,
    FieldType.AUTO_NUMBER,
  ];
  return numericTypes.includes(field.type);
});

const filteredAggregationTypes = computed(() => {
  if (!selectedWidget.value?.fieldId)
    return aggregationTypes.filter((a) =>
      ["count", "countDistinct"].includes(a.value),
    );
  const field = fields.value.find(
    (f) => f.id === selectedWidget.value!.fieldId,
  );
  if (!field)
    return aggregationTypes.filter((a) =>
      ["count", "countDistinct"].includes(a.value),
    );

  const numericTypes = [
    FieldType.NUMBER,
    FieldType.RATING,
    FieldType.PROGRESS,
    FieldType.AUTO_NUMBER,
  ];
  if (numericTypes.includes(field.type)) {
    return aggregationTypes;
  }
  return aggregationTypes.filter((a) =>
    ["count", "countDistinct"].includes(a.value),
  );
});

// 加载仪表盘列表
async function loadDashboards() {
  const baseId = route.params.id as string;
  if (!baseId) {
    console.warn("No baseId found in route params");
    return;
  }

  isLoading.value = true;
  loadingText.value = "加载基地信息...";

  try {
    // 如果 baseStore 中没有当前 base，先加载
    if (!baseStore.currentBase || baseStore.currentBase.id !== baseId) {
      await baseStore.loadBase(baseId);
    }

    if (!baseStore.currentBase) {
      console.warn("Failed to load base");
      ElMessage.error("加载基地信息失败");
      return;
    }

    loadingText.value = "加载仪表盘列表...";
    dashboards.value = await dashboardService.getDashboardsByBase(baseId);

    // 如果有路由参数指定了仪表盘ID，选中该仪表盘
    const dashboardIdFromRoute = route.params.dashboardId as string;
    if (dashboardIdFromRoute) {
      const targetDashboard = dashboards.value.find(
        (d) => d.id === dashboardIdFromRoute,
      );
      if (targetDashboard) {
        await selectDashboard(targetDashboard);
        return;
      }
    }

    // 如果有仪表盘，默认选中第一个
    if (dashboards.value.length > 0 && !currentDashboard.value) {
      await selectDashboard(dashboards.value[0]);
    }
  } catch (error) {
    console.error("加载仪表盘失败:", error);
    ElMessage.error("加载数据失败，请刷新页面重试");
  } finally {
    isLoading.value = false;
  }
}

// 选择仪表盘
async function selectDashboard(dashboard: Dashboard) {
  currentDashboard.value = dashboard;
  widgets.value = (dashboard.widgets || []) as WidgetConfig[];

  // 加载所有相关表的数据
  const tableIds = [...new Set(widgets.value.map((w) => w.tableId))];
  for (const tableId of tableIds) {
    await loadTableData(tableId);
  }

  // 渲染所有组件
  nextTick(() => {
    widgets.value.forEach((widget) => renderWidget(widget));
  });
}

// 创建仪表盘
async function createDashboard() {
  if (!baseStore.currentBase) {
    ElMessage.error("当前未选择基地");
    return;
  }

  if (!dashboardForm.value.name.trim()) {
    ElMessage.warning("请输入仪表盘名称");
    return;
  }

  try {
    const dashboard = await dashboardService.createDashboard({
      baseId: baseStore.currentBase.id,
      name: dashboardForm.value.name.trim(),
      description: dashboardForm.value.description,
      widgets: [],
    });

    dashboards.value.push(dashboard);
    currentDashboard.value = dashboard;
    widgets.value = [];
    isEditingDashboard.value = false;
    isCreatingDashboard.value = false;
    dashboardForm.value = { name: "", description: "" };

    ElMessage.success("仪表盘创建成功");
  } catch (error) {
    console.error("创建仪表盘失败:", error);
    ElMessage.error("创建仪表盘失败，请重试");
  }
}

// 更新仪表盘
async function updateDashboard() {
  if (!currentDashboard.value) {
    ElMessage.error("当前未选择仪表盘");
    return;
  }

  if (!dashboardForm.value.name.trim()) {
    ElMessage.warning("请输入仪表盘名称");
    return;
  }

  try {
    await dashboardService.updateDashboard(currentDashboard.value.id, {
      name: dashboardForm.value.name.trim(),
      description: dashboardForm.value.description,
    });

    currentDashboard.value.name = dashboardForm.value.name;
    currentDashboard.value.description = dashboardForm.value.description;

    // 刷新列表
    await loadDashboards();

    isEditingDashboard.value = false;
    isCreatingDashboard.value = false;
    ElMessage.success("仪表盘更新成功");
  } catch (error) {
    console.error("更新仪表盘失败:", error);
    ElMessage.error("更新仪表盘失败，请重试");
  }
}

// 删除仪表盘
async function deleteDashboard(dashboard: Dashboard) {
  try {
    await ElMessageBox.confirm(
      `确定要删除仪表盘 "${dashboard.name}" 吗？`,
      "确认删除",
      { type: "warning" },
    );

    await dashboardService.deleteDashboard(dashboard.id);
    dashboards.value = dashboards.value.filter((d) => d.id !== dashboard.id);

    if (currentDashboard.value?.id === dashboard.id) {
      currentDashboard.value = dashboards.value[0] || null;
      if (currentDashboard.value) {
        await selectDashboard(currentDashboard.value);
      } else {
        widgets.value = [];
      }
    }

    ElMessage.success("仪表盘已删除");
  } catch {
    // 用户取消
  }
}

// 复制仪表盘
async function duplicateDashboard(dashboard: Dashboard) {
  const duplicated = await dashboardService.duplicateDashboard(dashboard.id);
  dashboards.value.push(duplicated);
  await selectDashboard(duplicated);
  ElMessage.success("仪表盘复制成功");
}

// 保存状态
const isSaving = ref(false);
const saveTimeout = ref<number | null>(null);
const hasUnsavedChanges = ref(false);

// 保存组件配置（带防抖）
async function saveWidgets(showMessage = true) {
  if (!currentDashboard.value) {
    if (showMessage) {
      ElMessage.warning("请先创建或选择一个仪表盘");
    }
    return;
  }

  // 清除之前的定时器
  if (saveTimeout.value) {
    clearTimeout(saveTimeout.value);
    saveTimeout.value = null;
  }

  isSaving.value = true;
  hasUnsavedChanges.value = true;

  try {
    // 将响应式对象转换为普通对象，避免 DataCloneError
    const plainWidgets = JSON.parse(JSON.stringify(widgets.value));
    await dashboardService.updateDashboardWidgets(
      currentDashboard.value.id,
      plainWidgets,
    );
    hasUnsavedChanges.value = false;
    if (showMessage) {
      ElMessage.success("保存成功");
    }
  } catch (error) {
    console.error("保存失败:", error);
    if (showMessage) {
      ElMessage.error("保存失败，请重试");
    }
  } finally {
    isSaving.value = false;
  }
}

// 防抖保存（用于自动保存）
function debouncedSaveWidgets(delay = 1000) {
  if (saveTimeout.value) {
    clearTimeout(saveTimeout.value);
  }
  hasUnsavedChanges.value = true;
  saveTimeout.value = window.setTimeout(() => {
    saveWidgets(false);
  }, delay);
}

// ==================== 分享功能 ====================

// 打开分享对话框
async function openShareDialog() {
  if (!currentDashboard.value) {
    ElMessage.warning("请先选择仪表盘");
    return;
  }

  showShareDialog.value = true;
  currentShare.value = null;
  shareUrl.value = "";

  // 加载已有的分享链接
  await loadExistingShares();
}

// 加载已有的分享链接
async function loadExistingShares() {
  if (!currentDashboard.value) return;
  existingShares.value = await dashboardShareService.getSharesByDashboard(
    currentDashboard.value.id,
  );
}

// 创建分享链接
async function createShare() {
  if (!currentDashboard.value) return;

  isCreatingShare.value = true;
  try {
    const share = await dashboardShareService.createShare({
      dashboardId: currentDashboard.value.id,
      expiresInHours: shareForm.value.expiresInHours || undefined,
      maxAccessCount: shareForm.value.maxAccessCount || undefined,
      requireAccessCode: shareForm.value.requireAccessCode,
      permission: shareForm.value.permission,
    });

    currentShare.value = share;
    shareUrl.value = dashboardShareService.generateShareUrl(share.shareToken);

    // 刷新分享列表
    await loadExistingShares();

    ElMessage.success("分享链接创建成功");
  } catch (error) {
    console.error("创建分享链接失败:", error);
    ElMessage.error("创建分享链接失败");
  } finally {
    isCreatingShare.value = false;
  }
}

// 复制分享链接
async function copyShareUrl() {
  if (!shareUrl.value) return;

  const success = await dashboardShareService.copyToClipboard(shareUrl.value);
  if (success) {
    ElMessage.success("链接已复制到剪贴板");
  } else {
    ElMessage.error("复制失败，请手动复制");
  }
}

// 通过token复制分享链接
async function copyShareUrlByToken(token: string) {
  const url = dashboardShareService.generateShareUrl(token);
  const success = await dashboardShareService.copyToClipboard(url);
  if (success) {
    ElMessage.success("链接已复制到剪贴板");
  } else {
    ElMessage.error("复制失败，请手动复制");
  }
}

// 复制访问密码
async function copyAccessCode() {
  if (!currentShare.value?.accessCode) return;

  const success = await dashboardShareService.copyToClipboard(
    currentShare.value.accessCode,
  );
  if (success) {
    ElMessage.success("访问密码已复制到剪贴板");
  } else {
    ElMessage.error("复制失败，请手动复制");
  }
}

// 处理选择数据表
const handleTableSelect = (tableId: string) => {
  const baseId = route.params.id as string;
  router.push(`/base/${baseId}`);
  // 可以在这里添加选择数据表的逻辑
};

// 处理选择仪表盘
const handleDashboardSelect = (dashboardId: string) => {
  const baseId = route.params.id as string;
  router.push(`/base/${baseId}/dashboard/${dashboardId}`);
};

// 处理打开创建数据表对话框
const openCreateTableDialog = () => {
  // 可以在这里添加打开创建数据表对话框的逻辑
  // 或者导航到Base页面
  const baseId = route.params.id as string;
  router.push(`/base/${baseId}`);
};

// 处理打开创建仪表盘对话框
const openCreateDashboardDialog = () => {
  isEditingDashboard.value = true;
  isCreatingDashboard.value = true;
  dashboardForm.value = { name: "", description: "" };
};

// 处理重命名数据表
const handleRenameTable = async (table: { id: string; name: string }) => {
  try {
    const { value } = await ElMessageBox.prompt(
      "请输入新的数据表名称",
      "重命名数据表",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        inputValue: table.name,
        inputValidator: (value) => {
          if (!value || value.trim() === "") {
            return "名称不能为空";
          }
          if (value.length > 50) {
            return "名称长度不能超过50个字符";
          }
          return true;
        },
      },
    );

    if (value && value.trim() !== table.name) {
      await tableService.updateTable(table.id, {
        name: value.trim(),
      });
      ElMessage.success("数据表重命名成功");
      // 刷新数据表列表
      await loadTables();
    }
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("重命名失败");
      console.error(error);
    }
  }
};

// 处理删除数据表
const handleDeleteTable = async (table: { id: string; name: string }) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据表 "${table.name}" 吗？此操作不可恢复！`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    await tableService.deleteTable(table.id);
    ElMessage.success("数据表删除成功");
    // 刷新数据表列表
    await loadTables();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
      console.error(error);
    }
  }
};

// 处理切换数据表收藏状态
const handleToggleStarTable = async (table: {
  id: string;
  isStarred: boolean;
}) => {
  try {
    await tableService.updateTable(table.id, {
      isStarred: !table.isStarred,
    });
    ElMessage.success(table.isStarred ? "已取消收藏" : "收藏成功");
    // 刷新数据表列表
    await loadTables();
  } catch (error) {
    ElMessage.error("操作失败");
    console.error(error);
  }
};

// 处理重命名仪表盘
const handleRenameDashboard = async (dashboard: {
  id: string;
  name: string;
}) => {
  try {
    const { value } = await ElMessageBox.prompt(
      "请输入新的仪表盘名称",
      "重命名仪表盘",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        inputValue: dashboard.name,
        inputValidator: (value) => {
          if (!value || value.trim() === "") {
            return "名称不能为空";
          }
          if (value.length > 50) {
            return "名称长度不能超过50个字符";
          }
          return true;
        },
      },
    );

    if (value && value.trim() !== dashboard.name) {
      await dashboardService.updateDashboard(dashboard.id, {
        name: value.trim(),
      });
      ElMessage.success("仪表盘重命名成功");
      // 刷新当前仪表盘
      if (currentDashboard.value?.id === dashboard.id) {
        currentDashboard.value = await dashboardService.getDashboard(
          dashboard.id,
        );
      }
      // 刷新仪表盘列表
      await loadDashboards();
    }
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("重命名失败");
      console.error(error);
    }
  }
};

// 处理删除仪表盘
const handleDeleteDashboard = async (dashboard: {
  id: string;
  name: string;
}) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除仪表盘 "${dashboard.name}" 吗？`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    await dashboardService.deleteDashboard(dashboard.id);
    ElMessage.success("仪表盘删除成功");

    // 如果删除的是当前仪表盘，跳转到第一个仪表盘或清空
    if (currentDashboard.value?.id === dashboard.id) {
      const remainingDashboards = dashboards.value.filter(
        (d) => d.id !== dashboard.id,
      );
      if (remainingDashboards.length > 0) {
        const baseId = route.params.id as string;
        router.push(`/base/${baseId}/dashboard/${remainingDashboards[0].id}`);
      } else {
        currentDashboard.value = null;
        widgets.value = [];
      }
    }

    // 刷新仪表盘列表
    await loadDashboards();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
      console.error(error);
    }
  }
};

// 处理切换仪表盘收藏状态
const handleToggleStarDashboard = async (dashboard: {
  id: string;
  isStarred: boolean;
}) => {
  try {
    await dashboardService.updateDashboard(dashboard.id, {
      isStarred: !dashboard.isStarred,
    });
    ElMessage.success(dashboard.isStarred ? "已取消收藏" : "收藏成功");
    // 刷新仪表盘列表
    await loadDashboards();
    // 刷新当前仪表盘
    if (currentDashboard.value?.id === dashboard.id) {
      currentDashboard.value = await dashboardService.getDashboard(
        dashboard.id,
      );
    }
  } catch (error) {
    ElMessage.error("操作失败");
    console.error(error);
  }
};

// 处理仪表盘排序
const handleReorderDashboards = async (dashboardIds: string[]) => {
  try {
    const baseId = route.params.id as string;
    await dashboardService.reorderDashboards(baseId, dashboardIds);
    // 刷新仪表盘列表
    await loadDashboards();
  } catch (error) {
    ElMessage.error("排序失败");
    console.error(error);
  }
};

// 禁用分享链接
async function deactivateShare(share: DashboardShare) {
  try {
    await ElMessageBox.confirm(
      "禁用后该分享链接将无法访问，是否继续？",
      "确认禁用",
      { type: "warning" },
    );

    await dashboardShareService.deactivateShare(share.id);
    await loadExistingShares();

    if (currentShare.value?.id === share.id) {
      currentShare.value = null;
      shareUrl.value = "";
    }

    ElMessage.success("分享链接已禁用");
  } catch {
    // 用户取消
  }
}

// 删除分享链接
async function deleteShare(share: DashboardShare) {
  try {
    await ElMessageBox.confirm(
      "删除后该分享链接将永久失效，是否继续？",
      "确认删除",
      { type: "warning" },
    );

    await dashboardShareService.deleteShare(share.id);
    await loadExistingShares();

    if (currentShare.value?.id === share.id) {
      currentShare.value = null;
      shareUrl.value = "";
    }

    ElMessage.success("分享链接已删除");
  } catch {
    // 用户取消
  }
}

// 格式化过期时间
function formatExpireTime(timestamp: number): string {
  const now = Date.now();
  const diff = timestamp - now;

  if (diff <= 0) return "已过期";

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days}天${hours % 24}小时`;
  }
  return `${hours}小时`;
}

// 加载表列表
async function loadTables() {
  if (!baseStore.currentBase) return;
  tables.value = await tableService.getTablesByBase(baseStore.currentBase.id);
}

// 加载表数据
async function loadTableData(tableId: string) {
  const [tableFields, tableRecords] = await Promise.all([
    fieldService.getFieldsByTable(tableId),
    recordService.getRecordsByTable(tableId),
  ]);

  // 合并字段（避免重复）
  tableFields.forEach((field) => {
    if (!fields.value.find((f) => f.id === field.id)) {
      fields.value.push(field);
    }
  });

  // 合并记录（避免重复）
  tableRecords.forEach((record) => {
    if (!records.value.find((r) => r.id === record.id)) {
      records.value.push(record);
    }
  });
}

async function loadFields(tableId: string) {
  const tableFields = await fieldService.getFieldsByTable(tableId);
  tableFields.forEach((field) => {
    if (!fields.value.find((f) => f.id === field.id)) {
      fields.value.push(field);
    }
  });
}

async function loadRecords(tableId: string) {
  const tableRecords = await recordService.getRecordsByTable(tableId);
  tableRecords.forEach((record) => {
    if (!records.value.find((r) => r.id === record.id)) {
      records.value.push(record);
    }
  });
}

function handleTableChange(tableId: string) {
  loadFields(tableId);
  loadRecords(tableId);
}

// 添加组件
function addWidget(type: WidgetConfig["type"]) {
  if (!currentDashboard.value) {
    ElMessage.warning("请先创建仪表盘");
    return;
  }

  const newWidget: WidgetConfig = {
    id: `widget-${Date.now()}`,
    type,
    title: widgetTypes.find((t) => t.value === type)?.label || "新图表",
    tableId: tables.value[0]?.id || "",
    fieldId: "",
    aggregation: "count",
    position: { x: 0, y: 0, w: 6, h: 4 },
    config: {
      showLegend: true,
      showLabel: false,
      colors: [],
    },
  };

  widgets.value.push(newWidget);
  selectedWidget.value = newWidget;

  if (newWidget.tableId) {
    handleTableChange(newWidget.tableId);
  }

  // 防抖自动保存
  debouncedSaveWidgets();
}

// 移除组件
function removeWidget(widgetId: string) {
  const chart = chartRefs.value.get(widgetId);
  if (chart) {
    chart.dispose();
    chartRefs.value.delete(widgetId);
  }
  widgets.value = widgets.value.filter((w) => w.id !== widgetId);
  if (selectedWidget.value?.id === widgetId) {
    selectedWidget.value = null;
  }
  debouncedSaveWidgets();
}

// 渲染组件
function renderWidget(widget: WidgetConfig) {
  const container = chartContainers.value.get(widget.id);
  if (!container) return;

  // 获取该组件的数据
  const widgetRecords = records.value.filter(
    (r) => r.tableId === widget.tableId,
  );
  const widgetFields = fields.value.filter((f) => f.tableId === widget.tableId);

  if (!widget.fieldId || widgetRecords.length === 0) {
    container.innerHTML = '<div class="widget-empty">请配置数据源</div>';
    return;
  }

  const { labels, values } = processChartData(
    widgetRecords,
    widgetFields,
    widget.groupBy,
    widget.fieldId,
    widget.aggregation,
  );

  // 数字卡片特殊处理
  if (widget.type === "number") {
    const total = values.reduce((a, b) => a + b, 0);
    const field = widgetFields.find((f) => f.id === widget.fieldId);
    const formattedValue = formatLargeNumber(total);

    container.innerHTML = `
      <div class="number-card">
        <div class="number-value" style="color: ${widget.config?.colors?.[0] || "#3370FF"}">${formattedValue}</div>
        <div class="number-label">${widget.title}</div>
        ${values.length > 1 ? `<div class="number-detail">共 ${values.length} 项数据</div>` : ""}
      </div>
    `;
    return;
  }

  // 表格特殊处理
  if (widget.type === "table") {
    const colors = getChartColors(labels.length);
    container.innerHTML = `
      <div class="table-widget">
        <table class="data-table">
          <thead>
            <tr>
              <th>${widget.groupBy ? getFieldById(widget.groupBy)?.name || "分组" : "类别"}</th>
              <th>${getAggregationLabel(widget.aggregation)}</th>
            </tr>
          </thead>
          <tbody>
            ${labels
              .map(
                (label, i) => `
              <tr>
                <td>
                  <span class="table-dot" style="background-color: ${colors[i]}"></span>
                  ${label}
                </td>
                <td class="value-cell">${formatLargeNumber(values[i])}</td>
              </tr>
            `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
    return;
  }

  // 图表渲染
  let chart = chartRefs.value.get(widget.id);
  if (!chart) {
    chart = echarts.init(container);
    chartRefs.value.set(widget.id, chart);
  }

  const colors = widget.config?.colors?.length
    ? widget.config.colors
    : getChartColors(labels.length);

  const option = getChartOption(widget, labels, values, colors);
  chart.setOption(option, true);
}

// 获取图表配置
function getChartOption(
  widget: WidgetConfig,
  labels: string[],
  values: number[],
  colors: string[],
): EChartsOption {
  const baseOption: EChartsOption = {
    color: colors,
    tooltip: {
      trigger: widget.type === "pie" ? "item" : "axis",
      formatter: (params: any) => {
        if (Array.isArray(params)) {
          const p = params[0];
          return `${p.name}: <b>${formatLargeNumber(p.value)}</b>`;
        }
        return `${params.name}: <b>${formatLargeNumber(params.value)}</b> (${params.percent}%)`;
      },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: widget.config?.showLegend ? "15%" : "10%",
      containLabel: true,
    },
  };

  switch (widget.type) {
    case "bar":
      return {
        ...baseOption,
        legend: widget.config?.showLegend
          ? {
              data: [widget.title],
              top: 0,
            }
          : undefined,
        xAxis: {
          type: "category",
          data: labels,
          axisLabel: {
            rotate: labels.length > 6 ? 45 : 0,
            interval: 0,
          },
        },
        yAxis: {
          type: "value",
          axisLabel: {
            formatter: (value: number) => formatLargeNumber(value),
          },
        },
        series: [
          {
            name: widget.title,
            type: "bar",
            data: values,
            barWidth: "60%",
            itemStyle: {
              borderRadius: [4, 4, 0, 0],
            },
            label: widget.config?.showLabel
              ? {
                  show: true,
                  position: "top",
                  formatter: (p: any) => formatLargeNumber(p.value),
                }
              : undefined,
          },
        ],
      };

    case "line":
    case "area":
      return {
        ...baseOption,
        legend: widget.config?.showLegend
          ? {
              data: [widget.title],
              top: 0,
            }
          : undefined,
        xAxis: {
          type: "category",
          data: labels,
          boundaryGap: widget.type === "area",
        },
        yAxis: {
          type: "value",
          axisLabel: {
            formatter: (value: number) => formatLargeNumber(value),
          },
        },
        series: [
          {
            name: widget.title,
            type: "line",
            data: values,
            smooth: widget.config?.smooth ?? true,
            areaStyle:
              widget.type === "area"
                ? {
                    opacity: 0.3,
                  }
                : undefined,
            symbol: "circle",
            symbolSize: 8,
            lineStyle: {
              width: 3,
            },
          },
        ],
      };

    case "pie":
      return {
        ...baseOption,
        legend: widget.config?.showLegend
          ? {
              orient: "vertical",
              right: 10,
              top: "center",
              data: labels,
            }
          : undefined,
        series: [
          {
            type: "pie",
            radius: ["40%", "70%"],
            center: widget.config?.showLegend ? ["40%", "50%"] : ["50%", "50%"],
            data: labels.map((label, i) => ({
              name: label,
              value: values[i],
            })),
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: "rgba(0, 0, 0, 0.5)",
              },
            },
            label: widget.config?.showLabel
              ? {
                  show: true,
                  formatter: "{b}: {c} ({d}%)",
                }
              : {
                  show: false,
                },
          },
        ],
      };

    case "scatter":
      return {
        ...baseOption,
        xAxis: { type: "category", data: labels },
        yAxis: {
          type: "value",
          axisLabel: { formatter: (value: number) => formatLargeNumber(value) },
        },
        series: [
          {
            type: "scatter",
            data: values,
            symbolSize: (val: number) => Math.min(Math.max(val / 10, 10), 50),
          },
        ],
      };

    default:
      return baseOption;
  }
}

// 获取聚合类型标签
function getAggregationLabel(aggregation: string): string {
  return (
    aggregationTypes.find((a) => a.value === aggregation)?.label || aggregation
  );
}

// 获取字段信息
function getFieldById(fieldId: string): FieldEntity | undefined {
  return fields.value.find((f) => f.id === fieldId);
}

// 获取表信息
function getTableById(tableId: string): TableEntity | undefined {
  return tables.value.find((t) => t.id === tableId);
}

// 处理大小调整
function startResize(event: MouseEvent, widget: WidgetConfig) {
  event.stopPropagation();
  resizingWidget.value = widget.id;
  resizeStart.value = {
    x: event.clientX,
    y: event.clientY,
    w: widget.position.w,
    h: widget.position.h,
  };

  document.addEventListener("mousemove", onResize);
  document.addEventListener("mouseup", stopResize);
}

function onResize(event: MouseEvent) {
  if (!resizingWidget.value) return;

  const widget = widgets.value.find((w) => w.id === resizingWidget.value);
  if (!widget) return;

  const dx = event.clientX - resizeStart.value.x;
  const dy = event.clientY - resizeStart.value.y;

  // 每50px为一个单位
  const dw = Math.round(dx / 50);
  const dh = Math.round(dy / 30);

  widget.position.w = Math.max(2, Math.min(12, resizeStart.value.w + dw));
  widget.position.h = Math.max(2, Math.min(8, resizeStart.value.h + dh));

  // 重新渲染
  nextTick(() => {
    renderWidget(widget);
  });
}

// 停止调整
function stopResize() {
  if (resizingWidget.value) {
    debouncedSaveWidgets();
  }
  resizingWidget.value = null;
  document.removeEventListener("mousemove", onResize);
  document.removeEventListener("mouseup", stopResize);
}

// 监听组件变化
watch(
  widgets,
  () => {
    nextTick(() => {
      widgets.value.forEach((widget) => renderWidget(widget));
    });
  },
  { deep: true },
);

// 监听选中组件变化
watch(selectedWidget, (widget) => {
  if (widget) {
    handleTableChange(widget.tableId);
  }
});

// 窗口大小变化
function handleResize() {
  chartRefs.value.forEach((chart) => chart.resize());
}

onMounted(() => {
  loadTables();
  loadDashboards();
  window.addEventListener("resize", handleResize);
});

// 监听路由参数变化，刷新数据
watch(
  () => [route.params.id, route.params.dashboardId],
  ([newBaseId, newDashboardId], [oldBaseId, oldDashboardId]) => {
    // baseId 变化时重新加载
    if (newBaseId !== oldBaseId && newBaseId) {
      loadTables();
      loadDashboards();
    }
    // dashboardId 变化时切换到对应仪表盘
    else if (newDashboardId !== oldDashboardId && newDashboardId) {
      const targetDashboard = dashboards.value.find(
        (d) => d.id === newDashboardId,
      );
      if (targetDashboard) {
        selectDashboard(targetDashboard);
      }
    }
  },
  { immediate: false },
);

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartRefs.value.forEach((chart) => chart.dispose());

  // 清除保存定时器
  if (saveTimeout.value) {
    clearTimeout(saveTimeout.value);
  }

  // 如果有未保存的更改，立即保存
  if (hasUnsavedChanges.value && currentDashboard.value) {
    const plainWidgets = JSON.parse(JSON.stringify(widgets.value));
    dashboardService.updateDashboardWidgets(
      currentDashboard.value.id,
      plainWidgets,
    );
  }
});
</script>

<template>
  <div class="dashboard-view">
    <!-- 加载遮罩 -->
    <div v-if="isLoading" class="loading-overlay">
      <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
      <span class="loading-text">{{ loadingText }}</span>
    </div>

    <!-- 侧边栏 -->
    <BaseSidebar
      ref="sidebarRef"
      :current-dashboard-id="currentDashboard?.id"
      :show-tables="true"
      :show-dashboards="true"
      @select-table="handleTableSelect"
      @select-dashboard="handleDashboardSelect"
      @add-table="openCreateTableDialog"
      @add-dashboard="openCreateDashboardDialog"
      @rename-table="handleRenameTable"
      @delete-table="handleDeleteTable"
      @toggle-star="handleToggleStarTable"
      @rename-dashboard="handleRenameDashboard"
      @delete-dashboard="handleDeleteDashboard"
      @toggle-star-dashboard="handleToggleStarDashboard"
      @reorder-dashboards="handleReorderDashboards" />

    <div class="dashboard-main">
      <!-- 顶部工具栏 -->
      <div class="dashboard-toolbar">
        <div class="toolbar-left">
          <el-dropdown @command="showDashboardManager = true">
            <el-button text class="dashboard-selector">
              <el-icon><DataAnalysis /></el-icon>
              <span class="dashboard-name">{{
                currentDashboard?.name || "选择仪表盘"
              }}</span>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </el-button>
          </el-dropdown>

          <el-divider direction="vertical" />

          <el-dropdown @command="addWidget">
            <el-button type="primary">
              <el-icon><Plus /></el-icon>
              添加组件
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu class="widget-type-menu">
                <el-dropdown-item
                  v-for="type in widgetTypes"
                  :key="type.value"
                  :command="type.value">
                  <div class="widget-type-item">
                    <el-icon :size="20"><component :is="type.icon" /></el-icon>
                    <div class="widget-type-info">
                      <div class="widget-type-name">{{ type.label }}</div>
                      <div class="widget-type-desc">{{ type.description }}</div>
                    </div>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div class="toolbar-right">
          <el-button
            v-if="currentDashboard"
            type="success"
            @click="openShareDialog">
            <el-icon><Share /></el-icon>
            分享
          </el-button>
          <el-button
            v-if="currentDashboard"
            text
            @click="
              isEditingDashboard = true;
              isCreatingDashboard = false;
              dashboardForm = {
                name: currentDashboard.name,
                description: currentDashboard.description || '',
              };
            ">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button
            v-if="currentDashboard"
            text
            @click="duplicateDashboard(currentDashboard)">
            <el-icon><CopyDocument /></el-icon>
            复制
          </el-button>
          <el-button text @click="showDashboardManager = true">
            <el-icon><Management /></el-icon>
            管理
          </el-button>
        </div>
      </div>

      <!-- 仪表盘内容 -->
      <div class="dashboard-content">
        <!-- 组件网格 -->
        <div class="widgets-grid">
          <div
            v-for="widget in widgets"
            :key="widget.id"
            class="widget-card"
            :class="{
              selected: selectedWidget?.id === widget.id,
              resizing: resizingWidget === widget.id,
            }"
            :style="{
              gridColumn: `span ${widget.position.w}`,
              gridRow: `span ${widget.position.h}`,
            }"
            @click="selectedWidget = widget">
            <div class="widget-header">
              <div class="widget-title-section">
                <span class="widget-title">{{ widget.title }}</span>
                <span class="widget-subtitle">
                  {{ getTableById(widget.tableId)?.name }}
                  ·
                  {{ getAggregationLabel(widget.aggregation) }}
                </span>
              </div>
              <div class="widget-actions">
                <el-button
                  link
                  size="small"
                  @click.stop="removeWidget(widget.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <div
              :ref="
                (el) => el && chartContainers.set(widget.id, el as HTMLElement)
              "
              class="widget-body"></div>
            <!-- 调整大小手柄 -->
            <div
              class="resize-handle"
              @mousedown.stop="startResize($event, widget)">
              <el-icon><FullScreen /></el-icon>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="widgets.length === 0" class="empty-dashboard">
            <el-empty description="暂无组件">
              <template #image>
                <el-icon class="empty-icon"><DataAnalysis /></el-icon>
              </template>
              <template #description>
                <p>点击上方"添加组件"创建图表</p>
                <p v-if="!currentDashboard" class="empty-hint">
                  请先创建仪表盘
                </p>
              </template>
              <el-button
                v-if="!currentDashboard"
                type="primary"
                @click="isEditingDashboard = true">
                创建仪表盘
              </el-button>
            </el-empty>
          </div>
        </div>

        <!-- 配置面板 -->
        <div v-if="selectedWidget" class="config-panel">
          <div class="panel-header">
            <h3>组件配置</h3>
            <div class="panel-actions">
              <el-tag v-if="hasUnsavedChanges" size="small" type="warning"
                >未保存</el-tag
              >
              <el-tag v-else-if="isSaving" size="small" type="info"
                >保存中...</el-tag
              >
              <el-tag v-else size="small" type="success">已保存</el-tag>
              <el-button link @click="selectedWidget = null">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>

          <el-scrollbar class="panel-content">
            <el-form label-position="top" size="small">
              <!-- 基础配置 -->
              <div class="config-section">
                <div class="section-title">基础配置</div>

                <el-form-item label="标题">
                  <el-input
                    v-model="selectedWidget.title"
                    @change="debouncedSaveWidgets()" />
                </el-form-item>

                <el-form-item label="数据表">
                  <el-select
                    :model-value="selectedWidget.tableId"
                    @update:model-value="
                      (val) => {
                        selectedWidget!.tableId = val;
                        handleTableChange(val);
                        debouncedSaveWidgets();
                      }
                    ">
                    <el-option
                      v-for="table in tables"
                      :key="table.id"
                      :label="table.name"
                      :value="table.id" />
                  </el-select>
                </el-form-item>
              </div>

              <!-- 数据配置 -->
              <div class="config-section">
                <div class="section-title">数据配置</div>

                <el-form-item label="分组字段 (可选)">
                  <el-select
                    v-model="selectedWidget.groupBy"
                    clearable
                    placeholder="不分组"
                    @change="debouncedSaveWidgets()">
                    <el-option
                      v-for="field in fields.filter(
                        (f) => f.tableId === selectedWidget.tableId,
                      )"
                      :key="field.id"
                      :label="field.name"
                      :value="field.id">
                      <el-icon class="field-icon">
                        <CollectionTag
                          v-if="
                            field.type === FieldType.SINGLE_SELECT ||
                            field.type === FieldType.MULTI_SELECT
                          " />
                        <Calendar v-else-if="field.type === FieldType.DATE" />
                        <Sort v-else-if="field.type === FieldType.NUMBER" />
                        <Document v-else />
                      </el-icon>
                      {{ field.name }}
                    </el-option>
                  </el-select>
                </el-form-item>

                <el-form-item label="数值字段">
                  <el-select
                    v-model="selectedWidget.fieldId"
                    placeholder="选择字段"
                    @change="debouncedSaveWidgets()">
                    <el-option
                      v-for="field in fields.filter(
                        (f) => f.tableId === selectedWidget.tableId,
                      )"
                      :key="field.id"
                      :label="field.name"
                      :value="field.id">
                      <el-icon class="field-icon">
                        <CollectionTag
                          v-if="
                            field.type === FieldType.SINGLE_SELECT ||
                            field.type === FieldType.MULTI_SELECT
                          " />
                        <Calendar v-else-if="field.type === FieldType.DATE" />
                        <Sort v-else-if="field.type === FieldType.NUMBER" />
                        <Document v-else />
                      </el-icon>
                      {{ field.name }}
                    </el-option>
                  </el-select>
                </el-form-item>

                <el-form-item label="聚合方式">
                  <el-select
                    v-model="selectedWidget.aggregation"
                    @change="debouncedSaveWidgets()">
                    <el-option
                      v-for="agg in filteredAggregationTypes"
                      :key="agg.value"
                      :label="agg.label"
                      :value="agg.value">
                      <div class="aggregation-option">
                        <span>{{ agg.label }}</span>
                        <span class="aggregation-desc">{{
                          agg.description
                        }}</span>
                      </div>
                    </el-option>
                  </el-select>
                  <div
                    v-if="
                      !canUseNumericAggregation &&
                      selectedWidget.aggregation !== 'count' &&
                      selectedWidget.aggregation !== 'countDistinct'
                    "
                    class="validation-warning">
                    <el-icon><Warning /></el-icon>
                    当前字段不支持数值聚合，已自动切换为计数
                  </div>
                </el-form-item>
              </div>

              <!-- 样式配置 -->
              <div class="config-section">
                <div class="section-title">样式配置</div>

                <el-form-item
                  label="显示图例"
                  v-if="
                    selectedWidget.type !== 'number' &&
                    selectedWidget.type !== 'table'
                  ">
                  <el-switch
                    v-model="selectedWidget.config.showLegend"
                    @change="debouncedSaveWidgets()" />
                </el-form-item>

                <el-form-item
                  label="显示数值标签"
                  v-if="
                    selectedWidget.type === 'bar' ||
                    selectedWidget.type === 'pie'
                  ">
                  <el-switch
                    v-model="selectedWidget.config.showLabel"
                    @change="debouncedSaveWidgets()" />
                </el-form-item>

                <el-form-item
                  label="平滑曲线"
                  v-if="
                    selectedWidget.type === 'line' ||
                    selectedWidget.type === 'area'
                  ">
                  <el-switch
                    v-model="selectedWidget.config.smooth"
                    @change="debouncedSaveWidgets()" />
                </el-form-item>
              </div>

              <!-- 组件大小 -->
              <div class="config-section">
                <div class="section-title">组件大小</div>

                <el-form-item label="宽度 (列数)">
                  <el-slider
                    v-model="selectedWidget.position.w"
                    :min="2"
                    :max="12"
                    :step="1"
                    show-stops
                    @change="debouncedSaveWidgets()" />
                </el-form-item>

                <el-form-item label="高度 (行数)">
                  <el-slider
                    v-model="selectedWidget.position.h"
                    :min="2"
                    :max="8"
                    :step="1"
                    show-stops
                    @change="debouncedSaveWidgets()" />
                </el-form-item>
              </div>

              <!-- 保存按钮 -->
              <div class="config-section save-section">
                <el-button
                  type="primary"
                  :loading="isSaving"
                  :disabled="!hasUnsavedChanges"
                  @click="saveWidgets()"
                  style="width: 100%">
                  <el-icon><Check /></el-icon>
                  {{
                    isSaving
                      ? "保存中..."
                      : hasUnsavedChanges
                        ? "立即保存"
                        : "已保存"
                  }}
                </el-button>
              </div>
            </el-form>
          </el-scrollbar>
        </div>
      </div>

      <!-- 仪表盘管理对话框 -->
      <el-dialog
        v-model="showDashboardManager"
        title="仪表盘管理"
        width="600px"
        destroy-on-close>
        <div class="dashboard-manager">
          <div class="manager-header">
            <el-button
              type="primary"
              @click="
                isEditingDashboard = true;
                isCreatingDashboard = true;
                dashboardForm = { name: '', description: '' };
              ">
              <el-icon><Plus /></el-icon>
              新建仪表盘
            </el-button>
          </div>

          <el-table :data="dashboards" style="width: 100%">
            <el-table-column prop="name" label="名称" min-width="150">
              <template #default="{ row }">
                <div class="dashboard-name-cell">
                  <el-icon><DataAnalysis /></el-icon>
                  <span>{{ row.name }}</span>
                  <el-tag
                    v-if="row.id === currentDashboard?.id"
                    size="small"
                    type="primary"
                    >当前</el-tag
                  >
                </div>
              </template>
            </el-table-column>
            <el-table-column
              prop="description"
              label="描述"
              min-width="200"
              show-overflow-tooltip />
            <el-table-column prop="updatedAt" label="更新时间" width="150">
              <template #default="{ row }">
                {{ new Date(row.updatedAt).toLocaleString() }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  @click="
                    selectDashboard(row);
                    showDashboardManager = false;
                  ">
                  打开
                </el-button>
                <el-button link @click="duplicateDashboard(row)"
                  >复制</el-button
                >
                <el-button link type="danger" @click="deleteDashboard(row)"
                  >删除</el-button
                >
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-dialog>

      <!-- 创建/编辑仪表盘对话框 -->
      <el-dialog
        v-model="isEditingDashboard"
        :title="isCreatingDashboard ? '新建仪表盘' : '编辑仪表盘'"
        width="500px"
        destroy-on-close
        @closed="isCreatingDashboard = false">
        <el-form label-position="top">
          <el-form-item label="仪表盘名称" required>
            <el-input
              v-model="dashboardForm.name"
              placeholder="请输入仪表盘名称"
              maxlength="50"
              show-word-limit
              @keyup.enter="
                isCreatingDashboard ? createDashboard() : updateDashboard()
              " />
          </el-form-item>
          <el-form-item label="描述">
            <el-input
              v-model="dashboardForm.description"
              type="textarea"
              :rows="3"
              placeholder="请输入仪表盘描述（可选）"
              maxlength="200"
              show-word-limit />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="isEditingDashboard = false">取消</el-button>
          <el-button
            type="primary"
            @click="isCreatingDashboard ? createDashboard() : updateDashboard()"
            :disabled="!dashboardForm.name.trim()">
            {{ isCreatingDashboard ? "创建" : "保存" }}
          </el-button>
        </template>
      </el-dialog>

      <!-- 分享对话框 -->
      <el-dialog
        v-model="showShareDialog"
        title="分享仪表盘"
        width="600px"
        destroy-on-close>
        <div class="share-dialog-content">
          <!-- 创建新分享 -->
          <div class="share-create-section">
            <h4>创建分享链接</h4>
            <el-form label-position="top" size="small">
              <el-form-item label="有效期">
                <el-select
                  v-model="shareForm.expiresInHours"
                  style="width: 100%">
                  <el-option :value="1" label="1小时" />
                  <el-option :value="24" label="1天" />
                  <el-option :value="168" label="7天" />
                  <el-option :value="720" label="30天" />
                  <el-option :value="0" label="永久有效" />
                </el-select>
              </el-form-item>

              <el-form-item label="访问次数限制">
                <el-input-number
                  v-model="shareForm.maxAccessCount"
                  :min="0"
                  :max="10000"
                  :controls="true"
                  style="width: 100%"
                  placeholder="0表示无限制" />
              </el-form-item>

              <el-form-item label="访问密码">
                <el-switch
                  v-model="shareForm.requireAccessCode"
                  active-text="需要密码"
                  inactive-text="无需密码" />
              </el-form-item>

              <el-form-item label="权限">
                <el-radio-group v-model="shareForm.permission">
                  <el-radio label="view">仅查看</el-radio>
                  <el-radio label="edit">可编辑</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-button
                type="primary"
                :loading="isCreatingShare"
                @click="createShare"
                style="width: 100%">
                <el-icon><Link /></el-icon>
                生成分享链接
              </el-button>
            </el-form>
          </div>

          <!-- 生成的分享链接 -->
          <div v-if="currentShare && shareUrl" class="share-result-section">
            <el-divider />
            <h4>分享链接</h4>
            <div class="share-link-box">
              <el-input v-model="shareUrl" readonly class="share-link-input">
                <template #append>
                  <el-button @click="copyShareUrl">
                    <el-icon><CopyDocument /></el-icon>
                    复制
                  </el-button>
                </template>
              </el-input>
            </div>

            <div v-if="currentShare.accessCode" class="share-access-code">
              <span class="label">访问密码：</span>
              <span class="code">{{ currentShare.accessCode }}</span>
              <el-button
                link
                type="primary"
                size="small"
                @click="copyAccessCode">
                <el-icon><CopyDocument /></el-icon>
                复制密码
              </el-button>
            </div>

            <div class="share-info">
              <el-tag v-if="currentShare.expiresAt" size="small" type="info">
                有效期至：{{
                  new Date(currentShare.expiresAt).toLocaleString()
                }}
              </el-tag>
              <el-tag v-else size="small" type="info">永久有效</el-tag>
              <el-tag
                v-if="currentShare.maxAccessCount"
                size="small"
                type="warning">
                限 {{ currentShare.maxAccessCount }} 次访问
              </el-tag>
            </div>
          </div>

          <!-- 已有的分享链接 -->
          <div v-if="existingShares.length > 0" class="share-list-section">
            <el-divider />
            <h4>已有的分享链接</h4>
            <el-table :data="existingShares" size="small" style="width: 100%">
              <el-table-column label="创建时间" width="150">
                <template #default="{ row }">
                  {{ new Date(row.createdAt).toLocaleDateString() }}
                </template>
              </el-table-column>
              <el-table-column label="有效期" width="120">
                <template #default="{ row }">
                  <span v-if="row.expiresAt">{{
                    formatExpireTime(row.expiresAt)
                  }}</span>
                  <span v-else>永久</span>
                </template>
              </el-table-column>
              <el-table-column label="访问次数" width="100">
                <template #default="{ row }">
                  {{ row.currentAccessCount }}
                  <span v-if="row.maxAccessCount"
                    >/ {{ row.maxAccessCount }}</span
                  >
                </template>
              </el-table-column>
              <el-table-column label="密码" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.accessCode" size="small" type="warning"
                    >有</el-tag
                  >
                  <el-tag v-else size="small" type="info">无</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    size="small"
                    @click="copyShareUrlByToken(row.shareToken)">
                    复制
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    size="small"
                    @click="deleteShare(row)">
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script lang="ts">
import {
  Plus,
  Delete,
  DataAnalysis,
  BarChart,
  TrendCharts,
  PieChart,
  Grid,
  ArrowDown,
  Edit,
  CopyDocument,
  Management,
  Close,
  FullScreen,
  CollectionTag,
  Calendar,
  Sort,
  Document,
  Warning,
  Histogram,
  CircleCheck,
  Check,
  Share,
  Link,
  Loading,
} from "@element-plus/icons-vue";

export default {
  name: "DashboardView",
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.dashboard-view {
  display: flex;
  height: 100%;
  background-color: $bg-color;
  position: relative; // 为加载遮罩提供定位上下文
}

// 加载遮罩
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba($surface-color, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  gap: $spacing-md;

  .loading-icon {
    color: $primary-color;
    animation: rotate 1s linear infinite;
  }

  .loading-text {
    font-size: $font-size-base;
    color: $text-secondary;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.dashboard-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// 工具栏 - 固定位置，不随滚动
.dashboard-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  flex-shrink: 0; // 防止工具栏被压缩
  position: sticky;
  top: 0;
  z-index: 10;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }
}

.dashboard-selector {
  font-size: $font-size-lg;
  font-weight: 500;

  .dashboard-name {
    margin: 0 $spacing-xs;
  }

  .dropdown-icon {
    font-size: 12px;
    color: $text-secondary;
  }
}

.dropdown-icon {
  margin-left: 4px;
}

// 组件类型菜单
.widget-type-menu {
  .widget-type-item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-xs 0;

    .widget-type-info {
      .widget-type-name {
        font-weight: 500;
        color: $text-primary;
      }

      .widget-type-desc {
        font-size: $font-size-xs;
        color: $text-secondary;
        margin-top: 2px;
      }
    }
  }
}

// 内容区域
.dashboard-content {
  flex: 1;
  display: flex;
  flex-direction: row; // 横向排列：组件网格 + 配置面板
  overflow: hidden;
  min-height: 0; // 确保flex子元素可以正确收缩
}

// 组件网格 - 可滚动区域
.widgets-grid {
  flex: 1;
  padding: $spacing-lg;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 80px;
  gap: $spacing-md;
  overflow-y: auto;
  overflow-x: hidden;
  align-content: start;
  min-height: 0; // 确保可以正确滚动
}

// 组件卡片
.widget-card {
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  border: 1px solid $border-color;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
  position: relative;
  min-height: 160px;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.selected {
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.2);
  }

  &.resizing {
    opacity: 0.8;
    border-color: $primary-color;
  }
}

.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid $border-color;
  background-color: #fafafa;

  .widget-title-section {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;

    .widget-title {
      font-weight: 500;
      color: $text-primary;
      font-size: $font-size-base;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .widget-subtitle {
      font-size: $font-size-xs;
      color: $text-secondary;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .widget-actions {
    display: flex;
    gap: $spacing-xs;
    opacity: 0;
    transition: opacity 0.2s;
  }
}

.widget-card:hover .widget-actions {
  opacity: 1;
}

.widget-body {
  flex: 1;
  padding: $spacing-md;
  min-height: 0;
  position: relative;
}

// 调整大小手柄
.resize-handle {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: se-resize;
  color: $text-disabled;
  opacity: 0;
  transition: opacity 0.2s;

  &:hover {
    color: $primary-color;
  }
}

.widget-card:hover .resize-handle {
  opacity: 1;
}

// 空状态
.empty-dashboard {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;

  .empty-icon {
    font-size: 64px;
    color: $text-disabled;
  }

  .empty-hint {
    color: $text-secondary;
    margin-top: $spacing-sm;
  }
}

// 配置面板 - 固定在右侧，不遮挡组件
.config-panel {
  width: 320px;
  background-color: $surface-color;
  border-left: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  flex-shrink: 0; // 防止面板被压缩
  height: 100%; // 占满父容器高度
  overflow: hidden; // 防止整体滚动

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-md;
    border-bottom: 1px solid $border-color;
    flex-shrink: 0; // 防止头部被压缩

    h3 {
      font-size: $font-size-base;
      font-weight: 500;
      color: $text-primary;
      margin: 0;
    }

    .panel-actions {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
    }
  }

  .panel-content {
    flex: 1;
    padding: $spacing-md;
    overflow-y: auto; // 内容区域可滚动
    min-height: 0; // 确保可以正确滚动
  }
}

// 配置区域
.config-section {
  margin-bottom: $spacing-lg;

  .section-title {
    font-size: $font-size-sm;
    font-weight: 500;
    color: $text-secondary;
    margin-bottom: $spacing-sm;
    padding-bottom: $spacing-xs;
    border-bottom: 1px solid $border-color;
  }

  &.save-section {
    margin-top: $spacing-xl;
    padding-top: $spacing-md;
    border-top: 1px solid $border-color;
  }
}

.field-icon {
  margin-right: 6px;
  font-size: 14px;
  color: $text-secondary;
}

.aggregation-option {
  display: flex;
  flex-direction: column;

  .aggregation-desc {
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.validation-warning {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  margin-top: $spacing-xs;
  font-size: $font-size-xs;
  color: $warning-color;
}

// 数字卡片样式
.number-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  .number-value {
    font-size: 48px;
    font-weight: 700;
    line-height: 1.2;
  }

  .number-label {
    font-size: $font-size-base;
    color: $text-secondary;
    margin-top: $spacing-sm;
  }

  .number-detail {
    font-size: $font-size-sm;
    color: $text-disabled;
    margin-top: $spacing-xs;
  }
}

// 表格组件样式
.table-widget {
  height: 100%;
  overflow: auto;

  .data-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: $spacing-xs $spacing-sm;
      text-align: left;
      border-bottom: 1px solid $border-color;
      font-size: $font-size-sm;
    }

    th {
      font-weight: 500;
      color: $text-secondary;
      background-color: #f5f7fa;
      position: sticky;
      top: 0;
    }

    td {
      color: $text-primary;

      .table-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
      }
    }

    .value-cell {
      font-weight: 500;
      text-align: right;
    }
  }
}

.widget-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: $text-secondary;
  font-size: $font-size-sm;
}

// 仪表盘管理器
.dashboard-manager {
  .manager-header {
    margin-bottom: $spacing-md;
  }
}

.dashboard-name-cell {
  display: flex;
  align-items: center;
  gap: $spacing-xs;

  .el-tag {
    margin-left: $spacing-xs;
  }
}

// 分享对话框样式
.share-dialog-content {
  h4 {
    font-size: $font-size-base;
    font-weight: 500;
    color: $text-primary;
    margin: 0 0 $spacing-md 0;
  }

  .share-create-section {
    margin-bottom: $spacing-lg;
  }

  .share-result-section {
    margin-bottom: $spacing-lg;

    .share-link-box {
      margin-bottom: $spacing-md;

      .share-link-input {
        :deep(.el-input__inner) {
          font-family: monospace;
          font-size: $font-size-sm;
        }
      }
    }

    .share-access-code {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      margin-bottom: $spacing-md;
      padding: $spacing-sm;
      background-color: $bg-color;
      border-radius: $border-radius-base;

      .label {
        color: $text-secondary;
        font-size: $font-size-sm;
      }

      .code {
        font-family: monospace;
        font-size: $font-size-lg;
        font-weight: 600;
        color: $primary-color;
        letter-spacing: 2px;
      }
    }

    .share-info {
      display: flex;
      gap: $spacing-xs;
      flex-wrap: wrap;
    }
  }

  .share-list-section {
    h4 {
      margin-bottom: $spacing-md;
    }
  }
}
</style>
