<template>
  <div class="email-logs-page">
    <div class="page-header">
      <h1 class="page-title">{{ t('admin.emailLogs.title') }}</h1>
      <p class="page-description">{{ t('admin.emailLogs.desc') }}</p>
    </div>

    <div class="page-content">
      <el-card>
        <!-- 筛选栏 -->
        <div class="filter-bar">
          <el-select v-model="filters.status" :placeholder="t('admin.emailLogs.filterStatus')" clearable style="width: 120px">
            <el-option :label="t('admin.statusPending')" value="pending" />
            <el-option :label="t('admin.statusSent')" value="sent" />
            <el-option :label="t('admin.statusFailed')" value="failed" />
            <el-option :label="t('admin.statusRetrying')" value="retrying" />
          </el-select>
          <el-select v-model="filters.template_key" :placeholder="t('admin.emailLogs.filterTemplate')" clearable style="width: 150px">
            <el-option
              v-for="template in templates"
              :key="template.template_key"
              :label="template.name"
              :value="template.template_key"
            />
          </el-select>
          <el-input
            v-model="filters.recipient_email"
            :placeholder="t('admin.emailLogs.filterRecipient')"
            clearable
            style="width: 200px"
          />
          <el-date-picker
            v-model="filters.date_range"
            type="daterange"
            :range-separator="t('admin.dateRangeSeparator')"
            :start-placeholder="t('admin.startDate')"
            :end-placeholder="t('admin.endDate')"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
          <el-button type="primary" @click="handleSearch">{{ t('admin.search') }}</el-button>
          <el-button @click="handleReset">{{ t('admin.reset') }}</el-button>
        </div>

        <!-- 数据表格 -->
        <el-table v-loading="loading" :data="logs" stripe style="width: 100%; margin-top: 16px">
          <el-table-column prop="recipient_email" :label="t('admin.emailLogs.colRecipient')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="template_key" :label="t('admin.emailLogs.colTemplate')" min-width="120">
            <template #default="{ row }">
              {{ getTemplateName(row.template_key) }}
            </template>
          </el-table-column>
          <el-table-column prop="subject" :label="t('admin.emailLogs.colSubject')" min-width="200" show-overflow-tooltip />
          <el-table-column prop="status" :label="t('admin.emailLogs.colStatus')" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="retry_count" :label="t('admin.emailLogs.colRetryCount')" width="90" align="center" />
          <el-table-column prop="sent_at" :label="t('admin.emailLogs.colCreatedAt')" min-width="150">
            <template #default="{ row }">
              {{ formatDate(row.sent_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="t('admin.emailLogs.colCreatedAt')" min-width="150">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('admin.emailLogs.colActions')" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleViewDetail(row as EmailLog)">{{ t('admin.detail') }}</el-button>
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
    <el-dialog v-model="detailDialogVisible" :title="t('admin.emailLogs.detailTitle')" width="700px">
      <el-descriptions :column="1" border>
        <el-descriptions-item :label="t('admin.emailLogs.labelRecipient')">{{ currentLog?.recipient_email }}</el-descriptions-item>
        <el-descriptions-item :label="t('admin.emailLogs.labelRecipientName')">{{ currentLog?.recipient_name || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t('admin.emailLogs.labelTemplateType')">{{ getTemplateName(currentLog?.template_key) }}</el-descriptions-item>
        <el-descriptions-item :label="t('admin.emailLogs.labelSubject')">{{ currentLog?.subject }}</el-descriptions-item>
        <el-descriptions-item :label="t('admin.emailLogs.labelStatus')">
          <el-tag :type="getStatusType(currentLog?.status)">
            {{ getStatusText(currentLog?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="t('admin.emailLogs.labelRetryCount')">{{ currentLog?.retry_count || 0 }}</el-descriptions-item>
        <el-descriptions-item :label="t('admin.emailLogs.labelSentAt')">{{ formatDate(currentLog?.created_at || null) }}</el-descriptions-item>
        <el-descriptions-item :label="t('admin.emailLogs.labelSentAt')">{{ formatDate(currentLog?.sent_at || null) || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="currentLog?.error_message" :label="t('admin.emailLogs.errorInfo')">
          <span style="color: #f56c6c">{{ currentLog.error_message }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { emailApiService } from '@/services/api/emailApiService'

const { t } = useI18n()

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

import { formatDateTime } from "@/utils/timezone";

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
    pending: t('admin.statusPending'),
    sent: t('admin.statusSent'),
    failed: t('admin.statusFailed'),
    retrying: t('admin.statusRetrying')
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
    ElMessage.error(t('admin.emailLogs.fetchFailed'))
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
