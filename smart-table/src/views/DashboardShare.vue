<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { dashboardShareService } from '@/db/services/dashboardShareService'
import { dashboardService } from '@/db/services/dashboardService'
import { recordService } from '@/db/services/recordService'
import { fieldService } from '@/db/services/fieldService'
import type { DashboardShare, Dashboard } from '@/db/schema'
import type { WidgetConfig } from '@/db/services/dashboardService'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import {
  processChartData,
  getChartColors,
  formatLargeNumber
} from '@/utils/dashboardDataProcessor'
import { ElMessage } from 'element-plus'

const route = useRoute()

// 状态
const isLoading = ref(true)
const isValidating = ref(false)
const errorMessage = ref('')
const shareInfo = ref<DashboardShare | null>(null)
const dashboard = ref<Dashboard | null>(null)
const widgets = ref<WidgetConfig[]>([])
const accessCode = ref('')
const chartRefs = ref<Map<string, echarts.ECharts>>(new Map())
const chartContainers = ref<Map<string, HTMLElement>>(new Map())

// 验证分享链接
async function validateShare() {
  const token = route.params.token as string
  if (!token) {
    errorMessage.value = '分享链接无效'
    isLoading.value = false
    return
  }

  const result = await dashboardShareService.validateShare(token, accessCode.value || undefined)

  if (!result.valid) {
    if (result.share?.accessCode && !accessCode.value) {
      // 需要访问密码
      isValidating.value = true
      isLoading.value = false
      return
    }
    errorMessage.value = result.error || '分享链接无效'
    isLoading.value = false
    return
  }

  shareInfo.value = result.share!

  // 记录访问
  await dashboardShareService.recordAccess(result.share!.id)

  // 加载仪表盘数据
  await loadDashboard(result.share!.dashboardId)
}

// 加载仪表盘
async function loadDashboard(dashboardId: string) {
  try {
    const dashboardData = await dashboardService.getDashboard(dashboardId)
    if (!dashboardData) {
      errorMessage.value = '仪表盘不存在或已被删除'
      isLoading.value = false
      return
    }

    dashboard.value = dashboardData
    widgets.value = (dashboardData.widgets || []) as WidgetConfig[]

    // 加载所有相关表的数据
    const tableIds = [...new Set(widgets.value.map(w => w.tableId))]
    for (const tableId of tableIds) {
      await loadTableData(tableId)
    }

    isLoading.value = false

    // 渲染组件
    nextTick(() => {
      widgets.value.forEach(widget => renderWidget(widget))
    })
  } catch (error) {
    console.error('加载仪表盘失败:', error)
    errorMessage.value = '加载仪表盘失败'
    isLoading.value = false
  }
}

// 表数据缓存
const tableFieldsMap = ref<Map<string, any[]>>(new Map())
const tableRecordsMap = ref<Map<string, any[]>>(new Map())

async function loadTableData(tableId: string) {
  if (tableFieldsMap.value.has(tableId) && tableRecordsMap.value.has(tableId)) {
    return
  }

  const [fields, records] = await Promise.all([
    fieldService.getFieldsByTable(tableId),
    recordService.getRecordsByTable(tableId)
  ])

  tableFieldsMap.value.set(tableId, fields)
  tableRecordsMap.value.set(tableId, records)
}

// 提交访问密码
async function submitAccessCode() {
  if (!accessCode.value.trim()) {
    ElMessage.warning('请输入访问密码')
    return
  }
  isValidating.value = false
  isLoading.value = true
  await validateShare()
}

// 渲染组件
function renderWidget(widget: WidgetConfig) {
  const container = chartContainers.value.get(widget.id)
  if (!container) return

  const fields = tableFieldsMap.value.get(widget.tableId) || []
  const records = tableRecordsMap.value.get(widget.tableId) || []

  if (!widget.fieldId || records.length === 0) {
    container.innerHTML = '<div class="widget-empty">暂无数据</div>'
    return
  }

  const { labels, values } = processChartData(
    records,
    fields,
    widget.groupBy,
    widget.fieldId,
    widget.aggregation
  )

  // 数字卡片
  if (widget.type === 'number') {
    const total = values.reduce((a, b) => a + b, 0)
    const formattedValue = formatLargeNumber(total)

    container.innerHTML = `
      <div class="number-card">
        <div class="number-value">${formattedValue}</div>
        <div class="number-label">${widget.title}</div>
      </div>
    `
    return
  }

  // 表格
  if (widget.type === 'table') {
    const colors = getChartColors(labels.length)
    container.innerHTML = `
      <div class="table-widget">
        <table class="data-table">
          <thead>
            <tr>
              <th>${widget.groupBy ? fields.find((f: any) => f.id === widget.groupBy)?.name || '分组' : '类别'}</th>
              <th>数值</th>
            </tr>
          </thead>
          <tbody>
            ${labels.map((label, i) => `
              <tr>
                <td>
                  <span class="table-dot" style="background-color: ${colors[i]}"></span>
                  ${label}
                </td>
                <td class="value-cell">${formatLargeNumber(values[i])}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `
    return
  }

  // 图表
  let chart = chartRefs.value.get(widget.id)
  if (!chart) {
    chart = echarts.init(container)
    chartRefs.value.set(widget.id, chart)
  }

  const colors = widget.config?.colors?.length
    ? widget.config.colors
    : getChartColors(labels.length)

  const option = getChartOption(widget, labels, values, colors)
  chart.setOption(option, true)
}

// 获取图表配置
function getChartOption(
  widget: WidgetConfig,
  labels: string[],
  values: number[],
  colors: string[]
): EChartsOption {
  const baseOption: EChartsOption = {
    color: colors,
    tooltip: {
      trigger: widget.type === 'pie' ? 'item' : 'axis',
      formatter: (params: any) => {
        if (Array.isArray(params)) {
          const p = params[0]
          return `${p.name}: <b>${formatLargeNumber(p.value)}</b>`
        }
        return `${params.name}: <b>${formatLargeNumber(params.value)}</b> (${params.percent}%)`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: widget.config?.showLegend ? '15%' : '10%',
      containLabel: true
    }
  }

  switch (widget.type) {
    case 'bar':
      return {
        ...baseOption,
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: {
            rotate: labels.length > 6 ? 45 : 0,
            interval: 0
          }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: (value: number) => formatLargeNumber(value)
          }
        },
        series: [{
          type: 'bar',
          data: values,
          barWidth: '60%',
          itemStyle: {
            borderRadius: [4, 4, 0, 0]
          }
        }]
      }

    case 'line':
    case 'area':
      return {
        ...baseOption,
        xAxis: {
          type: 'category',
          data: labels,
          boundaryGap: widget.type === 'area'
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: (value: number) => formatLargeNumber(value)
          }
        },
        series: [{
          type: 'line',
          data: values,
          smooth: widget.config?.smooth ?? true,
          areaStyle: widget.type === 'area' ? { opacity: 0.3 } : undefined,
          symbol: 'circle',
          symbolSize: 8
        }]
      }

    case 'pie':
      return {
        ...baseOption,
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          data: labels.map((label, i) => ({
            name: label,
            value: values[i]
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      }

    case 'scatter':
      return {
        ...baseOption,
        xAxis: { type: 'category', data: labels },
        yAxis: {
          type: 'value',
          axisLabel: { formatter: (value: number) => formatLargeNumber(value) }
        },
        series: [{
          type: 'scatter',
          data: values,
          symbolSize: (val: number) => Math.min(Math.max(val / 10, 10), 50)
        }]
      }

    default:
      return baseOption
  }
}

onMounted(() => {
  validateShare()
})
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
          @keyup.enter="submitAccessCode"
        >
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
        sub-title="该分享链接可能已过期、被禁用或达到访问次数上限"
      >
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
      <div class="share-header">
        <div class="header-left">
          <h1>{{ dashboard?.name }}</h1>
          <p v-if="dashboard?.description">{{ dashboard.description }}</p>
        </div>
        <div class="header-right">
          <el-tag v-if="shareInfo?.permission === 'view'" type="info">仅查看</el-tag>
          <el-tag v-else type="warning">可编辑</el-tag>
        </div>
      </div>

      <!-- 组件网格 -->
      <div class="widgets-grid">
        <div
          v-for="widget in widgets"
          :key="widget.id"
          class="widget-card"
          :style="{
            gridColumn: `span ${widget.position.w}`,
            gridRow: `span ${widget.position.h}`
          }"
        >
          <div class="widget-header">
            <span class="widget-title">{{ widget.title }}</span>
          </div>
          <div
            :ref="el => el && chartContainers.set(widget.id, el as HTMLElement)"
            class="widget-body"
          ></div>
        </div>

        <div v-if="widgets.length === 0" class="empty-dashboard">
          <el-empty description="该仪表盘暂无组件" />
        </div>
      </div>

      <!-- 底部信息 -->
      <div class="share-footer">
        <p>通过 Smart Table 分享</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Lock } from '@element-plus/icons-vue'

export default {
  name: 'DashboardShareView'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

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

// 仪表盘内容
.dashboard-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.share-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: $spacing-lg;
  padding: $spacing-lg;
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

  .header-left {
    h1 {
      margin: 0 0 $spacing-xs;
      font-size: $font-size-xl;
      font-weight: 600;
      color: $text-primary;
    }

    p {
      margin: 0;
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }
}

// 组件网格
.widgets-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 80px;
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
}

// 组件卡片
.widget-card {
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  border: 1px solid $border-color;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .widget-header {
    display: flex;
    align-items: center;
    padding: $spacing-sm $spacing-md;
    border-bottom: 1px solid $border-color;
    background-color: #fafafa;

    .widget-title {
      font-weight: 500;
      color: $text-primary;
      font-size: $font-size-base;
    }
  }

  .widget-body {
    flex: 1;
    padding: $spacing-md;
    min-height: 0;
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

    th, td {
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

// 底部
.share-footer {
  text-align: center;
  padding: $spacing-lg;
  color: $text-secondary;
  font-size: $font-size-sm;
}
</style>
