<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useBaseStore } from '@/stores'
import { recordService } from '@/db/services/recordService'
import { fieldService } from '@/db/services/fieldService'
import { tableService } from '@/db/services/tableService'
import type { RecordEntity, FieldEntity, TableEntity } from '@/db/schema'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

interface Widget {
  id: string
  type: 'bar' | 'line' | 'pie' | 'number' | 'table'
  title: string
  tableId: string
  fieldId: string
  aggregation: 'count' | 'sum' | 'avg' | 'max' | 'min'
  groupBy?: string
  position: { x: number; y: number; w: number; h: number }
}

const baseStore = useBaseStore()

const tables = ref<TableEntity[]>([])
const fields = ref<FieldEntity[]>([])
const records = ref<RecordEntity[]>([])
const widgets = ref<Widget[]>([])
const selectedWidget = ref<Widget | null>(null)
const chartRefs = ref<Map<string, echarts.ECharts>>(new Map())
const chartContainers = ref<Map<string, HTMLElement>>(new Map())

const widgetTypes = [
  { value: 'bar', label: '柱状图', icon: 'BarChart' },
  { value: 'line', label: '折线图', icon: 'TrendCharts' },
  { value: 'pie', label: '饼图', icon: 'PieChart' },
  { value: 'number', label: '数字卡片', icon: 'DataAnalysis' },
  { value: 'table', label: '表格', icon: 'Grid' }
]

const aggregationTypes = [
  { value: 'count', label: '计数' },
  { value: 'sum', label: '求和' },
  { value: 'avg', label: '平均值' },
  { value: 'max', label: '最大值' },
  { value: 'min', label: '最小值' }
]

async function loadTables() {
  if (!baseStore.currentBase) return
  tables.value = await tableService.getTablesByBase(baseStore.currentBase.id)
}

async function loadFields(tableId: string) {
  fields.value = await fieldService.getFieldsByTable(tableId)
}

async function loadRecords(tableId: string) {
  records.value = await recordService.getRecordsByTable(tableId)
}

function handleTableChange(tableId: string) {
  loadFields(tableId)
  loadRecords(tableId)
}

function addWidget(type: Widget['type']) {
  const newWidget: Widget = {
    id: `widget-${Date.now()}`,
    type,
    title: '新图表',
    tableId: tables.value[0]?.id || '',
    fieldId: '',
    aggregation: 'count',
    position: { x: 0, y: 0, w: 6, h: 4 }
  }
  widgets.value.push(newWidget)
  selectedWidget.value = newWidget
  
  if (newWidget.tableId) {
    handleTableChange(newWidget.tableId)
  }
}

function removeWidget(widgetId: string) {
  const chart = chartRefs.value.get(widgetId)
  if (chart) {
    chart.dispose()
    chartRefs.value.delete(widgetId)
  }
  widgets.value = widgets.value.filter(w => w.id !== widgetId)
}

function getChartData(widget: Widget) {
  if (!records.value.length || !widget.fieldId) {
    return { labels: [], values: [] }
  }
  
  const field = fields.value.find(f => f.id === widget.fieldId)
  if (!field) return { labels: [], values: [] }
  
  const grouped: Record<string, number[]> = {}
  
  records.value.forEach(record => {
    const value = record.values[widget.fieldId]
    const key = String(value ?? '未设置')
    
    if (!grouped[key]) {
      grouped[key] = []
    }
    
    if (widget.aggregation !== 'count') {
      const numValue = Number(record.values[widget.fieldId])
      if (!isNaN(numValue)) {
        grouped[key].push(numValue)
      }
    } else {
      grouped[key].push(1)
    }
  })
  
  const labels = Object.keys(grouped)
  const values = labels.map(label => {
    const nums = grouped[label]
    switch (widget.aggregation) {
      case 'sum':
        return nums.reduce((a, b) => a + b, 0)
      case 'avg':
        return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : 0
      case 'max':
        return Math.max(...nums)
      case 'min':
        return Math.min(...nums)
      default:
        return nums.length
    }
  })
  
  return { labels, values }
}

function getChartOption(widget: Widget): EChartsOption {
  const { labels, values } = getChartData(widget)
  
  const baseOption: EChartsOption = {
    tooltip: {
      trigger: widget.type === 'pie' ? 'item' : 'axis'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    }
  }
  
  switch (widget.type) {
    case 'bar':
      return {
        ...baseOption,
        xAxis: {
          type: 'category',
          data: labels
        },
        yAxis: {
          type: 'value'
        },
        series: [{
          type: 'bar',
          data: values,
          itemStyle: {
            color: '#3370FF'
          }
        }]
      }
    
    case 'line':
      return {
        ...baseOption,
        xAxis: {
          type: 'category',
          data: labels
        },
        yAxis: {
          type: 'value'
        },
        series: [{
          type: 'line',
          data: values,
          smooth: true,
          itemStyle: {
            color: '#3370FF'
          }
        }]
      }
    
    case 'pie':
      return {
        ...baseOption,
        series: [{
          type: 'pie',
          radius: '60%',
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
    
    default:
      return baseOption
  }
}

function renderChart(widget: Widget) {
  let container = chartContainers.value.get(widget.id)
  if (!container) return
  
  let chart = chartRefs.value.get(widget.id)
  if (!chart) {
    chart = echarts.init(container)
    chartRefs.value.set(widget.id, chart)
  }
  
  if (widget.type === 'number') {
    const { values } = getChartData(widget)
    const total = values.reduce((a, b) => a + b, 0)
    container.innerHTML = `
      <div class="number-card">
        <div class="number-value">${total.toLocaleString()}</div>
        <div class="number-label">${widget.title}</div>
      </div>
    `
    return
  }
  
  if (widget.type === 'table') {
    const { labels, values } = getChartData(widget)
    container.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>分类</th>
            <th>值</th>
          </tr>
        </thead>
        <tbody>
          ${labels.map((label, i) => `
            <tr>
              <td>${label}</td>
              <td>${values[i]}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `
    return
  }
  
  chart.setOption(getChartOption(widget))
}

function handleResize() {
  chartRefs.value.forEach(chart => {
    chart.resize()
  })
}

watch(widgets, () => {
  widgets.value.forEach(widget => {
    setTimeout(() => renderChart(widget), 0)
  })
}, { deep: true })

watch(selectedWidget, (widget) => {
  if (widget) {
    handleTableChange(widget.tableId)
  }
})

onMounted(() => {
  loadTables()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartRefs.value.forEach(chart => chart.dispose())
})
</script>

<template>
  <div class="dashboard-view">
    <div class="dashboard-toolbar">
      <el-dropdown @command="addWidget">
        <el-button type="primary">
          <el-icon><Plus /></el-icon>
          添加组件
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="type in widgetTypes"
              :key="type.value"
              :command="type.value"
            >
              <el-icon><component :is="type.icon" /></el-icon>
              {{ type.label }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    
    <div class="dashboard-content">
      <div class="widgets-container">
        <div
          v-for="widget in widgets"
          :key="widget.id"
          class="widget-card"
          :class="{ selected: selectedWidget?.id === widget.id }"
          @click="selectedWidget = widget"
        >
          <div class="widget-header">
            <span class="widget-title">{{ widget.title }}</span>
            <el-button
              link
              type="danger"
              size="small"
              @click.stop="removeWidget(widget.id)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div
            :ref="el => el && chartContainers.set(widget.id, el as HTMLElement)"
            class="widget-body"
          ></div>
        </div>
        
        <div v-if="widgets.length === 0" class="empty-dashboard">
          <el-icon class="empty-icon"><DataAnalysis /></el-icon>
          <p>点击上方按钮添加图表组件</p>
        </div>
      </div>
      
      <div v-if="selectedWidget" class="config-panel">
        <div class="panel-header">
          <h3>组件配置</h3>
        </div>
        
        <el-form label-position="top" size="small">
          <el-form-item label="标题">
            <el-input v-model="selectedWidget.title" />
          </el-form-item>
          
          <el-form-item label="数据表">
            <el-select
              :model-value="selectedWidget?.tableId"
              @update:model-value="val => { if(selectedWidget) { selectedWidget.tableId = val; handleTableChange(val); } }"
            >
              <el-option
                v-for="table in tables"
                :key="table.id"
                :label="table.name"
                :value="table.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="字段">
            <el-select v-model="selectedWidget.fieldId">
              <el-option
                v-for="field in fields"
                :key="field.id"
                :label="field.name"
                :value="field.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="聚合方式">
            <el-select v-model="selectedWidget.aggregation">
              <el-option
                v-for="agg in aggregationTypes"
                :key="agg.value"
                :label="agg.label"
                :value="agg.value"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.dashboard-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-color;
}

.dashboard-toolbar {
  padding: $spacing-md;
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
}

.dashboard-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.widgets-container {
  flex: 1;
  padding: $spacing-md;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: $spacing-md;
  overflow-y: auto;
}

.widget-card {
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  border: 1px solid $border-color;
  overflow: hidden;
  
  &.selected {
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.2);
  }
}

.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid $border-color;
}

.widget-title {
  font-weight: 500;
  color: $text-primary;
}

.widget-body {
  height: 250px;
  padding: $spacing-md;
}

.config-panel {
  width: 280px;
  background-color: $surface-color;
  border-left: 1px solid $border-color;
  padding: $spacing-md;
  overflow-y: auto;
}

.panel-header {
  margin-bottom: $spacing-md;
  
  h3 {
    font-size: $font-size-base;
    font-weight: 500;
    color: $text-primary;
  }
}

.empty-dashboard {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-xl * 2;
  color: $text-secondary;
  
  .empty-icon {
    font-size: 48px;
    margin-bottom: $spacing-md;
    color: $text-disabled;
  }
}

.number-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  
  .number-value {
    font-size: 36px;
    font-weight: 600;
    color: $primary-color;
  }
  
  .number-label {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin-top: $spacing-sm;
  }
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  
  th, td {
    padding: $spacing-xs $spacing-sm;
    text-align: left;
    border-bottom: 1px solid $border-color;
  }
  
  th {
    font-weight: 500;
    color: $text-secondary;
    background-color: $bg-color;
  }
  
  td {
    color: $text-primary;
  }
}
</style>
