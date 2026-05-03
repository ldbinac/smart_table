<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from "vue";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import { ElDialog, ElButton, ElEmpty, ElIcon } from "element-plus";
import { Close } from "@element-plus/icons-vue";
import { fieldService, recordService, type WidgetConfig } from "@/db/services";
import type { Dashboard } from "@/db/schema";
import {
  processChartData,
  getChartColors,
  formatLargeNumber,
} from "@/utils/dashboardDataProcessor";
import { escapeHtml } from "@/utils/helpers";

const props = defineProps<{
  visible: boolean;
  dashboard: Dashboard | null;
  widgets: WidgetConfig[];
  gridColumns: 12 | 24;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const chartRefs = ref<Map<string, echarts.ECharts>>(new Map());
const chartContainers = ref<Map<string, HTMLElement>>(new Map());
const tableFieldsMap = ref<Map<string, any[]>>(new Map());
const tableRecordsMap = ref<Map<string, any[]>>(new Map());

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit("update:visible", val),
});

watch(dialogVisible, async (val) => {
  if (val) {
    const tableIds = [...new Set(props.widgets.map((w) => w.tableId).filter(Boolean))];
    for (const tableId of tableIds) {
      await loadTableData(tableId);
    }
    nextTick(() => {
      props.widgets.forEach((widget) => renderWidget(widget));
    });
  } else {
    cleanup();
  }
});

onUnmounted(() => {
  cleanup();
});

async function loadTableData(tableId: string) {
  if (tableFieldsMap.value.has(tableId) && tableRecordsMap.value.has(tableId)) {
    return;
  }
  try {
    const fields = await fieldService.getFieldsByTable(tableId);
    tableFieldsMap.value.set(tableId, fields);
    const records = await recordService.getRecordsByTable(tableId);
    tableRecordsMap.value.set(tableId, records);
  } catch (error) {
    console.error(`加载表 ${tableId} 数据失败:`, error);
    tableFieldsMap.value.set(tableId, []);
    tableRecordsMap.value.set(tableId, []);
  }
}

function cleanup() {
  chartRefs.value.forEach((chart) => chart.dispose());
  chartRefs.value.clear();
  chartContainers.value.clear();
}

function closeDialog() {
  dialogVisible.value = false;
}

function getWidgetStyle(widget: WidgetConfig): Record<string, string | number> {
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

function getBorderStyle(widget: WidgetConfig): Record<string, string> {
  const borderSize = widget.config?.borderSize || "none";
  const borderWidths: Record<string, string> = {
    none: "0px",
    narrow: "4px",
    medium: "8px",
    wide: "16px",
  };
  return {
    border: `${borderWidths[borderSize] || "0px"} solid #f0f0f0`,
    borderRadius: "12px",
    overflow: "hidden",
  };
}

function shouldShowHeader(widget: WidgetConfig): boolean {
  if (widget.type === "text") {
    return widget.config?.showHeader === true;
  }
  return widget.config?.showHeader !== false;
}

function getBodyPaddingStyle(widget: WidgetConfig): Record<string, string> {
  const borderSize = widget.config?.borderSize || "none";
  if (borderSize === "none") {
    return { padding: "0px" };
  }
  return { padding: "12px" };
}

function renderWidget(widget: WidgetConfig) {
  const container = chartContainers.value.get(widget.id);
  if (!container) return;

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

  const fields = tableFieldsMap.value.get(widget.tableId) || [];
  const records = tableRecordsMap.value.get(widget.tableId) || [];

  if (widget.type === "kpi" || widget.type === "realtime") {
    if (!widget.tableId || records.length === 0) {
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

  if (widget.type === "number") {
    const total = values.reduce((a, b) => a + b, 0);
    container.innerHTML = `
      <div class="number-card">
        <div class="number-value">${formatLargeNumber(total)}</div>
        <div class="number-label">${escapeHtml(widget.title)}</div>
      </div>
    `;
    return;
  }

  if (widget.type === "kpi") {
    renderKpiWidget(widget, container, values);
    return;
  }

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
            ${labels.map((label, i) => `
              <tr>
                <td><span class="table-dot" style="background-color: ${colors[i]}"></span>${escapeHtml(String(label))}</td>
                <td class="value-cell">${formatLargeNumber(values[i])}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
    return;
  }

  if (widget.type === "realtime") {
    renderRealtimeWidget(widget, container, labels, values);
    return;
  }

  let chart = chartRefs.value.get(widget.id);
  if (!chart) {
    chart = echarts.init(container);
    chartRefs.value.set(widget.id, chart);
  }

  const colors = widget.config?.colors?.length ? widget.config.colors : getChartColors(labels.length);
  const option = getChartOption(widget, labels, values, colors);
  chart.setOption(option, true);
}

function renderClockWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const is24Hour = config.timeFormat !== "12h";
  const timeFontSize = config.timeFontSize || 32;
  const dateFontSize = config.dateFontSize || 14;
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
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        height: 100%; background: ${backgroundColor}; border-radius: 12px; color: ${textColor}; padding: 16px;
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

function renderDateWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const now = new Date();
  const monthFontSize = config.monthFontSize || 16;
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";

  const monthYear = now.toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" });
  const weekday = now.toLocaleDateString("zh-CN", { weekday: "long" });

  container.innerHTML = `
    <div class="screen-widget date-widget" style="
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      height: 100%; background: ${backgroundColor}; border-radius: 12px; color: ${textColor}; padding: 16px;
    ">
      <div style="font-size: ${monthFontSize}px; margin-top: 4px;">${monthYear}
      ${config.showWeekday !== false ? `<span>${weekday}</span>` : ""}</div>
    </div>
  `;
}

function renderMarqueeWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const content = escapeHtml(config.content || "欢迎使用 Smart Table 数据仪表盘");
  const speed = config.speed || 2;
  const fontSize = config.fontSize || 16;
  const direction = config.direction || "left";
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";

  const animationStyle = direction === "left"
    ? `animation: marquee-left ${20 / speed}s linear infinite;`
    : `animation: marquee-right ${20 / speed}s linear infinite;`;

  container.innerHTML = `
    <div class="screen-widget marquee-widget" style="
      display: flex; align-items: center; height: 100%;
      background: ${backgroundColor}; border-radius: 12px; color: ${textColor};
      overflow: hidden; padding: 0 16px;
    ">
      <div style="white-space: nowrap; ${animationStyle} font-size: ${fontSize}px;">${content}</div>
    </div>
    <style>
      @keyframes marquee-left { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
      @keyframes marquee-right { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
    </style>
  `;
}

function renderTextWidget(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const text = escapeHtml(config.text || widget.title || "标题文字");
  const subtitle = escapeHtml(config.subtitle || "");
  const fontSize = config.fontSize || 32;
  const subtitleFontSize = config.subtitleFontSize || 16;
  const fontWeight = config.fontWeight || "bold";
  const textAlign = config.textAlign || "center";
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";
  const subtitleColor = config.subtitleColor || "rgba(0,0,0,0.6)";
  const letterSpacing = config.letterSpacing || 0;
  const lineHeight = config.lineHeight || 1.4;
  const textShadow = config.textShadow !== false;
  const textShadowColor = config.textShadowColor || "rgba(0,0,0,0.1)";
  const textShadowBlur = config.textShadowBlur || 2;

  const shadowCss = textShadow ? `text-shadow: 1px 1px ${textShadowBlur}px ${textShadowColor};` : "";

  container.innerHTML = `
    <div class="screen-widget text-widget" style="
      display: flex; flex-direction: column;
      align-items: ${textAlign === "center" ? "center" : textAlign === "left" ? "flex-start" : "flex-end"};
      justify-content: center; height: 100%;
      background: ${backgroundColor}; border-radius: 12px; color: ${textColor};
      padding: 24px; overflow: hidden; text-align: ${textAlign};
    ">
      <div style="font-size: ${fontSize}px; font-weight: ${fontWeight}; line-height: ${lineHeight};
        letter-spacing: ${letterSpacing}px; ${shadowCss} word-break: break-word;">${text}</div>
      ${subtitle ? `<div style="font-size: ${subtitleFontSize}px; color: ${subtitleColor}; margin-top: 8px;
        line-height: ${lineHeight}; letter-spacing: ${letterSpacing}px; ${shadowCss}">${subtitle}</div>` : ""}
    </div>
  `;
}

function renderKpiWidget(widget: WidgetConfig, container: HTMLElement, values: number[]) {
  const config = widget.config || {};
  const total = values.reduce((a, b) => a + b, 0);
  const formattedValue = formatLargeNumber(total);
  const prefix = escapeHtml(config.prefix || "");
  const suffix = escapeHtml(config.suffix || "");

  let trendHtml = "";
  if (config.showTrend && values.length > 1) {
    const prevValue = values[values.length - 2] || 0;
    const currentValue = values[values.length - 1] || 0;
    const trend = prevValue > 0 ? (((currentValue - prevValue) / prevValue) * 100).toFixed(1) : 0;
    const isUp = Number(trend) >= 0;
    trendHtml = `<div style="display: inline-flex; align-items: center; margin-left: 8px; font-size: 14px; color: ${isUp ? "#10B981" : "#EF4444"};">
      <span>${isUp ? "↑" : "↓"} ${Math.abs(Number(trend))}%</span></div>`;
  }

  let progressHtml = "";
  if (config.showTarget && config.targetValue) {
    const progress = Math.min(100, (total / Number(config.targetValue)) * 100);
    progressHtml = `<div style="margin-top: 12px;">
      <div style="display: flex; justify-content: space-between; font-size: 12px; color: #6B7280; margin-bottom: 4px;">
        <span>进度</span><span>${progress.toFixed(1)}%</span></div>
      <div style="height: 6px; background: #E5E7EB; border-radius: 3px; overflow: hidden;">
        <div style="width: ${progress}%; height: 100%; background: linear-gradient(90deg, #10B981, #34D399); border-radius: 3px;"></div></div></div>`;
  }

  container.innerHTML = `
    <div class="screen-widget kpi-widget" style="
      display: flex; flex-direction: column; justify-content: center; height: 100%;
      background: white; border-radius: 12px; padding: 20px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    ">
      <div style="font-size: 14px; color: #6B7280; margin-bottom: 8px;">${escapeHtml(widget.title)}</div>
      <div style="font-size: 32px; font-weight: bold; color: #111827;">${prefix}${formattedValue}${suffix}${trendHtml}</div>
      ${progressHtml}
    </div>
  `;
}

function renderRealtimeWidget(widget: WidgetConfig, container: HTMLElement, labels: string[], values: number[]) {
  const config = widget.config || {};
  const chartType = config.chartType || "line";

  let chart = chartRefs.value.get(widget.id);
  if (!chart) {
    chart = echarts.init(container);
    chartRefs.value.set(widget.id, chart);
  }

  const colors = config.colors?.length ? config.colors : ["#3B82F6", "#10B981", "#F59E0B"];

  const option: EChartsOption = {
    color: colors,
    grid: { left: "3%", right: "4%", bottom: "3%", top: "15%", containLabel: true },
    tooltip: { trigger: "axis", backgroundColor: "rgba(255, 255, 255, 0.95)", borderColor: "#E5E7EB", borderWidth: 1, textStyle: { color: "#374151", fontSize: 12 } },
    xAxis: { type: "category", data: labels, boundaryGap: chartType === "area", axisLabel: { color: "#9CA3AF", fontSize: 10 }, axisLine: { lineStyle: { color: "#E5E7EB" } } },
    yAxis: { type: "value", axisLabel: { formatter: (value: number) => formatLargeNumber(value), color: "#9CA3AF", fontSize: 10 }, splitLine: { lineStyle: { color: "#F3F4F6", type: "dashed" } } },
    series: [{ name: widget.title, type: "line", data: values, smooth: config.smooth !== false, areaStyle: chartType === "area" ? { opacity: 0.3, color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: colors[0] }, { offset: 1, color: "rgba(255,255,255,0)" }]) } : undefined, symbol: "circle", symbolSize: 6, lineStyle: { width: 2 } }],
    animation: true,
    animationDuration: 1000,
  };

  chart.setOption(option, true);
}

function renderRealtimeWidgetEmpty(widget: WidgetConfig, container: HTMLElement) {
  const config = widget.config || {};
  const backgroundColor = config.backgroundColor || "transparent";
  const textColor = config.textColor || "#000000";

  container.innerHTML = `
    <div class="screen-widget realtime-widget-empty" style="
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      height: 100%; background: ${backgroundColor}; border-radius: 12px; color: ${textColor};
      padding: 20px; text-align: center;
    ">
      <div style="font-size: 14px; opacity: 0.7; margin-bottom: 8px;">实时数据流组件</div>
      <div style="font-size: 12px; opacity: 0.5;">请配置数据表和字段以显示实时数据</div>
    </div>
  `;
}

function getChartOption(widget: WidgetConfig, labels: string[], values: number[], colors: string[]): EChartsOption {
  const baseOption: EChartsOption = {
    color: colors,
    tooltip: {
      trigger: widget.type === "pie" ? "item" : "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#E5E7EB",
      borderWidth: 1,
      padding: [12, 16],
      textStyle: { color: "#374151", fontSize: 13 },
      extraCssText: "box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); border-radius: 8px;",
    },
    grid: { left: "3%", right: "4%", bottom: "3%", top: widget.config?.showLegend ? "15%" : "10%", containLabel: true },
  };

  switch (widget.type) {
    case "bar":
      return { ...baseOption, xAxis: { type: "category", data: labels, axisLabel: { rotate: labels.length > 6 ? 45 : 0, interval: 0, color: "#9CA3AF", fontSize: 11 }, axisLine: { lineStyle: { color: "#E5E7EB" } } }, yAxis: { type: "value", axisLabel: { formatter: (value: number) => formatLargeNumber(value), color: "#9CA3AF", fontSize: 11 }, splitLine: { lineStyle: { color: "#F3F4F6", type: "dashed" } } }, series: [{ name: widget.title, type: "bar", data: values, barWidth: "50%", itemStyle: { borderRadius: [6, 6, 0, 0] } }] };
    case "line":
    case "area":
      return { ...baseOption, xAxis: { type: "category", data: labels, boundaryGap: widget.type === "area", axisLabel: { color: "#9CA3AF", fontSize: 11 }, axisLine: { lineStyle: { color: "#E5E7EB" } } }, yAxis: { type: "value", axisLabel: { formatter: (value: number) => formatLargeNumber(value), color: "#9CA3AF", fontSize: 11 }, splitLine: { lineStyle: { color: "#F3F4F6", type: "dashed" } } }, series: [{ name: widget.title, type: "line", data: values, smooth: widget.config?.smooth ?? true, areaStyle: widget.type === "area" ? { opacity: 0.15 } : undefined, symbol: "circle", symbolSize: 8, lineStyle: { width: 3 } }] };
    case "pie":
      return { ...baseOption, legend: widget.config?.showLegend ? { orient: "vertical", right: 10, top: "center", data: labels, textStyle: { color: "#6B7280", fontSize: 11 } } : undefined, series: [{ type: "pie", radius: ["45%", "75%"], center: widget.config?.showLegend ? ["38%", "50%"] : ["50%", "50%"], data: labels.map((label, i) => ({ name: label, value: values[i] })), emphasis: { itemStyle: { shadowBlur: 20, shadowOffsetX: 0, shadowColor: "rgba(0, 0, 0, 0.2)" } }, itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 }, label: widget.config?.showLabel ? { show: true, formatter: "{b}\n{c}", color: "#6B7280", fontSize: 11 } : { show: false } }] };
    default:
      return baseOption;
  }
}
</script>

<template>
  <ElDialog
    v-model="dialogVisible"
    title="仪表盘预览"
    width="100%"
    :fullscreen="true"
    :show-close="true"
    :close-on-click-modal="false"
    :close-on-press-escape="true"
    append-to-body
    destroy-on-close
    class="dashboard-preview-dialog">
    <div class="preview-content">
      <div class="preview-header">
        <h2>{{ dashboard?.name }}</h2>
        <p v-if="dashboard?.description">{{ dashboard.description }}</p>
      </div>

      <div class="preview-widgets-grid" :class="{ 'columns-24': gridColumns === 24 }">
        <div
          v-for="widget in widgets"
          :key="widget.id"
          class="preview-widget-card"
          :style="getWidgetStyle(widget)">
          <div v-if="shouldShowHeader(widget)" class="preview-widget-header">
            <span class="preview-widget-title">{{ widget.title }}</span>
          </div>
          <div
            :ref="(el) => el && chartContainers.set(widget.id, el as HTMLElement)"
            class="preview-widget-body"
            :style="{
              height: shouldShowHeader(widget) ? 'calc(100% - 44px)' : '100%',
              ...getBodyPaddingStyle(widget),
            }">
          </div>
        </div>

        <div v-if="widgets.length === 0" class="preview-empty">
          <ElEmpty description="该仪表盘暂无组件" />
        </div>
      </div>
    </div>

    <template #footer>
      <div class="preview-footer">
        <ElButton @click="closeDialog" type="danger" plain>
          <ElIcon><Close /></ElIcon>
          关闭预览
        </ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.dashboard-preview-dialog {
  :deep(.el-dialog) {
    margin: 0 !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100% !important;
    height: 100% !important;
    z-index: 2100 !important;
  }

  :deep(.el-overlay) {
    z-index: 2099 !important;
  }

  :deep(.el-dialog__header) {
    display: none;
  }

  :deep(.el-dialog__body) {
    padding: 0;
    height: 100vh;
    overflow: hidden;
  }

  :deep(.el-dialog__footer) {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 16px 24px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-top: 1px solid $gray-100;
    z-index: 10;
  }
}

.preview-content {
  width: 100%;
  height: calc(100vh - 70px);
  background-color: $bg-color;
  display: flex;
  flex-direction: column;
}

.preview-header {
  padding: 20px 24px;
  background: white;
  border-bottom: 1px solid $gray-100;

  h2 {
    font-size: 20px;
    font-weight: 600;
    color: $gray-800;
    margin: 0 0 4px 0;
  }

  p {
    font-size: 14px;
    color: $gray-500;
    margin: 0;
  }
}

.preview-widgets-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: minmax(0, 1fr);
  gap: 16px;
  padding: 16px;
  overflow: hidden;
  align-content: stretch;

  &.columns-24 {
    grid-template-columns: repeat(24, 1fr);
  }
}

.preview-widget-card {
  background-color: white;
  border-radius: 12px;
  border: 1px solid $gray-100;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.preview-widget-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid $gray-100;
  background-color: #fafafa;
  flex-shrink: 0;

  .preview-widget-title {
    font-weight: 500;
    color: $gray-800;
    font-size: 14px;
  }
}

.preview-widget-body {
  flex: 1;
  padding: 8px;
  min-height: 0;
  position: relative;
}

.preview-empty {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.preview-footer {
  display: flex;
  justify-content: center;

  .el-button {
    min-width: 120px;
  }
}
</style>
