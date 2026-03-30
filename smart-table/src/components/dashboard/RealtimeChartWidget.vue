<template>
  <div class="realtime-chart-widget" :class="{ 'dark-mode': config.darkMode }">
    <div class="chart-header">
      <div class="title-section">
        <h3 class="title">{{ config.title }}</h3>
        <span v-if="config.subtitle" class="subtitle">{{
          config.subtitle
        }}</span>
      </div>
      <div class="status-badge" :class="{ live: isLive }">
        <span class="pulse"></span>
        <span class="status-text">{{ isLive ? "LIVE" : "PAUSED" }}</span>
      </div>
    </div>

    <div class="chart-container" ref="chartContainer">
      <v-chart
        class="chart"
        :option="chartOption"
        autoresize
        @click="handleChartClick" />
    </div>

    <div class="chart-footer">
      <div class="stats-item">
        <span class="stats-label">当前值</span>
        <span class="stats-value current">{{
          formatNumber(currentValue)
        }}</span>
      </div>
      <div class="stats-item">
        <span class="stats-label">平均值</span>
        <span class="stats-value average">{{
          formatNumber(averageValue)
        }}</span>
      </div>
      <div class="stats-item">
        <span class="stats-label">最大值</span>
        <span class="stats-value max">{{ formatNumber(maxValue) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from "echarts/components";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
]);

interface ChartConfig {
  title: string;
  subtitle?: string;
  chartType?: "line" | "area";
  maxDataPoints?: number;
  updateInterval?: number;
  darkMode?: boolean;
  showArea?: boolean;
  smooth?: boolean;
  lineColor?: string;
  areaColor?: string;
  yAxisMin?: number;
  yAxisMax?: number;
  showGrid?: boolean;
}

interface ChartDataPoint {
  timestamp: number;
  value: number;
  label?: string;
}

interface ChartData {
  data?: ChartDataPoint[];
  seriesName?: string;
}

const props = defineProps<{
  config: ChartConfig;
  data?: ChartData;
}>();

const defaultConfig: Required<ChartConfig> = {
  title: "实时数据",
  subtitle: "",
  chartType: "area",
  maxDataPoints: 50,
  updateInterval: 1000,
  darkMode: false,
  showArea: true,
  smooth: true,
  lineColor: "#3b82f6",
  areaColor: "rgba(59, 130, 246, 0.3)",
  yAxisMin: 0,
  yAxisMax: 100,
  showGrid: true,
};

const mergedConfig = computed(() => ({
  ...defaultConfig,
  ...props.config,
}));

const isLive = ref(true);
const dataPoints = ref<ChartDataPoint[]>([]);
let updateTimer: number | null = null;

// 生成模拟数据（实际使用时可以从 props.data 获取）
const generateDataPoint = (): ChartDataPoint => {
  const now = Date.now();
  const baseValue = 50;
  const randomVariation = (Math.random() - 0.5) * 30;
  return {
    timestamp: now,
    value: Math.max(0, Math.min(100, baseValue + randomVariation)),
    label: new Date(now).toLocaleTimeString("zh-CN"),
  };
};

// 初始化数据
const initData = () => {
  const initialData: ChartDataPoint[] = [];
  const now = Date.now();
  for (let i = mergedConfig.value.maxDataPoints - 1; i >= 0; i--) {
    initialData.push({
      timestamp: now - i * mergedConfig.value.updateInterval,
      value: 50 + (Math.random() - 0.5) * 20,
      label: new Date(
        now - i * mergedConfig.value.updateInterval,
      ).toLocaleTimeString("zh-CN"),
    });
  }
  dataPoints.value = initialData;
};

// 更新数据
const updateData = () => {
  if (!isLive.value) return;

  const newPoint =
    props.data?.data?.[props.data.data.length - 1] || generateDataPoint();

  dataPoints.value.push(newPoint);

  // 保持数据点数量在限制范围内
  if (dataPoints.value.length > mergedConfig.value.maxDataPoints) {
    dataPoints.value.shift();
  }
};

// 统计数据
const currentValue = computed(() => {
  if (dataPoints.value.length === 0) return 0;
  return dataPoints.value[dataPoints.value.length - 1].value;
});

const averageValue = computed(() => {
  if (dataPoints.value.length === 0) return 0;
  const sum = dataPoints.value.reduce((acc, point) => acc + point.value, 0);
  return sum / dataPoints.value.length;
});

const maxValue = computed(() => {
  if (dataPoints.value.length === 0) return 0;
  return Math.max(...dataPoints.value.map((point) => point.value));
});

const formatNumber = (num: number): string => {
  return num.toFixed(2);
};

// ECharts 配置
const chartOption = computed(() => {
  const isDark = mergedConfig.value.darkMode;
  const textColor = isDark ? "#e5e7eb" : "#374151";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  return {
    backgroundColor: "transparent",
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: "10%",
      containLabel: true,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: isDark
        ? "rgba(30, 41, 59, 0.95)"
        : "rgba(255, 255, 255, 0.95)",
      borderColor: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)",
      textStyle: {
        color: textColor,
      },
      formatter: (params: any) => {
        const point = params[0];
        return `
          <div style="font-weight: 600; margin-bottom: 4px;">${point.name}</div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="display: inline-block; width: 10px; height: 10px; background: ${mergedConfig.value.lineColor}; border-radius: 50%;"></span>
            <span>${point.seriesName}: <strong>${Number(point.value).toFixed(2)}</strong></span>
          </div>
        `;
      },
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: dataPoints.value.map((point) => point.label),
      axisLine: {
        lineStyle: {
          color: gridColor,
        },
      },
      axisLabel: {
        color: isDark ? "#9ca3af" : "#6b7280",
        fontSize: 11,
        interval: Math.floor(dataPoints.value.length / 6),
      },
      axisTick: {
        show: false,
      },
    },
    yAxis: {
      type: "value",
      min: mergedConfig.value.yAxisMin,
      max: mergedConfig.value.yAxisMax,
      splitLine: {
        show: mergedConfig.value.showGrid,
        lineStyle: {
          color: gridColor,
          type: "dashed",
        },
      },
      axisLabel: {
        color: isDark ? "#9ca3af" : "#6b7280",
        fontSize: 11,
      },
    },
    series: [
      {
        name: props.data?.seriesName || "数值",
        type: "line",
        smooth: mergedConfig.value.smooth,
        symbol: "circle",
        symbolSize: 6,
        sampling: "average",
        itemStyle: {
          color: mergedConfig.value.lineColor,
        },
        lineStyle: {
          width: 3,
          color: mergedConfig.value.lineColor,
        },
        areaStyle: mergedConfig.value.showArea
          ? {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: mergedConfig.value.areaColor },
                  { offset: 1, color: "rgba(59, 130, 246, 0.01)" },
                ],
              },
            }
          : undefined,
        data: dataPoints.value.map((point) => point.value),
        animationDuration: 300,
        animationEasing: "linear",
      },
    ],
  };
});

const handleChartClick = (params: any) => {
  console.log("Chart clicked:", params);
};

// 监听外部数据变化
watch(
  () => props.data?.data,
  (newData) => {
    if (newData && newData.length > 0) {
      dataPoints.value = newData.slice(-mergedConfig.value.maxDataPoints);
    }
  },
  { deep: true },
);

onMounted(() => {
  initData();
  updateTimer = window.setInterval(
    updateData,
    mergedConfig.value.updateInterval,
  );
});

onUnmounted(() => {
  if (updateTimer) {
    clearInterval(updateTimer);
  }
});
</script>

<style scoped lang="scss">
.realtime-chart-widget {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  min-height: 360px;

  &:hover {
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  }

  &.dark-mode {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: white;

    .title {
      color: white;
    }

    .subtitle {
      color: rgba(255, 255, 255, 0.6);
    }

    .stats-label {
      color: rgba(255, 255, 255, 0.5);
    }
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;

    .title-section {
      .title {
        font-size: 16px;
        font-weight: 600;
        color: #374151;
        margin: 0 0 4px 0;
      }

      .subtitle {
        font-size: 13px;
        color: #9ca3af;
      }
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: #f3f4f6;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      color: #6b7280;
      transition: all 0.3s ease;

      &.live {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;

        .pulse {
          animation: pulse 2s ease-in-out infinite;
        }
      }

      .pulse {
        width: 8px;
        height: 8px;
        background: currentColor;
        border-radius: 50%;
      }

      .status-text {
        letter-spacing: 0.5px;
      }
    }
  }

  .chart-container {
    flex: 1;
    min-height: 240px;
    position: relative;

    .chart {
      width: 100%;
      height: 100%;
      min-height: 240px;
    }
  }

  .chart-footer {
    display: flex;
    justify-content: space-around;
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);

    .stats-item {
      text-align: center;

      .stats-label {
        display: block;
        font-size: 12px;
        color: #9ca3af;
        margin-bottom: 4px;
      }

      .stats-value {
        font-size: 18px;
        font-weight: 700;

        &.current {
          color: #3b82f6;
        }

        &.average {
          color: #10b981;
        }

        &.max {
          color: #f59e0b;
        }
      }
    }
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

// 响应式适配
@media (max-width: 768px) {
  .realtime-chart-widget {
    padding: 16px;
    min-height: 300px;

    .chart-header {
      .title {
        font-size: 14px;
      }
    }

    .chart-container {
      min-height: 180px;

      .chart {
        min-height: 180px;
      }
    }

    .chart-footer {
      .stats-item {
        .stats-value {
          font-size: 14px;
        }
      }
    }
  }
}
</style>
