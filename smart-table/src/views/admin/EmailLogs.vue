<template>
  <div class="email-logs-page">
    <div class="page-header">
      <h1 class="page-title">邮件发送日志</h1>
      <p class="page-description">查看系统邮件发送记录和状态</p>
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
          <el-select v-model="filters.template_key" placeholder="邮件类型" clearable style="width: 150px">
            <el-option
              v-for="template in templates"
              :key="template.template_key"
              :label="template.name"
              :value="template.template_key"
            />
          </el-select>
          <el-input
            v-model="filters.recipient_email"
            placeholder="收件人邮箱"
            clearable
            style="width: 200px"
          />
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
          <el-table-column prop="recipient_email" label="收件人" min-width="180" show-overflow-tooltip />
          <el-table-column prop="template_key" label="邮件类型" min-width="120">
            <template #default="{ row }">
              {{ getTemplateName(row.template_key) }}
            </template>
          </el-table-column>
          <el-table-column prop="subject" label="主题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="retry_count" label="重试次数" width="90" align="center" />
          <el-table-column prop="sent_at" label="发送时间" min-width="150">
            <template #default="{ row }">
              {{ formatDate(row.sent_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="150">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleViewDetail(row)">详情</el-button>
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

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="邮件详情" width="700px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="收件人">{{ currentLog?.recipient_email }}</el-descriptions-item>
        <el-descriptions-item label="收件人名称">{{ currentLog?.recipient_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮件类型">{{ getTemplateName(currentLog?.template_key) }}</el-descriptions-item>
        <el-descriptions-item label="邮件主题">{{ currentLog?.subject }}</el-descriptions-item>
        <el-descriptions-item label="发送状态">
          <el-tag :type="getStatusType(currentLog?.status)">
            {{ getStatusText(currentLog?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="重试次数">{{ currentLog?.retry_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(currentLog?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="发送时间">{{ formatDate(currentLog?.sent_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="currentLog?.error_message" label="错误信息">
          <span style="color: #f56c6c">{{ currentLog.error_message }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { emailApiService } from '@/services/api/emailApiService'

interface EmailLog {
  id: string
  recipient_email: string
  recipient_name: string
  template_key: string
  subject: string
  status: 'pending' | 'sent' | 'failed' | 'retrying'
  retry_count: number
  error_message: string | null
  sent_at: string | null
  created_at: string
}

interface EmailTemplate {
  template_key: string
  name: string
}

const loading = ref(false)
const logs = ref<EmailLog[]>([])
const templates = ref<EmailTemplate[]>([])
const detailDialogVisible = ref(false)
const currentLog = ref<EmailLog | null>(null)

const filters = reactive({
  status: '',
  template_key: '',
  recipient_email: '',
  date_range: [] as string[]
})

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

const formatDate = (date: string | null) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
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

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      per_page: pagination.per_page
    }
    
    if (filters.status) params.status = filters.status
    if (filters.template_key) params.template_key = filters.template_key
    if (filters.recipient_email) params.recipient_email = filters.recipient_email
    if (filters.date_range && filters.date_range.length === 2) {
      params.start_date = filters.date_range[0]
      params.end_date = filters.date_range[1]
    }
    
    const response = await emailApiService.getLogs(params)
    // 后端返回的数据结构：{ data: [...], meta: { pagination: {...} } }
    logs.value = response.data || []
    pagination.total = response.meta?.pagination?.total || 0
  } catch (error) {
    console.error('获取邮件日志失败:', error)
    ElMessage.error('获取邮件日志失败')
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
  filters.template_key = ''
  filters.recipient_email = ''
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

const handleViewDetail = (row: EmailLog) => {
  currentLog.value = row
  detailDialogVisible.value = true
}

onMounted(() => {
  fetchTemplates()
  fetchLogs()
})
</script>

<style scoped lang="scss">
.email-logs-page {
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
}
</style>
