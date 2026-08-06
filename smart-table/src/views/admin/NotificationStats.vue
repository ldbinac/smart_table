<template>
  <div class="notification-stats-page">
    <div class="page-header">
      <h1 class="page-title">站内信统计</h1>
      <p class="page-description">查看系统站内信发送的统计数据和分析</p>
    </div>

    <div v-loading="loading" class="page-content">
      <!-- 概览卡片 -->
      <el-row :gutter="16" class="stats-overview">
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value">{{ stats.total || 0 }}</div>
              <div class="stat-label">总量</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value success">{{ stats.sent || 0 }}</div>
              <div class="stat-label">已发送</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value danger">{{ stats.failed || 0 }}</div>
              <div class="stat-label">失败</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value">{{ stats.pending || 0 }}</div>
              <div class="stat-label">待发送</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="16" class="stats-overview">
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value warning">{{ stats.retrying || 0 }}</div>
              <div class="stat-label">重试中</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value success">{{ stats.read || 0 }}</div>
              <div class="stat-label">已读数</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value">{{ stats.unread || 0 }}</div>
              <div class="stat-label">未读数</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value success">{{ successRate }}%</div>
              <div class="stat-label">成功率</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 状态分布 -->
      <el-card class="status-distribution-card">
        <template #header>
          <div class="card-header">
            <span>状态分布</span>
          </div>
        </template>
        <div class="status-list">
          <div v-for="item in statusDistribution" :key="item.key" class="status-item">
            <div class="status-item-header">
              <el-tag :type="item.type">{{ item.label }}</el-tag>
              <span class="status-item-count">{{ item.value }} ({{ item.percentage }}%)</span>
            </div>
            <el-progress
              :percentage="item.percentage"
              :color="item.color"
              :show-text="false"
              :stroke-width="10"
            />
          </div>
        </div>
      </el-card>

      <!-- 按来源分组统计 -->
      <el-card class="source-stats-card">
        <template #header>
          <div class="card-header">
            <span>按来源分组统计</span>
          </div>
        </template>
        <el-table :data="sourceStats" stripe style="width: 100%">
          <el-table-column prop="source" label="来源" min-width="120">
            <template #default="{ row }">
              <el-tag type="info">{{ getSourceText(row.source) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="count" label="数量" width="120" align="center" />
          <el-table-column label="占比" width="200" align="center">
            <template #default="{ row }">
              <el-progress :percentage="row.percentage" :show-text="true" :stroke-width="8" />
            </template>
          </el-table-column>
        </el-table>
        <div v-if="sourceStats.length === 0" class="empty-text">暂无数据</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { notificationApiService, type NotificationStats } from '@/services/api/notificationApiService'

const loading = ref(false)
const stats = ref<NotificationStats>({
  total: 0,
  sent: 0,
  failed: 0,
  pending: 0,
  retrying: 0,
  read: 0,
  unread: 0,
  by_source: {},
  by_template: {}
})

// 计算成功率
const successRate = computed(() => {
  if (!stats.value.total) return 0
  return Math.round((stats.value.sent / stats.value.total) * 100)
})

// 状态分布数据
const statusDistribution = computed(() => {
  const total = stats.value.total || 0
  const calc = (value: number) => total > 0 ? Math.round((value / total) * 100) : 0
  return [
    {
      key: 'sent',
      label: '已发送',
      value: stats.value.sent,
      percentage: calc(stats.value.sent),
      type: 'success',
      color: '#67c23a'
    },
    {
      key: 'failed',
      label: '失败',
      value: stats.value.failed,
      percentage: calc(stats.value.failed),
      type: 'danger',
      color: '#f56c6c'
    },
    {
      key: 'pending',
      label: '待发送',
      value: stats.value.pending,
      percentage: calc(stats.value.pending),
      type: 'info',
      color: '#909399'
    },
    {
      key: 'retrying',
      label: '重试中',
      value: stats.value.retrying,
      percentage: calc(stats.value.retrying),
      type: 'warning',
      color: '#e6a23c'
    }
  ]
})

// 按来源分组统计
const sourceStats = computed(() => {
  const total = stats.value.total || 0
  const bySource = stats.value.by_source || {}
  return Object.entries(bySource).map(([source, count]) => ({
    source,
    count: count as number,
    percentage: total > 0 ? Math.round(((count as number) / total) * 100) : 0
  })).sort((a, b) => b.count - a.count)
})

const getSourceText = (source: string | undefined) => {
  const textMap: Record<string, string> = {
    system: '系统',
    auth: '认证',
    admin: '管理',
    workflow: '工作流',
    approval: '审批'
  }
  return textMap[source || ''] || source || '-'
}

const fetchStats = async () => {
  loading.value = true
  try {
    const response = await notificationApiService.getStats()
    // 后端返回的数据结构：{ data: {...}, success, message }
    const statsData = (response as any).data || response
    if (statsData) {
      stats.value = {
        total: statsData.total || 0,
        sent: statsData.sent || 0,
        failed: statsData.failed || 0,
        pending: statsData.pending || 0,
        retrying: statsData.retrying || 0,
        read: statsData.read || 0,
        unread: statsData.unread || 0,
        by_source: statsData.by_source || {},
        by_template: statsData.by_template || {}
      }
    }
  } catch (error) {
    console.error('获取站内信统计失败:', error)
    ElMessage.error('获取站内信统计失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped lang="scss">
.notification-stats-page {
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
    margin-bottom: 16px;

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

        &.warning {
          color: #e6a23c;
        }
      }

      .stat-label {
        font-size: 14px;
        color: #666;
      }
    }
  }

  .card-header {
    font-weight: 600;
  }

  .status-distribution-card {
    margin-bottom: 24px;

    .status-list {
      display: flex;
      flex-direction: column;
      gap: 20px;

      .status-item {
        .status-item-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;

          .status-item-count {
            font-size: 14px;
            color: #666;
          }
        }
      }
    }
  }

  .source-stats-card {
    margin-top: 24px;

    .empty-text {
      text-align: center;
      color: #999;
      padding: 24px 0;
    }
  }
}
</style>
