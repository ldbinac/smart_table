<template>
  <div class="email-stats-page">
    <div class="page-header">
      <h1 class="page-title">邮件发送统计</h1>
      <p class="page-description">查看系统邮件发送的统计数据和分析</p>
    </div>

    <div v-loading="loading" class="page-content">
      <!-- 概览卡片 -->
      <el-row :gutter="16" class="stats-overview">
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value">{{ stats.total_emails || 0 }}</div>
              <div class="stat-label">总发送量</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value success">{{ stats.sent_count || 0 }}</div>
              <div class="stat-label">发送成功</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value danger">{{ stats.failed_count || 0 }}</div>
              <div class="stat-label">发送失败</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value">{{ stats.success_rate || 0 }}%</div>
              <div class="stat-label">成功率</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 图表区域 -->
      <el-row :gutter="16" class="charts-row">
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>邮件类型分布</span>
              </div>
            </template>
            <div ref="typeChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>发送状态分布</span>
              </div>
            </template>
            <div ref="statusChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 模板统计表格 -->
      <el-card class="template-stats-card">
        <template #header>
          <div class="card-header">
            <span>各模板发送统计</span>
          </div>
        </template>
        <el-table :data="stats.template_stats || []" stripe style="width: 100%">
          <el-table-column prop="template_key" label="模板标识" min-width="150">
            <template #default="{ row }">
              {{ getTemplateName(row.template_key) }}
            </template>
          </el-table-column>
          <el-table-column prop="total" label="总发送量" width="120" align="center" />
          <el-table-column prop="sent" label="成功" width="100" align="center">
            <template #default="{ row }">
              <span style="color: #67c23a">{{ row.sent }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="failed" label="失败" width="100" align="center">
            <template #default="{ row }">
              <span style="color: #f56c6c">{{ row.failed }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="success_rate" label="成功率" width="120" align="center">
            <template #default="{ row }">
              {{ row.success_rate }}%
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { emailApiService } from '@/services/api/emailApiService'

interface TemplateStat {
  template_key: string
  total: number
  sent: number
  failed: number
  success_rate: number
}

interface EmailStats {
  total_emails: number
  sent_count: number
  failed_count: number
  pending_count: number
  retrying_count: number
  success_rate: number
  template_stats: TemplateStat[]
}

interface EmailTemplate {
  template_key: string
  name: string
}

const loading = ref(false)
const stats = ref<EmailStats>({
  total_emails: 0,
  sent_count: 0,
  failed_count: 0,
  pending_count: 0,
  retrying_count: 0,
  success_rate: 0,
  template_stats: []
})
const templates = ref<EmailTemplate[]>([])

const typeChartRef = ref<HTMLElement>()
const statusChartRef = ref<HTMLElement>()
let typeChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null

const getTemplateName = (templateKey: string | undefined) => {
  if (!templateKey) return '-'
  const template = templates.value.find(t => t.template_key === templateKey)
  return template?.name || templateKey
}

const fetchTemplates = async () => {
  try {
    const response = await emailApiService.getTemplates()
    templates.value = response.data || []
  } catch (error) {
    console.error('获取模板列表失败:', error)
  }
}

const fetchStats = async () => {
  loading.value = true
  try {
    const data = await emailApiService.getStats()

    if (data) {
      // 转换后端数据结构到前端数据结构
      stats.value = {
        total_emails: data.total || 0,
        sent_count: data.sent || 0,
        failed_count: data.failed || 0,
        pending_count: data.pending || 0,
        retrying_count: data.retrying || 0,
        success_rate: data.success_rate || 0,
        // 将 by_template 对象转换为数组
        template_stats: data.by_template ? Object.entries(data.by_template).map(([key, value]: [string, any]) => ({
          template_key: key,
          total: value.total || 0,
          sent: value.sent || 0,
          failed: value.failed || 0,
          success_rate: value.total > 0 ? Math.round((value.sent / value.total) * 100) : 0
        })) : []
      }
    }

    await nextTick()
    initCharts()
  } catch (error) {
    console.error('获取邮件统计失败:', error)
    ElMessage.error('获取邮件统计失败')
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  // 邮件类型分布图
  if (typeChartRef.value) {
    if (typeChart) {
      typeChart.dispose()
    }
    typeChart = echarts.init(typeChartRef.value)
    
    const typeData = stats.value.template_stats?.map(stat => ({
      name: getTemplateName(stat.template_key),
      value: stat.total
    })) || []
    
    typeChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'center'
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 18,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: typeData
      }]
    })
  }
  
  // 发送状态分布图
  if (statusChartRef.value) {
    if (statusChart) {
      statusChart.dispose()
    }
    statusChart = echarts.init(statusChartRef.value)
    
    statusChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'center'
      },
      series: [{
        type: 'pie',
        radius: '70%',
        data: [
          { value: stats.value.sent_count, name: '已发送', itemStyle: { color: '#67c23a' } },
          { value: stats.value.failed_count, name: '发送失败', itemStyle: { color: '#f56c6c' } },
          { value: stats.value.pending_count, name: '待发送', itemStyle: { color: '#909399' } },
          { value: stats.value.retrying_count, name: '重试中', itemStyle: { color: '#e6a23c' } }
        ].filter(item => item.value > 0),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    })
  }
}

// 监听窗口大小变化
const handleResize = () => {
  typeChart?.resize()
  statusChart?.resize()
}

onMounted(() => {
  fetchTemplates()
  fetchStats()
  window.addEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.email-stats-page {
  padding: 24px;
  height: calc(100vh - 48px);
  overflow-y: auto;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0 0 8px 0;
    }

    .page-description {
      color: #666;
      margin: 0;
    }
  }

  .stats-overview {
    margin-bottom: 24px;

    .stat-item {
      text-align: center;
      padding: 20px 0;

      .stat-value {
        font-size: 32px;
        font-weight: 600;
        color: #409eff;
        margin-bottom: 8px;

        &.success {
          color: #67c23a;
        }

        &.danger {
          color: #f56c6c;
        }
      }

      .stat-label {
        font-size: 14px;
        color: #666;
      }
    }
  }

  .charts-row {
    margin-bottom: 24px;

    .chart-container {
      height: 300px;
    }
  }

  .card-header {
    font-weight: 600;
  }

  .template-stats-card {
    margin-top: 24px;
  }
}
</style>
