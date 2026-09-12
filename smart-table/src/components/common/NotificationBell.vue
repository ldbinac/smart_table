<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Bell } from '@element-plus/icons-vue'
import { useNotificationStore } from '@/stores/notificationStore'
import { useAuthStore } from '@/stores/authStore'
import { formatDateTime, formatRelativeTime } from '@/utils/timezone'
import { notificationApiService, type AppNotification } from '@/services/api/notificationApiService'

defineOptions({ name: 'NotificationBell' })

const router = useRouter()
const { t } = useI18n()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

// 未读数量
const unreadCount = computed(() => notificationStore.unreadCount)
// 最近通知列表
const recentNotifications = computed(() => notificationStore.recentNotifications)

// 来源标签映射
const sourceTagMap: Record<string, { labelKey: string; type: any }> = {
  system: { labelKey: 'common.sourceSystem', type: 'info' },
  auth: { labelKey: 'common.sourceAuth', type: 'warning' },
  admin: { labelKey: 'common.sourceAdmin', type: 'danger' },
  workflow: { labelKey: 'common.sourceWorkflow', type: 'success' },
  approval: { labelKey: 'common.sourceApproval', type: 'primary' },
}

const getSourceTag = (source: string) => {
  const item = sourceTagMap[source]
  if (item) return { label: t(item.labelKey), type: item.type }
  return { label: source || t('common.sourceOther'), type: 'info' }
}

// 内容摘要：优先使用纯文本，否则去除 HTML 标签
const getContentSummary = (notification: AppNotification): string => {
  if (notification.content_text) {
    return notification.content_text
  }
  if (notification.content) {
    return notification.content.replace(/<[^>]+>/g, '').trim()
  }
  return ''
}

// 下拉面板显隐（打开详情时需收起，避免遮挡弹窗）
const popoverVisible = ref(false)
// 消息详情弹窗
const detailVisible = ref(false)
const currentNotification = ref<AppNotification | null>(null)

// 状态标签映射
const statusTagMap: Record<string, { labelKey: string; type: any }> = {
  pending: { labelKey: 'notification.pending', type: 'info' },
  sent: { labelKey: 'notification.sent', type: 'success' },
  failed: { labelKey: 'notification.failed', type: 'danger' },
  retrying: { labelKey: 'notification.retrying', type: 'warning' },
}

const getStatusTag = (status: string) => {
  const item = statusTagMap[status]
  if (item) return { label: t(item.labelKey), type: item.type }
  return { label: status || t('common.sourceOther'), type: 'info' }
}

// 跳转到通知列表页
const goToList = () => {
  popoverVisible.value = false
  detailVisible.value = false
  router.push('/notifications')
}

// 点击单条通知：收起下拉面板并直接打开详情弹窗，未读的同时标记已读
const handleClickNotification = async (notification: AppNotification) => {
  currentNotification.value = notification
  detailVisible.value = true
  popoverVisible.value = false

  if (notification.is_read) return

  try {
    await notificationStore.markAsRead(notification.id)
    // 重新拉取详情，补齐服务端的 read_at 等字段
    const res = await notificationApiService.getNotification(notification.id)
    if (res?.data) {
      currentNotification.value = res.data
    }
  } catch (error) {
    console.error('[NotificationBell] markAsRead failed:', error)
  }
}

// 全部已读
const handleMarkAllAsRead = async () => {
  if (unreadCount.value === 0) return
  try {
    await notificationStore.markAllAsRead()
    ElMessage.success(t('notification.markAllReadSuccess'))
  } catch (error) {
    console.error('[NotificationBell] markAllAsRead failed:', error)
    ElMessage.error(t('notification.markAllReadFailed'))
  }
}

/** 定时轮询未读数的间隔（毫秒） */
const UNREAD_POLL_INTERVAL = 60_000

let pollTimer: ReturnType<typeof setInterval> | null = null

/**
 * 刷新入口统一做登录态判断，
 * 避免未登录时调用需认证的接口导致跳转登录页。
 */
function safeRefresh() {
  if (!authStore.isAuthenticated) return
  notificationStore.refresh()
}

/** 页面重新可见时立即刷新，避免后台标签页长时间挂起后看到陈旧数据 */
function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    safeRefresh()
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (!authStore.isAuthenticated) return
    notificationStore.fetchUnreadCount()
  }, UNREAD_POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  safeRefresh()
  startPolling()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopPolling()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

// 登录态兜底：已登录时立即刷新，登出时清空本地状态，避免残留上一位用户的数据
watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      safeRefresh()
    } else {
      notificationStore.reset()
    }
  },
)
</script>

<template>
  <el-popover
    v-model:visible="popoverVisible"
    placement="bottom-end"
    :width="380"
    trigger="click"
    popper-class="notification-bell-popover"
    @show="safeRefresh"
  >
    <template #reference>
      <el-badge
        :value="unreadCount"
        :hidden="unreadCount === 0"
        :max="99"
        class="notification-badge"
      >
        <el-button type="primary" plain circle :title="t('notification.pageTitle')">
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>
    </template>

    <div class="notification-panel">
      <!-- 头部：标题 + 全部已读 -->
      <div class="panel-header">
        <span class="panel-title">{{ t('notification.pageTitle') }}</span>
        <el-button
          link
          type="primary"
          :disabled="unreadCount === 0"
          @click="handleMarkAllAsRead"
        >
          {{ t('notification.markAllRead') }}
        </el-button>
      </div>

      <!-- 列表区 -->
      <div class="panel-list">
        <div v-if="recentNotifications.length === 0" class="empty-state">
          {{ t('notification.noNotification') }}
        </div>
        <div
          v-for="item in recentNotifications"
          :key="item.id"
          class="notification-item"
          :class="{ 'is-unread': !item.is_read }"
          @click="handleClickNotification(item)"
        >
          <div class="item-header">
            <div class="item-title">
              <span v-if="!item.is_read" class="unread-dot"></span>
              <span class="title-text">{{ item.title }}</span>
            </div>
            <el-tag size="small" :type="getSourceTag(item.source).type">
              {{ getSourceTag(item.source).label }}
            </el-tag>
          </div>
          <div v-if="getContentSummary(item)" class="item-content">
            {{ getContentSummary(item) }}
          </div>
          <div class="item-time">
            {{ formatRelativeTime(item.created_at) }}
          </div>
        </div>
      </div>

      <!-- 底部：查看全部通知 -->
      <div class="panel-footer">
        <el-button link type="primary" @click="goToList">
          {{ t('notification.viewAll') }}
        </el-button>
      </div>
    </div>
  </el-popover>

  <!-- 消息详情弹窗：点击下拉列表中的消息后直接展开查看。
       必须 append-to-body 传送到 body，否则会被 AppHeader 的层叠上下文
       （position: relative; z-index: 100）限制在导航栏区域内，导致内容不可见。 -->
  <el-dialog
    v-model="detailVisible"
    :title="t('notification.detailTitle')"
    width="560px"
    append-to-body
    class="notification-detail-dialog"
  >
    <div v-if="currentNotification" class="detail-content">
      <h2 class="detail-title">{{ currentNotification.title }}</h2>
      <div class="detail-meta">
        <el-tag size="small" :type="getSourceTag(currentNotification.source).type">
          {{ getSourceTag(currentNotification.source).label }}
        </el-tag>
        <el-tag size="small" :type="getStatusTag(currentNotification.status).type">
          {{ getStatusTag(currentNotification.status).label }}
        </el-tag>
        <el-tag size="small" :type="currentNotification.is_read ? 'info' : 'danger'">
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
  </el-dialog>
</template>

<style lang="scss" scoped>
.notification-badge {
  display: inline-flex;
}

:deep(.el-button.is-circle) {
  width: 32px;
  height: 32px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px;
  border-bottom: 1px solid var(--el-border-color-lighter);

  .panel-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }
}

.panel-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 4px 0;
}

.empty-state {
  padding: 32px 0;
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.notification-item {
  padding: 10px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--el-fill-color-light);
  }

  &.is-unread {
    background-color: var(--el-color-primary-light-9);
  }

  .item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 4px;
  }

  .item-title {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    flex: 1;

    .unread-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: var(--el-color-primary);
      flex-shrink: 0;
    }

    .title-text {
      font-size: 13px;
      color: var(--el-text-color-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  &.is-unread .title-text {
    font-weight: 600;
  }

  .item-content {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.5;
    margin-bottom: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .item-time {
    font-size: 12px;
    color: var(--el-text-color-placeholder);
  }
}

.panel-footer {
  text-align: center;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 8px;
  margin-top: 4px;
}

// 弹窗经 append-to-body 传送到 body，此处限制最大宽度以适配窄屏
.notification-detail-dialog {
  max-width: 90vw;
}

.detail-content {
  .detail-title {
    font-size: 18px;
    font-weight: 600;
    margin: 0 0 12px 0;
    color: var(--el-text-color-primary);
    word-break: break-word;
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
    color: var(--el-text-color-secondary);
  }

  .detail-body {
    font-size: 14px;
    line-height: 1.6;
    color: var(--el-text-color-primary);
    word-break: break-word;

    :deep(p) {
      margin: 0 0 8px 0;
    }
  }
}
</style>
