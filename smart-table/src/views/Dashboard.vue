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
} from "@/db/services/dashboardShareService";
import type { DashboardShare } from "@/db/schema";
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
const isCreatingDashboard = ref(false);
const dashboardForm = ref({
  name: "",
  description: "",
});

// 加载状态
const isLoading = ref(false);
const loadingText = ref("加载中...");
const skeletonCount = ref(6);

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
  expiresInHours: 168,
  maxAccessCount: undefined as number | undefined,
  requireAccessCode: false,
  permission: "view" as "view" | "edit",
});
const currentShare = ref<DashboardShare | null>(null);
const shareUrl = ref("");
const isCreatingShare = ref(false);
const existingShares = ref<DashboardShare[]>([]);

// 清新配色方案
const freshColors = {
  primary: "#3B82F6",
  primaryLight: "#EFF6FF",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  gray50: "#F9FAFB",
  gray100: "#F3F4F6",
  gray200: "#E5E7EB",
  gray300: "#D1D5DB",
  gray400: "#9CA3AF",
  gray500: "#6B7280",
  gray600: "#4B5563",
  gray700: "#374151",
  gray800: "#1F2937",
};

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
  const numericTypes: string[] = [
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

  const numericTypes: string[] = [
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

  const tableIds = [...new Set(widgets.value.map((w) => w.tableId))];
  for (const tableId of tableIds) {
    await loadTableData(tableId);
  }

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

  if (saveTimeout.value) {
    clearTimeout(saveTimeout.value);
    saveTimeout.value = null;
  }

  isSaving.value = true;
  hasUnsavedChanges.value = true;

  try {
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

// 防抖保存
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

async function openShareDialog() {
  if (!currentDashboard.value) {
    ElMessage.warning("请先选择仪表盘");
    return;
  }

  showShareDialog.value = true;
  currentShare.value = null;
  shareUrl.value = "";

  await loadExistingShares();
}

async function loadExistingShares() {
  if (!currentDashboard.value) return;
  existingShares.value = await dashboardShareService.getSharesByDashboard(
    currentDashboard.value.id,
  );
}

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

    await loadExistingShares();

    ElMessage.success("分享链接创建成功");
  } catch (error) {
    console.error("创建分享链接失败:", error);
    ElMessage.error("创建分享链接失败");
  } finally {
    isCreatingShare.value = false;
  }
}

async function copyShareUrl() {
  if (!shareUrl.value) return;

  const success = await dashboardShareService.copyToClipboard(shareUrl.value);
  if (success) {
    ElMessage.success("链接已复制到剪贴板");
  } else {
    ElMessage.error("复制失败，请手动复制");
  }
}

async function copyShareUrlByToken(token: string) {
  const url = dashboardShareService.generateShareUrl(token);
  const success = await dashboardShareService.copyToClipboard(url);
  if (success) {
    ElMessage.success("链接已复制到剪贴板");
  } else {
    ElMessage.error("复制失败，请手动复制");
  }
}

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

const handleTableSelect = (_tableId: string) => {
  const baseId = route.params.id as string;
  router.push(`/base/${baseId}`);
};

const handleDashboardSelect = (dashboardId: string) => {
  const baseId = route.params.id as string;
  router.push(`/base/${baseId}/dashboard/${dashboardId}`);
};

const openCreateTableDialog = () => {
  const baseId = route.params.id as string;
  router.push(`/base/${baseId}`);
};

const openCreateDashboardDialog = () => {
  isEditingDashboard.value = true;
  isCreatingDashboard.value = true;
  dashboardForm.value = { name: "", description: "" };
};

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
      await loadTables();
    }
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("重命名失败");
      console.error(error);
    }
  }
};

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
    await loadTables();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
      console.error(error);
    }
  }
};

const handleToggleStarTable = async (table: {
  id: string;
  isStarred: boolean;
}) => {
  try {
    await tableService.updateTable(table.id, {
      isStarred: !table.isStarred,
    });
    ElMessage.success(table.isStarred ? "已取消收藏" : "收藏成功");
    await loadTables();
  } catch (error) {
    ElMessage.error("操作失败");
    console.error(error);
  }
};

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
      if (currentDashboard.value?.id === dashboard.id) {
        const updatedDashboard = await dashboardService.getDashboard(dashboard.id);
        if (updatedDashboard) {
          currentDashboard.value = updatedDashboard;
        }
      }
      await loadDashboards();
    }
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("重命名失败");
      console.error(error);
    }
  }
};

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

    await loadDashboards();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
      console.error(error);
    }
  }
};

const handleToggleStarDashboard = async (dashboard: {
  id: string;
  isStarred: boolean;
}) => {
  try {
    await dashboardService.updateDashboard(dashboard.id, {
      isStarred: !dashboard.isStarred,
    });
    ElMessage.success(dashboard.isStarred ? "已取消收藏" : "收藏成功");
    await loadDashboards();
    if (currentDashboard.value?.id === dashboard.id) {
      const updatedDashboard = await dashboardService.getDashboard(dashboard.id);
      if (updatedDashboard) {
        currentDashboard.value = updatedDashboard;
      }
    }
  } catch (error) {
    ElMessage.error("操作失败");
    console.error(error);
  }
};

const handleReorderDashboards = async (dashboardIds: string[]) => {
  try {
    const baseId = route.params.id as string;
    await dashboardService.reorderDashboards(baseId, dashboardIds);
    await loadDashboards();
  } catch (error) {
    ElMessage.error("排序失败");
    console.error(error);
  }
};

// @ts-expect-error - 保留但未使用的函数
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

async function loadTables() {
  if (!baseStore.currentBase) return;
  tables.value = await tableService.getTablesByBase(baseStore.currentBase.id);
}

async function loadTableData(tableId: string) {
  const [tableFields, tableRecords] = await Promise.all([
    fieldService.getFieldsByTable(tableId),
    recordService.getRecordsByTable(tableId),
  ]);

  tableFields.forEach((field) => {
    if (!fields.value.find((f) => f.id === field.id)) {
      fields.value.push(field);
    }
  });

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

  debouncedSaveWidgets();
}

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

function renderWidget(widget: WidgetConfig) {
  const container = chartContainers.value.get(widget.id);
  if (!container) return;

  const widgetRecords = records.value.filter(
    (r) => r.tableId === widget.tableId,
  );
  const widgetFields = fields.value.filter((f) => f.tableId === widget.tableId);

  if (!widget.fieldId || widgetRecords.length === 0) {
    container.innerHTML = `
      <div class="widget-empty-state">
        <div class="empty-icon-wrapper">
          <el-icon :size="32"><DataAnalysis /></el-icon>
        </div>
        <span class="empty-text">请配置数据源</span>
        <span class="empty-hint">选择数据表和字段以开始</span>
      </div>
    `;
    return;
  }

  const { labels, values } = processChartData(
    widgetRecords,
    widgetFields,
    widget.groupBy,
    widget.fieldId,
    widget.aggregation,
  );

  if (widget.type === "number") {
    const total = values.reduce((a, b) => a + b, 0);
    const formattedValue = formatLargeNumber(total);
    const color = widget.config?.colors?.[0] || freshColors.primary;

    container.innerHTML = `
      <div class="number-card" style="--number-color: ${color}">
        <div class="number-value">${formattedValue}</div>
        <div class="number-label">${widget.title}</div>
        ${values.length > 1 ? `<div class="number-detail">共 ${values.length} 项数据</div>` : ""}
      </div>
    `;
    return;
  }

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
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: freshColors.gray200,
      borderWidth: 1,
      padding: [12, 16],
      textStyle: {
        color: freshColors.gray700,
        fontSize: 13,
      },
      extraCssText: "box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); border-radius: 8px;",
      formatter: (params: any) => {
        if (Array.isArray(params)) {
          const p = params[0];
          return `<div style="font-weight: 600; margin-bottom: 4px;">${p.name}</div><div style="color: ${freshColors.primary}; font-weight: 500;">${formatLargeNumber(p.value)}</div>`;
        }
        return `<div style="font-weight: 600; margin-bottom: 4px;">${params.name}</div><div style="color: ${freshColors.primary}; font-weight: 500;">${formatLargeNumber(params.value)} (${params.percent}%)</div>`;
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
              textStyle: { color: freshColors.gray600, fontSize: 12 },
            }
          : undefined,
        xAxis: {
          type: "category",
          data: labels,
          axisLabel: {
            rotate: labels.length > 6 ? 45 : 0,
            interval: 0,
            color: freshColors.gray500,
            fontSize: 11,
          },
          axisLine: { lineStyle: { color: freshColors.gray200 } },
          axisTick: { show: false },
        },
        yAxis: {
          type: "value",
          axisLabel: {
            formatter: (value: number) => formatLargeNumber(value),
            color: freshColors.gray500,
            fontSize: 11,
          },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { lineStyle: { color: freshColors.gray100, type: "dashed" } },
        },
        series: [
          {
            name: widget.title,
            type: "bar",
            data: values,
            barWidth: "50%",
            itemStyle: {
              borderRadius: [6, 6, 0, 0],
            },
            label: widget.config?.showLabel
              ? {
                  show: true,
                  position: "top",
                  formatter: (p: any) => formatLargeNumber(p.value),
                  color: freshColors.gray600,
                  fontSize: 11,
                  fontWeight: 500,
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
              textStyle: { color: freshColors.gray600, fontSize: 12 },
            }
          : undefined,
        xAxis: {
          type: "category",
          data: labels,
          boundaryGap: widget.type === "area",
          axisLabel: {
            color: freshColors.gray500,
            fontSize: 11,
          },
          axisLine: { lineStyle: { color: freshColors.gray200 } },
          axisTick: { show: false },
        },
        yAxis: {
          type: "value",
          axisLabel: {
            formatter: (value: number) => formatLargeNumber(value),
            color: freshColors.gray500,
            fontSize: 11,
          },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { lineStyle: { color: freshColors.gray100, type: "dashed" } },
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
                    opacity: 0.15,
                    color: new (echarts as any).graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: colors[0] },
                      { offset: 1, color: "rgba(255,255,255,0)" },
                    ]),
                  }
                : undefined,
            symbol: "circle",
            symbolSize: 8,
            lineStyle: {
              width: 3,
              shadowColor: "rgba(0,0,0,0.1)",
              shadowBlur: 8,
              shadowOffsetY: 4,
            },
            itemStyle: {
              borderWidth: 2,
              borderColor: "#fff",
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
              textStyle: { color: freshColors.gray600, fontSize: 11 },
              itemWidth: 10,
              itemHeight: 10,
              itemGap: 12,
            }
          : undefined,
        series: [
          {
            type: "pie",
            radius: ["45%", "75%"],
            center: widget.config?.showLegend ? ["38%", "50%"] : ["50%", "50%"],
            data: labels.map((label, i) => ({
              name: label,
              value: values[i],
            })),
            emphasis: {
              itemStyle: {
                shadowBlur: 20,
                shadowOffsetX: 0,
                shadowColor: "rgba(0, 0, 0, 0.2)",
              },
              scale: true,
              scaleSize: 8,
            },
            itemStyle: {
              borderRadius: 6,
              borderColor: "#fff",
              borderWidth: 2,
            },
            label: widget.config?.showLabel
              ? {
                  show: true,
                  formatter: "{b}\n{c}",
                  color: freshColors.gray600,
                  fontSize: 11,
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
        xAxis: {
          type: "category",
          data: labels,
          axisLabel: { color: freshColors.gray500, fontSize: 11 },
          axisLine: { lineStyle: { color: freshColors.gray200 } },
          axisTick: { show: false },
        },
        yAxis: {
          type: "value",
          axisLabel: { formatter: (value: number) => formatLargeNumber(value), color: freshColors.gray500, fontSize: 11 },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { lineStyle: { color: freshColors.gray100, type: "dashed" } },
        },
        series: [
          {
            type: "scatter",
            data: values,
            symbolSize: (val: number) => Math.min(Math.max(val / 10, 10), 50),
            itemStyle: {
              shadowBlur: 10,
              shadowColor: "rgba(0,0,0,0.1)",
              shadowOffsetY: 4,
            },
          },
        ],
      };

    default:
      return baseOption;
  }
}

function getAggregationLabel(aggregation: string): string {
  return (
    aggregationTypes.find((a) => a.value === aggregation)?.label || aggregation
  );
}

function getFieldById(fieldId: string): FieldEntity | undefined {
  return fields.value.find((f) => f.id === fieldId);
}

function getTableById(tableId: string): TableEntity | undefined {
  return tables.value.find((t) => t.id === tableId);
}

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

  const dw = Math.round(dx / 50);
  const dh = Math.round(dy / 30);

  widget.position.w = Math.max(2, Math.min(12, resizeStart.value.w + dw));
  widget.position.h = Math.max(2, Math.min(8, resizeStart.value.h + dh));

  nextTick(() => {
    renderWidget(widget);
  });
}

function stopResize() {
  if (resizingWidget.value) {
    debouncedSaveWidgets();
  }
  resizingWidget.value = null;
  document.removeEventListener("mousemove", onResize);
  document.removeEventListener("mouseup", stopResize);
}

watch(
  widgets,
  () => {
    nextTick(() => {
      widgets.value.forEach((widget) => renderWidget(widget));
    });
  },
  { deep: true },
);

watch(selectedWidget, (widget) => {
  if (widget) {
    handleTableChange(widget.tableId);
  }
});

function handleResize() {
  chartRefs.value.forEach((chart) => chart.resize());
}

onMounted(() => {
  loadTables();
  loadDashboards();
  window.addEventListener("resize", handleResize);
});

watch(
  () => [route.params.id, route.params.dashboardId],
  ([newBaseId, newDashboardId], [oldBaseId, oldDashboardId]) => {
    if (newBaseId !== oldBaseId && newBaseId) {
      loadTables();
      loadDashboards();
    } else if (newDashboardId !== oldDashboardId && newDashboardId) {
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

  if (saveTimeout.value) {
    clearTimeout(saveTimeout.value);
  }

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
    <!-- 骨架屏加载状态 -->
    <div v-if="isLoading" class="skeleton-overlay">
      <div class="skeleton-container">
        <div class="skeleton-header">
          <div class="skeleton-title"></div>
          <div class="skeleton-actions">
            <div class="skeleton-btn"></div>
            <div class="skeleton-btn"></div>
          </div>
        </div>
        <div class="skeleton-grid">
          <div v-for="i in skeletonCount" :key="i" class="skeleton-card">
            <div class="skeleton-card-header">
              <div class="skeleton-text"></div>
              <div class="skeleton-text short"></div>
            </div>
            <div class="skeleton-card-body">
              <div class="skeleton-chart"></div>
            </div>
          </div>
        </div>
      </div>
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
              <div class="selector-icon">
                <el-icon><DataAnalysis /></el-icon>
              </div>
              <span class="dashboard-name">{{
                currentDashboard?.name || "选择仪表盘"
              }}</span>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </el-button>
          </el-dropdown>

          <el-divider direction="vertical" class="toolbar-divider" />

          <el-dropdown @command="addWidget">
            <el-button type="primary" class="add-widget-btn">
              <el-icon><Plus /></el-icon>
              <span>添加组件</span>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu class="widget-type-menu">
                <el-dropdown-item
                  v-for="type in widgetTypes"
                  :key="type.value"
                  :command="type.value">
                  <div class="widget-type-item">
                    <div class="widget-type-icon" :style="{ backgroundColor: freshColors.primaryLight }">
                      <el-icon :size="18"><component :is="type.icon" /></el-icon>
                    </div>
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
            class="share-btn"
            @click="openShareDialog">
            <el-icon><Share /></el-icon>
            <span>分享</span>
          </el-button>
          <el-button
            v-if="currentDashboard"
            text
            class="toolbar-btn"
            @click="
              isEditingDashboard = true;
              isCreatingDashboard = false;
              dashboardForm = {
                name: currentDashboard.name,
                description: currentDashboard.description || '',
              };
            ">
            <el-icon><Edit /></el-icon>
            <span>编辑</span>
          </el-button>
          <el-button
            v-if="currentDashboard"
            text
            class="toolbar-btn"
            @click="duplicateDashboard(currentDashboard)">
            <el-icon><CopyDocument /></el-icon>
            <span>复制</span>
          </el-button>
          <el-button text class="toolbar-btn" @click="showDashboardManager = true">
            <el-icon><Management /></el-icon>
            <span>管理</span>
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
                  <span class="subtitle-dot">·</span>
                  {{ getAggregationLabel(widget.aggregation) }}
                </span>
              </div>
              <div class="widget-actions">
                <el-button
                  link
                  size="small"
                  class="delete-btn"
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
              :class="{ active: resizingWidget === widget.id }"
              @mousedown.stop="startResize($event, widget)">
              <el-icon><FullScreen /></el-icon>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="widgets.length === 0" class="empty-dashboard">
            <div class="empty-illustration">
              <svg viewBox="0 0 200 160" fill="none">
                <rect x="30" y="40" width="140" height="100" rx="12" fill="#EFF6FF" stroke="#3B82F6" stroke-width="2" stroke-dasharray="8 4"/>
                <rect x="50" y="60" width="60" height="8" rx="4" fill="#3B82F6" opacity="0.3"/>
                <rect x="50" y="80" width="100" height="6" rx="3" fill="#9CA3AF" opacity="0.3"/>
                <rect x="50" y="95" width="80" height="6" rx="3" fill="#9CA3AF" opacity="0.3"/>
                <rect x="50" y="110" width="90" height="6" rx="3" fill="#9CA3AF" opacity="0.3"/>
                <circle cx="150" cy="50" r="15" fill="#10B981" opacity="0.2"/>
                <path d="M144 50L148 54L156 46" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h3 class="empty-title">开始创建您的仪表盘</h3>
            <p class="empty-desc">添加图表组件，让数据可视化呈现</p>
            <p v-if="!currentDashboard" class="empty-hint">
              请先创建一个仪表盘
            </p>
            <el-button
              v-if="!currentDashboard"
              type="primary"
              class="create-dashboard-btn"
              @click="isEditingDashboard = true">
              <el-icon><Plus /></el-icon>
              创建仪表盘
            </el-button>
            <el-button
              v-else
              type="primary"
              class="create-dashboard-btn"
              @click="addWidget('bar')">
              <el-icon><Plus /></el-icon>
              添加第一个组件
            </el-button>
          </div>
        </div>

        <!-- 配置面板 -->
        <div v-if="selectedWidget" class="config-panel">
          <div class="panel-header">
            <div class="panel-title-wrapper">
              <div class="panel-icon">
                <el-icon><Setting /></el-icon>
              </div>
              <h3>组件配置</h3>
            </div>
            <div class="panel-actions">
              <el-tag v-if="hasUnsavedChanges" size="small" type="warning" effect="light"
                >未保存</el-tag
              >
              <el-tag v-else-if="isSaving" size="small" type="info" effect="light"
                >保存中...</el-tag
              >
              <el-tag v-else size="small" type="success" effect="light">已保存</el-tag>
              <el-button link class="close-btn" @click="selectedWidget = null">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>

          <el-scrollbar class="panel-content">
            <el-form label-position="top" size="small">
              <!-- 基础配置 -->
              <div class="config-section">
                <div class="section-title">
                  <span class="section-icon">📋</span>
                  基础配置
                </div>

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
                <div class="section-title">
                  <span class="section-icon">📊</span>
                  数据配置
                </div>

                <el-form-item label="分组字段 (可选)">
                  <el-select
                    v-model="selectedWidget.groupBy"
                    clearable
                    placeholder="不分组"
                    @change="debouncedSaveWidgets()">
                    <el-option
                      v-for="field in fields.filter(
                        (f) => f.tableId === selectedWidget!.tableId,
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
                    v-model="selectedWidget!.fieldId"
                    placeholder="选择字段"
                    @change="debouncedSaveWidgets()">
                    <el-option
                      v-for="field in fields.filter(
                        (f) => f.tableId === selectedWidget!.tableId,
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
                <div class="section-title">
                  <span class="section-icon">🎨</span>
                  样式配置
                </div>

                <el-form-item
                  label="显示图例"
                  v-if="
                    selectedWidget!.type !== 'number' &&
                    selectedWidget!.type !== 'table'
                  ">
                  <el-switch
                    v-model="(selectedWidget!.config as any).showLegend"
                    @change="debouncedSaveWidgets()" />
                </el-form-item>

                <el-form-item
                  label="显示数值标签"
                  v-if="
                    selectedWidget!.type === 'bar' ||
                    selectedWidget!.type === 'pie'
                  ">
                  <el-switch
                    v-model="(selectedWidget!.config as any).showLabel"
                    @change="debouncedSaveWidgets()" />
                </el-form-item>

                <el-form-item
                  label="平滑曲线"
                  v-if="
                    selectedWidget!.type === 'line' ||
                    selectedWidget!.type === 'area'
                  ">
                  <el-switch
                    v-model="(selectedWidget!.config as any).smooth"
                    @change="debouncedSaveWidgets()" />
                </el-form-item>
              </div>

              <!-- 组件大小 -->
              <div class="config-section">
                <div class="section-title">
                  <span class="section-icon">📐</span>
                  组件大小
                </div>

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
                  class="save-btn">
                  <el-icon><Check /></el-icon>
                  <span>{{
                    isSaving
                      ? "保存中..."
                      : hasUnsavedChanges
                        ? "立即保存"
                        : "已保存"
                  }}</span>
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
        width="680px"
        destroy-on-close
        class="dashboard-manager-dialog">
        <div class="dashboard-manager">
          <div class="manager-header">
            <el-button
              type="primary"
              class="create-btn"
              @click="
                isEditingDashboard = true;
                isCreatingDashboard = true;
                dashboardForm = { name: '', description: '' };
              ">
              <el-icon><Plus /></el-icon>
              新建仪表盘
            </el-button>
          </div>

          <el-table :data="dashboards" style="width: 100%" class="manager-table">
            <el-table-column prop="name" label="名称" min-width="160">
              <template #default="{ row }">
                <div class="dashboard-name-cell">
                  <div class="dashboard-icon">
                    <el-icon><DataAnalysis /></el-icon>
                  </div>
                  <span>{{ row.name }}</span>
                  <el-tag
                    v-if="row.id === currentDashboard?.id"
                    size="small"
                    type="primary"
                    effect="light"
                    >当前</el-tag
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
            <el-table-column label="操作" width="180" fixed="right">
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
        width="480px"
        destroy-on-close
        class="dashboard-form-dialog"
        @closed="isCreatingDashboard = false">
        <el-form label-position="top" class="compact-form">
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
            class="confirm-btn"
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
        destroy-on-close
        class="share-dialog">
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
                class="generate-btn"
                :loading="isCreatingShare"
                @click="createShare">
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
                  <el-button @click="copyShareUrl" class="copy-btn">
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
              <el-tag v-if="currentShare.expiresAt" size="small" type="info" effect="light">
                有效期至：{{
                  new Date(currentShare.expiresAt).toLocaleString()
                }}
              </el-tag>
              <el-tag v-else size="small" type="info" effect="light">永久有效</el-tag>
              <el-tag
                v-if="currentShare.maxAccessCount"
                size="small"
                type="warning"
                effect="light">
                限 {{ currentShare.maxAccessCount }} 次访问
              </el-tag>
            </div>
          </div>

          <!-- 已有的分享链接 -->
          <div v-if="existingShares.length > 0" class="share-list-section">
            <el-divider />
            <h4>已有的分享链接</h4>
            <el-table :data="existingShares" size="small" style="width: 100%">
              <el-table-column label="创建时间" width="130">
                <template #default="{ row }">
                  {{ new Date(row.createdAt).toLocaleDateString() }}
                </template>
              </el-table-column>
              <el-table-column label="有效期" width="110">
                <template #default="{ row }">
                  <span v-if="row.expiresAt">{{
                    formatExpireTime(row.expiresAt)
                  }}</span>
                  <span v-else>永久</span>
                </template>
              </el-table-column>
              <el-table-column label="访问次数" width="90">
                <template #default="{ row }">
                  {{ row.currentAccessCount }}
                  <span v-if="row.maxAccessCount"
                    >/ {{ row.maxAccessCount }}</span
                  >
                </template>
              </el-table-column>
              <el-table-column label="密码" width="70">
                <template #default="{ row }">
                  <el-tag v-if="row.accessCode" size="small" type="warning" effect="light"
                    >有</el-tag
                  >
                  <el-tag v-else size="small" type="info" effect="light">无</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="130">
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
  Check,
  Share,
  Link,
  Setting,
} from "@element-plus/icons-vue";

export default {
  name: "DashboardView",
};
</script>

<style lang="scss" scoped>
// 清新配色变量
$primary: #3B82F6;
$primary-light: #EFF6FF;
$primary-dark: #2563EB;
$success: #10B981;
$warning: #F59E0B;
$danger: #EF4444;
$gray-50: #F9FAFB;
$gray-100: #F3F4F6;
$gray-200: #E5E7EB;
$gray-300: #D1D5DB;
$gray-400: #9CA3AF;
$gray-500: #6B7280;
$gray-600: #4B5563;
$gray-700: #374151;
$gray-800: #1F2937;

.dashboard-view {
  display: flex;
  height: 100%;
  background: linear-gradient(180deg, $gray-50 0%, #FFFFFF 100%);
  position: relative;
}

// 骨架屏样式
.skeleton-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(180deg, $gray-50 0%, #FFFFFF 100%);
  z-index: 1000;
  overflow: hidden;
}

.skeleton-container {
  padding: 24px;
  height: 100%;
}

.skeleton-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.skeleton-title {
  width: 160px;
  height: 24px;
  background: linear-gradient(90deg, $gray-200 25%, $gray-100 50%, $gray-200 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: shimmer 1.5s infinite;
}

.skeleton-actions {
  display: flex;
  gap: 12px;
}

.skeleton-btn {
  width: 80px;
  height: 36px;
  background: linear-gradient(90deg, $gray-200 25%, $gray-100 50%, $gray-200 75%);
  background-size: 200% 100%;
  border-radius: 8px;
  animation: shimmer 1.5s infinite;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 80px;
  gap: 16px;
}

.skeleton-card {
  grid-column: span 6;
  grid-row: span 4;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.skeleton-card-header {
  margin-bottom: 16px;
}

.skeleton-text {
  width: 120px;
  height: 16px;
  background: linear-gradient(90deg, $gray-200 25%, $gray-100 50%, $gray-200 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.5s infinite;
  margin-bottom: 8px;

  &.short {
    width: 80px;
    height: 12px;
  }
}

.skeleton-card-body {
  height: calc(100% - 60px);
}

.skeleton-chart {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, $gray-100 25%, $gray-50 50%, $gray-100 75%);
  background-size: 200% 100%;
  border-radius: 8px;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.dashboard-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// 工具栏
.dashboard-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid $gray-200;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.dashboard-selector {
  font-size: 16px;
  font-weight: 600;
  color: $gray-800;
  padding: 8px 12px;
  border-radius: 10px;
  transition: all 0.2s ease;

  &:hover {
    background: $gray-100;
  }

  .selector-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
    border-radius: 8px;
    color: white;
    margin-right: 10px;
  }

  .dashboard-name {
    margin: 0 8px;
  }

  .dropdown-icon {
    font-size: 12px;
    color: $gray-400;
  }
}

.toolbar-divider {
  height: 24px;
  background: $gray-200;
}

.add-widget-btn {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-weight: 500;
  background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
  border: none;
  box-shadow: 0 4px 14px rgba($primary, 0.35);
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba($primary, 0.45);
  }

  .el-icon {
    margin-right: 6px;
  }

  .dropdown-icon {
    margin-left: 6px;
    margin-right: 0;
  }
}

.share-btn {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-weight: 500;
  background: linear-gradient(135deg, $success 0%, #34D399 100%);
  border: none;
  color: white;
  box-shadow: 0 4px 14px rgba($success, 0.35);
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba($success, 0.45);
    color: white;
  }

  .el-icon {
    margin-right: 6px;
  }
}

.toolbar-btn {
  height: 40px;
  padding: 0 12px;
  border-radius: 10px;
  color: $gray-600;
  transition: all 0.2s ease;

  &:hover {
    background: $gray-100;
    color: $gray-800;
  }

  .el-icon {
    margin-right: 4px;
  }
}

// 组件类型菜单
.widget-type-menu {
  padding: 8px;

  .widget-type-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 4px;

    .widget-type-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      color: $primary;
    }

    .widget-type-info {
      .widget-type-name {
        font-weight: 600;
        color: $gray-800;
        font-size: 14px;
      }

      .widget-type-desc {
        font-size: 12px;
        color: $gray-500;
        margin-top: 2px;
      }
    }
  }
}

// 内容区域
.dashboard-content {
  flex: 1;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  min-height: 0;
}

// 组件网格
.widgets-grid {
  flex: 1;
  padding: 24px;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 80px;
  gap: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  align-content: start;
  min-height: 0;
}

// 组件卡片 - 清新风格
.widget-card {
  background: white;
  border-radius: 12px;
  border: 1px solid $gray-200;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  min-height: 160px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.1);
    border-color: $gray-300;

    .widget-actions {
      opacity: 1;
      transform: translateY(0);
    }

    .resize-handle {
      opacity: 1;
    }
  }

  &.selected {
    border-color: $primary;
    box-shadow: 0 0 0 3px rgba($primary, 0.15), 0 12px 24px -8px rgba(0, 0, 0, 0.1);
  }

  &.resizing {
    opacity: 0.85;
    border-color: $primary;
    box-shadow: 0 0 0 3px rgba($primary, 0.25);
    cursor: se-resize;
  }
}

.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid $gray-100;
  background: linear-gradient(180deg, $gray-50 0%, white 100%);

  .widget-title-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;

    .widget-title {
      font-weight: 600;
      color: $gray-800;
      font-size: 15px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .widget-subtitle {
      font-size: 12px;
      color: $gray-500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: flex;
      align-items: center;
      gap: 4px;

      .subtitle-dot {
        color: $gray-400;
      }
    }
  }

  .widget-actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transform: translateY(4px);
    transition: all 0.2s ease;

    .delete-btn {
      padding: 6px;
      color: $gray-400;
      transition: all 0.2s;

      &:hover {
        color: $danger;
        background: rgba($danger, 0.1);
      }
    }
  }
}

.widget-body {
  flex: 1;
  padding: 16px;
  min-height: 0;
  position: relative;
}

// 调整大小手柄
.resize-handle {
  position: absolute;
  right: 6px;
  bottom: 6px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: se-resize;
  color: $gray-400;
  opacity: 0;
  transition: all 0.2s ease;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);

  &:hover,
  &.active {
    color: $primary;
    background: $primary-light;
  }
}

// 空状态 - 插画风格
.empty-dashboard {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  text-align: center;

  .empty-illustration {
    width: 200px;
    height: 160px;
    margin-bottom: 24px;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .empty-title {
    font-size: 20px;
    font-weight: 600;
    color: $gray-800;
    margin: 0 0 8px;
  }

  .empty-desc {
    font-size: 14px;
    color: $gray-500;
    margin: 0 0 16px;
  }

  .empty-hint {
    color: $gray-400;
    font-size: 13px;
    margin-bottom: 20px;
  }

  .create-dashboard-btn {
    height: 44px;
    padding: 0 24px;
    border-radius: 10px;
    font-weight: 500;
    background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
    border: none;
    box-shadow: 0 4px 14px rgba($primary, 0.35);
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba($primary, 0.45);
    }

    .el-icon {
      margin-right: 8px;
    }
  }
}

// 组件内空状态
.widget-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 20px;

  .empty-icon-wrapper {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $gray-100;
    border-radius: 14px;
    color: $gray-400;
    margin-bottom: 12px;
  }

  .empty-text {
    font-size: 14px;
    font-weight: 500;
    color: $gray-600;
    margin-bottom: 4px;
  }

  .empty-hint {
    font-size: 12px;
    color: $gray-400;
  }
}

// 配置面板
.config-panel {
  width: 320px;
  background: white;
  border-left: 1px solid $gray-200;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100%;
  overflow: hidden;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.03);

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid $gray-100;
    flex-shrink: 0;
    background: linear-gradient(180deg, $gray-50 0%, white 100%);

    .panel-title-wrapper {
      display: flex;
      align-items: center;
      gap: 10px;

      .panel-icon {
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: $primary-light;
        border-radius: 8px;
        color: $primary;
      }

      h3 {
        font-size: 15px;
        font-weight: 600;
        color: $gray-800;
        margin: 0;
      }
    }

    .panel-actions {
      display: flex;
      align-items: center;
      gap: 8px;

      .close-btn {
        padding: 6px;
        color: $gray-400;
        transition: all 0.2s;

        &:hover {
          color: $gray-600;
          background: $gray-100;
        }
      }
    }
  }

  .panel-content {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    min-height: 0;
  }
}

// 配置区域
.config-section {
  margin-bottom: 24px;

  .section-title {
    font-size: 13px;
    font-weight: 600;
    color: $gray-700;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid $gray-100;
    display: flex;
    align-items: center;
    gap: 6px;

    .section-icon {
      font-size: 14px;
    }
  }

  &.save-section {
    margin-top: 32px;
    padding-top: 20px;
    border-top: 1px solid $gray-200;

    .save-btn {
      width: 100%;
      height: 44px;
      border-radius: 10px;
      font-weight: 500;
      background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
      border: none;
      box-shadow: 0 4px 14px rgba($primary, 0.35);
      transition: all 0.3s ease;

      &:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba($primary, 0.45);
      }

      &:disabled {
        background: $gray-300;
        box-shadow: none;
      }

      .el-icon {
        margin-right: 6px;
      }
    }
  }
}

.field-icon {
  margin-right: 6px;
  font-size: 14px;
  color: $gray-400;
}

.aggregation-option {
  display: flex;
  flex-direction: column;

  .aggregation-desc {
    font-size: 12px;
    color: $gray-400;
  }
}

.validation-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 12px;
  font-size: 12px;
  color: $warning;
  background: rgba($warning, 0.08);
  border-radius: 8px;
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
    font-size: 52px;
    font-weight: 700;
    line-height: 1.2;
    background: linear-gradient(135deg, var(--number-color) 0%, lighten-color(var(--number-color), 20%) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .number-label {
    font-size: 15px;
    color: $gray-600;
    margin-top: 12px;
    font-weight: 500;
  }

  .number-detail {
    font-size: 13px;
    color: $gray-400;
    margin-top: 6px;
  }
}

// 表格组件样式
.table-widget {
  height: 100%;
  overflow: auto;

  .data-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;

    th,
    td {
      padding: 10px 12px;
      text-align: left;
      font-size: 13px;
    }

    th {
      font-weight: 600;
      color: $gray-600;
      background: $gray-50;
      position: sticky;
      top: 0;
      border-bottom: 1px solid $gray-200;

      &:first-child {
        border-radius: 8px 0 0 0;
      }

      &:last-child {
        border-radius: 0 8px 0 0;
      }
    }

    td {
      color: $gray-700;
      border-bottom: 1px solid $gray-100;

      .table-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
      }
    }

    tr:last-child td {
      border-bottom: none;

      &:first-child {
        border-radius: 0 0 0 8px;
      }

      &:last-child {
        border-radius: 0 0 8px 0;
      }
    }

    .value-cell {
      font-weight: 600;
      text-align: right;
      color: $gray-800;
    }
  }
}

// 仪表盘管理器对话框
.dashboard-manager-dialog {
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

.dashboard-manager {
  .manager-header {
    margin-bottom: 20px;

    .create-btn {
      height: 40px;
      padding: 0 16px;
      border-radius: 10px;
      font-weight: 500;
      background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
      border: none;
      box-shadow: 0 4px 14px rgba($primary, 0.35);
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba($primary, 0.45);
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

.dashboard-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;

  .dashboard-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $primary-light;
    border-radius: 8px;
    color: $primary;
  }

  .el-tag {
    margin-left: 6px;
  }
}

// 仪表盘表单对话框
.dashboard-form-dialog {
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

  :deep(.el-dialog__footer) {
    padding: 16px 24px;
    border-top: 1px solid $gray-100;
  }
}

.compact-form {
  .el-form-item {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(.el-form-item__label) {
    font-size: 13px;
    font-weight: 500;
    color: $gray-700;
    padding-bottom: 6px;
  }
}

.confirm-btn {
  height: 40px;
  padding: 0 20px;
  border-radius: 10px;
  font-weight: 500;
  background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
  border: none;
  box-shadow: 0 4px 14px rgba($primary, 0.35);
  transition: all 0.3s ease;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba($primary, 0.45);
  }

  &:disabled {
    background: $gray-300;
    box-shadow: none;
  }
}

// 分享对话框
.share-dialog {
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

.share-dialog-content {
  h4 {
    font-size: 15px;
    font-weight: 600;
    color: $gray-800;
    margin: 0 0 16px 0;
  }

  .share-create-section {
    margin-bottom: 24px;

    .generate-btn {
      width: 100%;
      height: 44px;
      border-radius: 10px;
      font-weight: 500;
      background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
      border: none;
      box-shadow: 0 4px 14px rgba($primary, 0.35);
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba($primary, 0.45);
      }

      .el-icon {
        margin-right: 6px;
      }
    }
  }

  .share-result-section {
    margin-bottom: 24px;

    .share-link-box {
      margin-bottom: 16px;

      .share-link-input {
        :deep(.el-input__wrapper) {
          border-radius: 10px 0 0 10px;
          box-shadow: 0 0 0 1px $gray-200 inset;
        }

        :deep(.el-input__inner) {
          font-family: monospace;
          font-size: 13px;
          color: $gray-700;
        }

        :deep(.el-input-group__append) {
          border-radius: 0 10px 10px 0;
          padding: 0;
          background: white;
          box-shadow: 0 0 0 1px $gray-200 inset;

          .copy-btn {
            border: none;
            background: transparent;
            color: $primary;
            font-weight: 500;
            padding: 0 16px;
            height: 100%;

            &:hover {
              background: $primary-light;
            }
          }
        }
      }
    }

    .share-access-code {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding: 12px 16px;
      background: $gray-50;
      border-radius: 10px;
      border: 1px solid $gray-200;

      .label {
        color: $gray-500;
        font-size: 13px;
      }

      .code {
        font-family: monospace;
        font-size: 18px;
        font-weight: 700;
        color: $primary;
        letter-spacing: 3px;
        flex: 1;
      }
    }

    .share-info {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
  }

  .share-list-section {
    h4 {
      margin-bottom: 16px;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .dashboard-toolbar {
    padding: 12px 16px;
    flex-wrap: wrap;
    gap: 12px;

    .toolbar-left {
      flex-wrap: wrap;
    }
  }

  .dashboard-selector {
    .selector-icon {
      display: none;
    }
  }

  .widgets-grid {
    padding: 16px;
    gap: 12px;
  }

  .config-panel {
    position: fixed;
    right: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    box-shadow: -8px 0 24px rgba(0, 0, 0, 0.15);
  }
}
</style>
