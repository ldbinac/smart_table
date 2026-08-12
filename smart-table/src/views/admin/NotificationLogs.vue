<template>
  <div class="notification-logs-page">
    <div class="page-header">
      <h1 class="page-title">站内信日志</h1>
      <p class="page-description">查看系统站内信发送记录和状态</p>
    </div>

    <div class="page-content">
      <el-card>
        <!-- 筛选栏 -->
        <div class="filter-bar">
          <el-select v-model="filters.status" placeholder="发送状态" clearable style="width: 120px">
            <el-option label="待发送" value="pending" />
            <el-option label="已发送" value="sent" />
            <el-option label="发送失败" value="failed" />
            <el-option label="重试中" value="retrying" />
          </el-select>
          <el-select v-model="filters.source" placeholder="来源" clearable style="width: 140px">
            <el-option label="系统" value="system" />
            <el-option label="认证" value="auth" />
            <el-option label="管理" value="admin" />
            <el-option label="工作流" value="workflow" />
            <el-option label="审批" value="approval" />
          </el-select>
          <el-input
            v-model="filters.recipient_user_id"
            placeholder="收件人用户ID"
            clearable
            style="width: 200px"
          />
          <el-select v-model="filters.is_read" placeholder="已读" clearable style="width: 120px">
            <el-option label="已读" value="read" />
            <el-option label="未读" value="unread" />
          </el-select>
          <el-date-picker
            v-model="filters.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>

        <!-- 数据表格 -->
        <el-table v-loading="loading" :data="logs" stripe style="width: 100%; margin-top: 16px">
          <el-table-column prop="recipient_user_id" label="收件人用户ID" min-width="150" show-overflow-tooltip />
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="source" label="来源" width="100">
            <template #default="{ row }">
              <el-tag type="info">{{ getSourceText(row.source) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_read" label="已读" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_read ? 'success' : 'info'">
                {{ row.is_read ? '已读' : '未读' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="retry_count" label="重试次数" width="90" align="center" />
          <el-table-column prop="created_at" label="创建时间" min-width="150">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'failed'"
                link
                type="warning"
                @click="handleRetry(row as AppNotification)"
              >重试</el-button>
              <el-button link type="primary" @click="handleViewDetail(row as AppNotification)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.per_page"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailDrawerVisible" title="站内信详情" size="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="收件人用户ID">{{ currentLog?.recipient_user_id }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ currentLog?.title }}</el-descriptions-item>
        <el-descriptions-item label="来源">
          <el-tag type="info">{{ getSourceText(currentLog?.source) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="发送状态">
          <el-tag :type="getStatusType(currentLog?.status)">
            {{ getStatusText(currentLog?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="是否已读">
          <el-tag :type="currentLog?.is_read ? 'success' : 'info'">
            {{ currentLog?.is_read ? '已读' : '未读' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="重试次数">{{ currentLog?.retry_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(currentLog?.created_at || null) }}</el-descriptions-item>
        <el-descriptions-item label="发送时间">{{ formatDate(currentLog?.sent_at || null) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="阅读时间">{{ formatDate(currentLog?.read_at || null) || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="detail-content">
        <div class="detail-content-label">内容</div>
        <div class="detail-content-body" v-html="currentLog?.content || ''"></div>
      </div>
      <div v-if="currentLog?.error_message" class="detail-error">
        <div class="detail-content-label">错误信息</div>
        <div class="detail-content-body" style="color: #f56c6c">{{ currentLog.error_message }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { notificationApiService, type AppNotification } from '@/services/api/notificationApiService'
import { formatDateTime } from "@/utils/timezone";

const loading = ref(false)
const logs = ref<AppNotification[]>([])
const detailDrawerVisible = ref(false)
const currentLog = ref<AppNotification | null>(null)

const filters = reactive({
  status: '',
  source: '',
  recipient_user_id: '',
  is_read: '',
  date_range: [] as string[]
})

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

const formatDate = (date: string | null) => {
  if (!date) return '-'
  return formatDateTime(date, "YYYY-MM-DD HH:mm:ss")
}

const getStatusType = (status: string | undefined) => {
  const typeMap: Record<string, any> = {
    pending: 'info',
    sent: 'success',
    failed: 'danger',
    retrying: 'warning'
  }
  return typeMap[status || ''] || 'info'
}

const getStatusText = (status: string | undefined) => {
  const textMap: Record<string, string> = {
    pending: '待发送',
    sent: '已发送',
    failed: '失败',
    retrying: '重试中'
  }
  return textMap[status || ''] || status
}

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

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      per_page: pagination.per_page
    }

    if (filters.status) params.status = filters.status
    if (filters.source) params.source = filters.source
    if (filters.recipient_user_id) params.recipient_user_id = filters.recipient_user_id
    if (filters.is_read === 'read') params.is_read = true
    if (filters.is_read === 'unread') params.is_read = false
    if (filters.date_range && filters.date_range.length === 2) {
      params.start_date = filters.date_range[0]
      params.end_date = filters.date_range[1]
    }

    const response = await notificationApiService.getLogs(params)
    // 后端返回的数据结构：{ data: [...], meta: { pagination: {...} } }
    logs.value = response.data || []
    pagination.total = response.meta?.pagination?.total || 0
  } catch (error) {
    console.error('获取站内信日志失败:', error)
    ElMessage.error('获取站内信日志失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchLogs()
}

const handleReset = () => {
  filters.status = ''
  filters.source = ''
  filters.recipient_user_id = ''
  filters.is_read = ''
  filters.date_range = []
  pagination.page = 1
  fetchLogs()
}

const handleSizeChange = (size: number) => {
  pagination.per_page = size
  pagination.page = 1
  fetchLogs()
}

const handlePageChange = (page: number) => {
  pagination.page = page
  fetchLogs()
}

const handleViewDetail = (row: AppNotification) => {
  currentLog.value = row
  detailDrawerVisible.value = true
}

const handleRetry = async (row: AppNotification) => {
  try {
    await notificationApiService.retryNotification(row.id)
    ElMessage.success('重试请求已提交')
    fetchLogs()
  } catch (error) {
    console.error('重试站内信失败:', error)
    ElMessage.error('重试站内信失败')
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped lang="scss">
.notification-logs-page {
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

  .filter-bar {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
  }

  .pagination-container {
    margin-top: 24px;
    display: flex;
    justify-content: flex-end;
  }

  .detail-content {
    margin-top: 16px;

    .detail-content-label {
      font-weight: 600;
      margin-bottom: 8px;
      color: #333;
    }

    .detail-content-body {
      color: #666;
      line-height: 1.6;
      word-break: break-word;
    }
  }

  .detail-error {
    margin-top: 16px;
  }
}
</style>
