<template>
  <div class="notifications-page">
    <div class="page-header">
      <h1 class="page-title">{{ t('notification.pageTitle') }}</h1>
      <p class="page-description">{{ t('notification.pageDesc') }}</p>
    </div>

    <div class="page-content">
      <el-card>
        <!-- 筛选栏 -->
        <div class="filter-bar">
          <el-select
            v-model="filters.is_read"
            :placeholder="t('notification.readStatus')"
            clearable
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option :label="t('common.all')" value="" />
            <el-option :label="t('notification.unread')" value="unread" />
            <el-option :label="t('notification.read')" value="read" />
          </el-select>
          <el-select
            v-model="filters.source"
            :placeholder="t('notification.source')"
            clearable
            style="width: 160px"
            @change="handleSearch"
          >
            <el-option :label="t('notification.system')" value="system" />
            <el-option :label="t('notification.auth')" value="auth" />
            <el-option :label="t('notification.admin')" value="admin" />
            <el-option :label="t('notification.workflow')" value="workflow" />
            <el-option :label="t('notification.approval')" value="approval" />
          </el-select>
          <el-button type="primary" @click="handleSearch">{{ t('notification.query') }}</el-button>
          <el-button @click="handleReset">{{ t('common.reset') }}</el-button>
          <el-button
            type="success"
            plain
            :disabled="unreadCount === 0"
            @click="handleMarkAllAsRead"
          >
            {{ t('notification.markAllRead') }}
          </el-button>
        </div>

        <!-- 数据表格 -->
        <el-table
          v-loading="loading"
          :data="notifications"
          stripe
          style="width: 100%; margin-top: 16px"
        >
          <el-table-column prop="title" :label="t('notification.title')" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="{ 'title-unread': !row.is_read }">{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="source" :label="t('notification.source')" width="110">
            <template #default="{ row }">
              <el-tag :type="getSourceTagType(row.source)" size="small">
                {{ getSourceLabel(row.source) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" :label="t('common.status')" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_read" :label="t('notification.isRead')" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_read ? 'info' : 'danger'" size="small">
                {{ row.is_read ? t('notification.read') : t('notification.unread') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleViewDetail(row as AppNotification)">
                {{ t('notification.detail') }}
              </el-button>
              <el-button
                v-if="!row.is_read"
                link
                type="success"
                @click="handleMarkAsRead(row as AppNotification)"
              >
                {{ t('notification.markRead') }}
              </el-button>
              <el-button link type="danger" @click="handleDelete(row as AppNotification)">
                {{ t('common.delete') }}
              </el-button>
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
    <el-drawer v-model="detailVisible" :title="t('notification.detailTitle')" size="500px">
      <div v-if="currentNotification" class="detail-content">
        <h2 class="detail-title">{{ currentNotification.title }}</h2>
        <div class="detail-meta">
          <el-tag :type="getSourceTagType(currentNotification.source)" size="small">
            {{ getSourceLabel(currentNotification.source) }}
          </el-tag>
          <el-tag :type="getStatusTagType(currentNotification.status)" size="small">
            {{ getStatusText(currentNotification.status) }}
          </el-tag>
          <el-tag :type="currentNotification.is_read ? 'info' : 'danger'" size="small">
            {{ currentNotification.is_read ? t('notification.read') : t('notification.unread') }}
          </el-tag>
        </div>
        <div class="detail-time">
          <span>{{ t('notification.createTime') }}：{{ formatDateTime(currentNotification.created_at) }}</span>
          <span v-if="currentNotification.sent_at">
            {{ t('notification.sentTime') }}：{{ formatDateTime(currentNotification.sent_at) }}
          </span>
          <span v-if="currentNotification.read_at">
            {{ t('notification.readTime') }}：{{ formatDateTime(currentNotification.read_at) }}
          </span>
        </div>
        <el-divider />
        <!-- 内容为后端生成的 HTML，使用 v-html 渲染 -->
        <div class="detail-body" v-html="currentNotification.content"></div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  notificationApiService,
  type AppNotification,
  type NotificationStatus,
} from '@/services/api/notificationApiService'
import { useNotificationStore } from '@/stores/notificationStore'
import { formatDateTime } from '@/utils/timezone'

const { t } = useI18n()
const notificationStore = useNotificationStore()

const loading = ref(false)
const notifications = ref<AppNotification[]>([])
const detailVisible = ref(false)
const currentNotification = ref<AppNotification | null>(null)

// 未读数量（来自 store，用于控制"全部标记已读"按钮状态）
const unreadCount = ref(0)

const filters = reactive<{ is_read: string; source: string }>({
  is_read: '',
  source: '',
})

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0,
})

// 来源标签映射
const sourceMap: Record<string, { label: string; type: any }> = {
  system: { label: t('notification.system'), type: 'info' },
  auth: { label: t('notification.auth'), type: 'warning' },
  admin: { label: t('notification.admin'), type: 'danger' },
  workflow: { label: t('notification.workflow'), type: 'success' },
  approval: { label: t('notification.approval'), type: 'primary' },
}

const getSourceLabel = (source: string): string => {
  return sourceMap[source]?.label || source || t('notification.other')
}

const getSourceTagType = (source: string): any => {
  return sourceMap[source]?.type || 'info'
}

const getStatusTagType = (status: NotificationStatus): any => {
  const typeMap: Record<string, any> = {
    pending: 'info',
    sent: 'success',
    failed: 'danger',
    retrying: 'warning',
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status: NotificationStatus): string => {
  const textMap: Record<string, string> = {
    pending: t('notification.pending'),
    sent: t('notification.sent'),
    failed: t('notification.failed'),
    retrying: t('notification.retrying'),
  }
  return textMap[status] || status
}

// 获取通知列表
const fetchList = async () => {
  loading.value = true
  try {
    const params: {
      page: number
      per_page: number
      is_read?: boolean
      source?: string
    } = {
      page: pagination.page,
      per_page: pagination.per_page,
    }
    if (filters.is_read === 'unread') {
      params.is_read = false
    } else if (filters.is_read === 'read') {
      params.is_read = true
    }
    if (filters.source) {
      params.source = filters.source
    }
    const response = await notificationApiService.getNotifications(params)
    notifications.value = response.data || []
    pagination.total = response.meta?.pagination?.total || 0
  } catch (error) {
    console.error('[Notifications] 获取通知列表失败:', error)
    ElMessage.error(t('notification.fetchFailed'))
  } finally {
    loading.value = false
  }
}

// 刷新未读数量（同步到 store，更新顶部铃铛徽标）
const refreshUnreadCount = async () => {
  try {
    await notificationStore.fetchUnreadCount()
    unreadCount.value = notificationStore.unreadCount
  } catch (error) {
    console.error('[Notifications] 获取未读数量失败:', error)
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchList()
}

const handleReset = () => {
  filters.is_read = ''
  filters.source = ''
  pagination.page = 1
  fetchList()
}

const handleSizeChange = (size: number) => {
  pagination.per_page = size
  pagination.page = 1
  fetchList()
}

const handlePageChange = (page: number) => {
  pagination.page = page
  fetchList()
}

// 查看详情
const handleViewDetail = (row: AppNotification) => {
  currentNotification.value = row
  detailVisible.value = true
}

// 标记单条已读
const handleMarkAsRead = async (row: AppNotification) => {
  try {
    await notificationApiService.markAsRead(row.id)
    row.is_read = true
    ElMessage.success(t('notification.markReadSuccess'))
    await refreshUnreadCount()
  } catch (error) {
    console.error('[Notifications] 标记已读失败:', error)
    ElMessage.error(t('notification.markReadFailed'))
  }
}

// 全部标记已读
const handleMarkAllAsRead = async () => {
  try {
    await ElMessageBox.confirm(t('notification.markAllConfirm'), t('notification.markAllTitle'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    await notificationApiService.markAllAsRead()
    ElMessage.success(t('notification.markAllReadSuccess'))
    await fetchList()
    await refreshUnreadCount()
  } catch (error) {
    if (error === 'cancel') return
    console.error('[Notifications] 全部标记已读失败:', error)
    ElMessage.error(t('notification.markAllReadFailed'))
  }
}

// 删除通知
const handleDelete = async (row: AppNotification) => {
  try {
    await ElMessageBox.confirm(
      t('notification.deleteConfirm', { title: row.title }),
      t('notification.deleteTitle'),
      {
        confirmButtonText: t('notification.deleteConfirmBtn'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )
    await notificationApiService.deleteNotification(row.id)
    ElMessage.success(t('notification.deleteSuccess'))
    await fetchList()
    await refreshUnreadCount()
  } catch (error) {
    if (error === 'cancel') return
    console.error('[Notifications] 删除通知失败:', error)
    ElMessage.error(t('notification.deleteFailed'))
  }
}

onMounted(() => {
  fetchList()
  refreshUnreadCount()
})
</script>

<style scoped lang="scss">
.notifications-page {
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

  .title-unread {
    font-weight: 600;
  }

  .detail-content {
    padding: 0 8px;

    .detail-title {
      font-size: 18px;
      font-weight: 600;
      margin: 0 0 12px 0;
      color: #303133;
    }

    .detail-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }

    .detail-time {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 13px;
      color: #909399;
    }

    .detail-body {
      font-size: 14px;
      line-height: 1.6;
      color: #303133;
      word-break: break-word;

      :deep(p) {
        margin: 0 0 8px 0;
      }
    }
  }
}
</style>
