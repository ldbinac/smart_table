<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { useRoute } from "vue-router";
import { dashboardShareService } from "@/db/services/dashboardShareService";
import { dashboardService } from "@/db/services/dashboardService";
import { recordService } from "@/db/services/recordService";
import { fieldService } from "@/db/services/fieldService";
import type { DashboardShare, Dashboard } from "@/db/schema";
import type { WidgetConfig } from "@/db/services/dashboardService";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import {
  processChartData,
  getChartColors,
  formatLargeNumber,
} from "@/utils/dashboardDataProcessor";
import { ElMessage } from "element-plus";

const route = useRoute();

// 清新配色方案 - 与 Dashboard.vue 保持一致
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

// 状态
const isLoading = ref(true);
const isValidating = ref(false);
const errorMessage = ref("");
const shareInfo = ref<DashboardShare | null>(null);
const dashboard = ref<Dashboard | null>(null);
const widgets = ref<WidgetConfig[]>([]);
const accessCode = ref("");
const chartRefs = ref<Map<string, echarts.ECharts>>(new Map());
const chartContainers = ref<Map<string, HTMLElement>>(new Map());

// 布局配置
const layoutType = ref<"grid" | "free">("grid");
const gridColumns = ref<12 | 24>(12);

// 验证分享链接
async function validateShare() {
  const token = route.params.token as string;
  if (!token) {
    errorMessage.value = "分享链接无效";
    isLoading.value = false;
    return;
  }

  const result = await dashboardShareService.validateShare(
    token,
    accessCode.value || undefined,
  );

  if (!result.valid) {
    if (result.share?.accessCode && !accessCode.value) {
      // 需要访问密码
      isValidating.value = true;
      isLoading.value = false;
      return;
    }
    errorMessage.value = result.error || "分享链接无效";
    isLoading.value = false;
    return;
  }

  shareInfo.value = result.share!;

  // 记录访问
  await dashboardShareService.recordAccess(result.share!.id);

  // 加载仪表盘数据
  await loadDashboard(result.share!.dashboardId);
}

// 加载仪表盘
async function loadDashboard(dashboardId: string) {
  try {
    const dashboardData = await dashboardService.getDashboard(dashboardId);
    if (!dashboardData) {
      errorMessage.value = "仪表盘不存在或已被删除";
      isLoading.value = false;
      return;
    }

    dashboard.value = dashboardData;
    widgets.value = (dashboardData.widgets || []) as WidgetConfig[];

    // 设置布局配置
    layoutType.value = dashboardData.layoutType || "grid";
    gridColumns.value = (dashboardData.gridColumns as 12 | 24) || 12;

    // 加载所有相关表的数据
    const tableIds = [...new Set(widgets.value.map((w) => w.tableId))];
    for (const tableId of tableIds) {
      await loadTableData(tableId);
    }

    isLoading.value = false;

    // 渲染组件
    nextTick(() => {
      widgets.value.forEach((widget) => renderWidget(widget));
    });
  } catch (error) {
    console.error("加载仪表盘失败:", error);
    errorMessage.value = "加载仪表盘失败";
    isLoading.value = false;
  }
}

// 表数据缓存
const tableFieldsMap = ref<Map<string, any[]>>(new Map());
const tableRecordsMap = ref<Map<string, any[]>>(new Map());

async function loadTableData(tableId: string) {
  if (tableFieldsMap.value.has(tableId) && tableRecordsMap.value.has(tableId)) {
    return;
  }

  const [fields, records] = await Promise.all([
    fieldService.getFieldsByTable(tableId),
    recordService.getRecordsByTable(tableId),
  ]);

  tableFieldsMap.value.set(tableId, fields);
  tableRecordsMap.value.set(tableId, records);
}

// 提交访问密码
async function submitAccessCode() {
  if (!accessCode.value.trim()) {
    ElMessage.warning("请输入访问密码");
    return;
  }
  isValidating.value = false;
  isLoading.value = true;
  await validateShare();
}

// 计算网格单元格尺寸 - 用于自适应布局
function calculateCellDimensions() {
  const gridContainer = document.querySelector(".widgets-grid");
  if (!gridContainer) return { cellWidth: 100, cellHeight: 80 };

  const containerRect = gridContainer.getBoundingClientRect();
  const gap = 16; // 与 gap 一致
  const columns = gridColumns.value;
  const rows = 12; // 默认行数

  // 计算单元格尺寸（减去间隙）
  const cellWidth = (containerRect.width - (columns - 1) * gap) / columns;
  const cellHeight = (containerRect.height - (rows - 1) * gap) / rows;

  return { cellWidth, cellHeight };
}

// 获取组件样式 - 支持全屏自适应
function getWidgetStyle(widget: WidgetConfig): Record<string, string | number> {
  if (layoutType.value === "free") {
    // 自由布局：使用百分比或绝对定位
    const { cellWidth, cellHeight } = calculateCellDimensions();
    const x = widget.position.x || 0;
    const y = widget.position.y || 0;
    const w = widget.position.w || 4;
    const h = widget.position.h || 4;

    return {
      position: "absolute",
      left: `${x * cellWidth + x * 16}px`,
      top: `${y * cellHeight + y * 16}px`,
      width: `${w * cellWidth + (w - 1) * 16}px`,
      height: `${h * cellHeight + (h - 1) * 16}px`,
      zIndex: widget.position.z || 1,
      ...getBorderStyle(widget),
    };
  } else {
    // 网格布局：使用 grid-area 指定位置
    const x = widget.position.x || 0;
    const y = widget.position.y || 0;
    const w = widget.position.w || 4;
    const h = widget.position.h || 4;
    return {
      gridColumn: `${x + 1} / span ${w}`,
      gridRow: `${y + 1} / span ${h}`,
      ...getBorderStyle(widget),
    };
  }
}

// 判断是否显示标题栏
// 文字组件默认隐藏标题栏，其他组件根据 showHeader 配置
function shouldShowHeader(widget: WidgetConfig): boolean {
  // 文字组件默认隐藏标题栏
  if (widget.type === "text") {
    return widget.config?.showHeader === true;
  }
  // 其他组件默认显示标题栏
  return widget.config?.showHeader !== false;
}

// 获取边框样式
function getBorderStyle(widget: WidgetConfig): Record<string, string> {
  const borderSize = widget.config?.borderSize || "none";
  const borderWidths = {
    none: "0px",
    narrow: "4px",
    medium: "8px",
    wide: "16px",
  };
  const borderWidth = borderWidths[borderSize] || "0px";

  return {
    border: `${borderWidth} solid #f0f0f0`,
    borderRadius: "12px",
    overflow: "hidden",
  };
}

// 获取内容区域 padding 样式
function getBodyPaddingStyle(widget: WidgetConfig): Record<string, string> {
  const borderSize = widget.config?.borderSize || "none";

  // 当无边框时，padding 设置为 0px
  if (borderSize === "none") {
    return { padding: "0px" };
  }

  // 有边框时，使用默认 padding
  return { padding: "12px" };
}

// 渲染组件
function renderWidget(widget: WidgetConfig) {
  const container = chartContainers.value.get(widget.id);
  if (!container) return;

  // 大屏专用组件渲染（不需要数据表）
  if (widget.type === "clock") {
    renderClockWidget(widget, container);
    return;
  }

  if (widget.type === "date") {
    renderDateWidget(widget, container);
    return;
  }

  if (widget.type === "marquee") {
    renderMarqueeWidget(widget, container);
    return;
  }

  if (widget.type === "text") {
    renderTextWidget(widget, container);
    return;
  }

  // 需要数据的组件
  const fields = tableFieldsMap.value.get(widget.tableId) || [];
  const records = tableRecordsMap.value.get(widget.tableId) || [];

  // 大屏组件 kpi 和 realtime 可以没有数据时显示默认状态
  if (widget.type === "kpi" || widget.type === "realtime") {
    if (!widget.tableId || records.length === 0) {
      // 显示默认空状态
      if (widget.type === "kpi") {
        renderKpiWidget(widget, container, [0]);
      } else {
        renderRealtimeWidgetEmpty(widget, container);
      }
      return;
    }
  } else if (!widget.fieldId || records.length === 0) {
    container.innerHTML = '<div class="widget-empty">暂无数据</div>';
    return;
  }

  const { labels, values } = processChartData(
    records,
    fields,
    widget.groupBy,
    widget.fieldId,
    widget.aggregation,
  );

  // 数字卡片
  if (widget.type === "number") {
    const total = values.reduce((a, b) => a + b, 0);
    const formattedValue = formatLargeNumber(total);

    container.innerHTML = `
      <div class="number-card">
        <div class="number-value">${formattedValue}</div>
        <div class="number-label">${widget.title}</div>
      </div>
    `;
    return;
  }

  // KPI 指标组件
  if (widget.type === "kpi") {
    renderKpiWidget(widget, container, values);
    return;
  }

  // 表格
  if (widget.type === "table") {
    const colors = getChartColors(labels.length);
    container.innerHTML = `
      <div class="table-widget">
        <table class="data-table">
          <thead>
            <tr>
              <th>${widget.groupBy ? fields.find((f: any) => f.id === widget.groupBy)?.name || "分组" : "类别"}</th>
              <th>数值</th>
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

  // 实时数据流组件
  if (widget.type === "realtime") {
    renderRealtimeWidget(widget, container, labels, values);
    return;
  }

  // 图表
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

// ==================== 大屏专用组件渲染函数 ====================

// 时钟组件
function renderClockWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const is24Hour = config.timeFormat !== "12h";
  const timeFontSize = config.timeFontSize || 32;
  const dateFontSize = config.dateFontSize || 14;
  // 背景色和文字颜色配置，默认透明背景和黑色文字
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";

  const updateClock = () => {
    const now = new Date();
    const hours = is24Hour ? now.getHours() : now.getHours() % 12 || 12;
    const minutes = now.getMinutes().toString().padStart(2, "0");
    const seconds = now.getSeconds().toString().padStart(2, "0");
    const ampm = now.getHours() >= 12 ? "PM" : "AM";

    const timeStr = is24Hour
      ? `${hours.toString().padStart(2, "0")}:${minutes}:${seconds}`
      : `${hours}:${minutes}:${seconds} ${ampm}`;

    const dateStr = now.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: config.showWeekday !== false ? "long" : undefined,
    });

    container.innerHTML = `
      <div class="screen-widget clock-widget" style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        background: ${backgroundColor};
        border-radius: 12px;
        color: ${textColor};
        padding: 16px;
      ">
        <div style="font-size: ${timeFontSize}px; font-weight: bold; font-family: 'Courier New', monospace;">${timeStr}</div>
        ${config.showDate !== false ? `<div style="font-size: ${dateFontSize}px; margin-top: 8px; opacity: 0.8;">${dateStr}</div>` : ""}
      </div>
    `;
  };

  updateClock();
  const timer = setInterval(updateClock, 1000);
  (container as any)._clockTimer = timer;
}

// 日期组件
function renderDateWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const now = new Date();
  const monthFontSize = config.monthFontSize || 16;
  // 背景色和文字颜色配置，默认透明背景和黑色文字
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";

  const day = now.getDate();
  const monthYear = now.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const weekday = now.toLocaleDateString("zh-CN", { weekday: "long" });

  container.innerHTML = `
    <div class="screen-widget date-widget" style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: ${backgroundColor};
      border-radius: 12px;
      color: ${textColor};
      padding: 16px;
    ">
      <div style="font-size: ${monthFontSize}px; margin-top: 4px;">${monthYear}
      ${config.showWeekday !== false ? `<span>${weekday}</span>` : ""}</div>
    </div>
  `;
}

// 跑马灯组件
function renderMarqueeWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const content = config.content || "欢迎使用 Smart Table 数据仪表盘";
  const speed = config.speed || 2;
  const fontSize = config.fontSize || 16;
  const direction = config.direction || "left";
  // 背景色和文字颜色配置，默认透明背景和黑色文字
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";

  const animationStyle =
    direction === "left"
      ? `animation: marquee-left ${20 / speed}s linear infinite;`
      : `animation: marquee-right ${20 / speed}s linear infinite;`;

  container.innerHTML = `
    <div class="screen-widget marquee-widget" style="
      display: flex;
      align-items: center;
      height: 100%;
      background: ${backgroundColor};
      border-radius: 12px;
      color: ${textColor};
      overflow: hidden;
      padding: 0 16px;
    ">
      <div style="
        white-space: nowrap;
        ${animationStyle}
        font-size: ${fontSize}px;
      ">${content}</div>
    </div>
    <style>
      @keyframes marquee-left {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
      }
      @keyframes marquee-right {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
      }
    </style>
  `;
}

// KPI 指标组件
function renderKpiWidget(
  widget: WidgetConfig,
  container: HTMLElement,
  values: number[],
) {
  const config = widget.config || {};
  const total = values.reduce((a, b) => a + b, 0);
  const formattedValue = formatLargeNumber(total);
  const prefix = config.prefix || "";
  const suffix = config.suffix || "";

  // 计算趋势
  let trendHtml = "";
  if (config.showTrend && values.length > 1) {
    const prevValue = values[values.length - 2] || 0;
    const currentValue = values[values.length - 1] || 0;
    const trend =
      prevValue > 0
        ? (((currentValue - prevValue) / prevValue) * 100).toFixed(1)
        : 0;
    const isUp = Number(trend) >= 0;
    trendHtml = `
      <div style="
        display: inline-flex;
        align-items: center;
        margin-left: 8px;
        font-size: 14px;
        color: ${isUp ? "#10B981" : "#EF4444"};
      ">
        <span>${isUp ? "↑" : "↓"} ${Math.abs(Number(trend))}%</span>
      </div>
    `;
  }

  // 目标值进度
  let progressHtml = "";
  if (config.showTarget && config.targetValue) {
    const progress = Math.min(100, (total / Number(config.targetValue)) * 100);
    progressHtml = `
      <div style="margin-top: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #6B7280; margin-bottom: 4px;">
          <span>进度</span>
          <span>${progress.toFixed(1)}%</span>
        </div>
        <div style="height: 6px; background: #E5E7EB; border-radius: 3px; overflow: hidden;">
          <div style="width: ${progress}%; height: 100%; background: linear-gradient(90deg, #10B981, #34D399); border-radius: 3px; transition: width 0.5s;"></div>
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="screen-widget kpi-widget" style="
      display: flex;
      flex-direction: column;
      justify-content: center;
      height: 100%;
      background: white;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    ">
      <div style="font-size: 14px; color: #6B7280; margin-bottom: 8px;">${widget.title}</div>
      <div style="font-size: 32px; font-weight: bold; color: #111827;">
        ${prefix}${formattedValue}${suffix}
        ${trendHtml}
      </div>
      ${progressHtml}
    </div>
  `;
}

// 实时数据流组件 - 与 Dashboard.vue 保持一致
function renderRealtimeWidget(
  widget: WidgetConfig,
  container: HTMLElement,
  labels: string[],
  values: number[],
) {
  const config = widget.config || {};
  const chartType = config.chartType || "line";

  // 使用 ECharts 渲染实时图表
  let chart = chartRefs.value.get(widget.id);
  if (!chart) {
    chart = echarts.init(container);
    chartRefs.value.set(widget.id, chart);
  }

  const colors = config.colors?.length
    ? config.colors
    : ["#3B82F6", "#10B981", "#F59E0B"];

  const option: EChartsOption = {
    color: colors,
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: "15%",
      containLabel: true,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: freshColors.gray200,
      borderWidth: 1,
      textStyle: { color: freshColors.gray700, fontSize: 12 },
    },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: chartType === "area",
      axisLabel: { color: freshColors.gray500, fontSize: 10 },
      axisLine: { lineStyle: { color: freshColors.gray200 } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => formatLargeNumber(value),
        color: freshColors.gray500,
        fontSize: 10,
      },
      splitLine: { lineStyle: { color: freshColors.gray100, type: "dashed" } },
    },
    series: [
      {
        name: widget.title,
        type: "line",
        data: values,
        smooth: config.smooth !== false,
        areaStyle:
          chartType === "area"
            ? {
                opacity: 0.3,
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: colors[0] },
                  { offset: 1, color: "rgba(255,255,255,0)" },
                ]),
              }
            : undefined,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { width: 2 },
      },
    ],
    animation: true,
    animationDuration: 1000,
  };

  chart.setOption(option, true);
}

// 实时数据组件空状态渲染（无数据时）- 与 Dashboard.vue 保持一致
function renderRealtimeWidgetEmpty(
  widget: WidgetConfig,
  container: HTMLElement,
) {
  const config = widget.config || {};
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";

  container.innerHTML = `
    <div class="screen-widget realtime-widget-empty" style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: ${backgroundColor};
      border-radius: 12px;
      color: ${textColor};
      padding: 20px;
      text-align: center;
    ">
      <div style="font-size: 14px; opacity: 0.7; margin-bottom: 8px;">实时数据流组件</div>
      <div style="font-size: 12px; opacity: 0.5;">请配置数据表和字段以显示实时数据</div>
    </div>
  `;
}

// 标题文字组件
function renderTextWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const text = config.text || widget.title || "标题文字";
  const subtitle = config.subtitle || "";
  const fontSize = config.fontSize || 32;
  const subtitleFontSize = config.subtitleFontSize || 16;
  const fontWeight = config.fontWeight || "bold";
  const textAlign = config.textAlign || "center";
  // 背景色和文字颜色配置，默认透明背景和黑色文字
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";
  const subtitleColor = config.subtitleColor || "rgba(0,0,0,0.6)";
  const letterSpacing = config.letterSpacing || 0;
  const lineHeight = config.lineHeight || 1.4;
  const textShadow = config.textShadow !== false;
  const textShadowColor = config.textShadowColor || "rgba(0,0,0,0.1)";
  const textShadowBlur = config.textShadowBlur || 2;

  const shadowCss = textShadow
    ? `text-shadow: 1px 1px ${textShadowBlur}px ${textShadowColor};`
    : "";

  container.innerHTML = `
    <div class="screen-widget text-widget" style="
      display: flex;
      flex-direction: column;
      align-items: ${textAlign === "center" ? "center" : textAlign === "left" ? "flex-start" : "flex-end"};
      justify-content: center;
      height: 100%;
      background: ${backgroundColor};
      border-radius: 12px;
      color: ${textColor};
      padding: 24px;
      overflow: hidden;
      text-align: ${textAlign};
    ">
      <div style="
        font-size: ${fontSize}px;
        font-weight: ${fontWeight};
        line-height: ${lineHeight};
        letter-spacing: ${letterSpacing}px;
        ${shadowCss}
        word-break: break-word;
      ">${text}</div>
      ${
        subtitle
          ? `
        <div style="
          font-size: ${subtitleFontSize}px;
          color: ${subtitleColor};
          margin-top: 8px;
          line-height: ${lineHeight};
          letter-spacing: ${letterSpacing}px;
          ${shadowCss}
        ">${subtitle}</div>
      `
          : ""
      }
    </div>
  `;
}

// 获取图表配置 - 与 Dashboard.vue 保持一致
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
      extraCssText:
        "box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); border-radius: 8px;",
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
          splitLine: {
            lineStyle: { color: freshColors.gray100, type: "dashed" },
          },
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
          splitLine: {
            lineStyle: { color: freshColors.gray100, type: "dashed" },
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
                    opacity: 0.15,
                    color: new (echarts as any).graphic.LinearGradient(
                      0,
                      0,
                      0,
                      1,
                      [
                        { offset: 0, color: colors[0] },
                        { offset: 1, color: "rgba(255,255,255,0)" },
                      ],
                    ),
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
          axisLabel: {
            formatter: (value: number) => formatLargeNumber(value),
            color: freshColors.gray500,
            fontSize: 11,
          },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: {
            lineStyle: { color: freshColors.gray100, type: "dashed" },
          },
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

// 处理窗口大小变化 - 重绘图表
function handleResize() {
  // 使用 requestAnimationFrame 优化性能
  requestAnimationFrame(() => {
    chartRefs.value.forEach((chart) => {
      chart.resize();
    });
  });
}

// 防抖函数
function debounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

// 防抖处理的重绘函数
const debouncedResize = debounce(handleResize, 200);

onMounted(() => {
  validateShare();
  window.addEventListener("resize", debouncedResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", debouncedResize);
  // 清理图表实例
  chartRefs.value.forEach((chart) => chart.dispose());
  chartRefs.value.clear();
});
</script>

<template>
  <div class="dashboard-share-view">
    <!-- 加载中 -->
    <div v-if="isLoading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 访问密码输入 -->
    <div v-else-if="isValidating" class="access-code-container">
      <el-card class="access-code-card">
        <template #header>
          <div class="card-header">
            <el-icon :size="48" color="#3370FF"><Lock /></el-icon>
            <h2>需要访问密码</h2>
            <p>此仪表盘分享链接需要密码才能访问</p>
          </div>
        </template>
        <el-input
          v-model="accessCode"
          placeholder="请输入6位访问密码"
          maxlength="6"
          size="large"
          @keyup.enter="submitAccessCode">
          <template #append>
            <el-button type="primary" @click="submitAccessCode">
              进入
            </el-button>
          </template>
        </el-input>
      </el-card>
    </div>

    <!-- 错误提示 -->
    <div v-else-if="errorMessage" class="error-container">
      <el-result
        icon="error"
        :title="errorMessage"
        sub-title="该分享链接可能已过期、被禁用或达到访问次数上限">
        <template #extra>
          <el-button type="primary" @click="$router.push('/')">
            返回首页
          </el-button>
        </template>
      </el-result>
    </div>

    <!-- 仪表盘内容 -->
    <div v-else class="dashboard-content">
      <!-- 头部信息 -->
      <div class="share-header" style="display: none">
        <div class="header-left">
          <h1>{{ dashboard?.name }}</h1>
          <p v-if="dashboard?.description">{{ dashboard.description }}</p>
        </div>
        <div class="header-right">
          <el-tag v-if="shareInfo?.permission === 'view'" type="info"
            >仅查看</el-tag
          >
          <el-tag v-else type="warning">可编辑</el-tag>
        </div>
      </div>

      <!-- 组件网格 - 自适应布局 -->
      <div
        class="widgets-grid"
        :class="{
          'columns-24': gridColumns === 24,
          'free-layout': layoutType === 'free',
        }"
        :style="layoutType === 'free' ? { position: 'relative' } : {}">
        <div
          v-for="widget in widgets"
          :key="widget.id"
          class="widget-card"
          :style="getWidgetStyle(widget)">
          <div v-if="shouldShowHeader(widget)" class="widget-header">
            <span class="widget-title">{{ widget.title }}</span>
          </div>
          <div
            :ref="
              (el) => el && chartContainers.set(widget.id, el as HTMLElement)
            "
            class="widget-body"
            :style="{
              height: shouldShowHeader(widget) ? 'calc(100% - 44px)' : '100%',
              ...getBodyPaddingStyle(widget),
            }"></div>
        </div>

        <div v-if="widgets.length === 0" class="empty-dashboard">
          <el-empty description="该仪表盘暂无组件" />
        </div>
      </div>

      <!-- 底部信息 -->
      <div class="share-footer" style="display: none">
        <p>通过 Smart Table 分享</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Lock } from "@element-plus/icons-vue";

export default {
  name: "DashboardShareView",
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.dashboard-share-view {
  min-height: 100vh;
  background-color: $bg-color;
}

// 加载中
.loading-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-xl;
}

// 访问密码
.access-code-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: $spacing-xl;

  .access-code-card {
    width: 100%;
    max-width: 400px;

    .card-header {
      text-align: center;

      h2 {
        margin: $spacing-md 0 $spacing-xs;
        font-size: $font-size-lg;
        color: $text-primary;
      }

      p {
        margin: 0;
        font-size: $font-size-sm;
        color: $text-secondary;
      }
    }
  }
}

// 错误页面
.error-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: $spacing-xl;
}

// 仪表盘内容 - 全屏自适应布局
.dashboard-content {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: $bg-color;
}

// 组件网格 - 自适应全屏
.widgets-grid {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: minmax(0, 1fr);
  gap: $spacing-md;
  padding: $spacing-md;
  overflow: hidden;
  align-content: stretch;

  // 24列网格支持
  &.columns-24 {
    grid-template-columns: repeat(24, 1fr);
  }

  // 自由布局模式
  &.free-layout {
    display: block;
    position: relative;
    overflow: auto;
  }
}

// 组件卡片 - 自适应高度
.widget-card {
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  border: 1px solid $border-color;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;

  .widget-header {
    display: flex;
    align-items: center;
    padding: $spacing-sm $spacing-md;
    border-bottom: 1px solid $border-color;
    background-color: #fafafa;
    flex-shrink: 0;

    .widget-title {
      font-weight: 500;
      color: $text-primary;
      font-size: $font-size-base;
    }
  }

  .widget-body {
    flex: 1;
    padding: $spacing-xs;
    min-height: 0;
    position: relative;
  }
}

// 空状态
.empty-dashboard {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

// 数字卡片
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
    color: $primary-color;
    line-height: 1.2;
  }

  .number-label {
    font-size: $font-size-base;
    color: $text-secondary;
    margin-top: $spacing-sm;
  }
}

// 表格
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

// 响应式适配
@media (max-width: 768px) {
  .widgets-grid {
    padding: $spacing-sm;
    gap: $spacing-sm;
  }
}

// 全屏模式优化
:fullscreen .dashboard-share-view {
  .dashboard-content {
    width: 100vw;
    height: 100vh;
  }
}
</style>
