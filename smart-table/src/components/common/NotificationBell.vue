<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell } from '@element-plus/icons-vue'
import { useNotificationStore } from '@/stores/notificationStore'
import { formatRelativeTime } from '@/utils/timezone'
import type { AppNotification } from '@/services/api/notificationApiService'

defineOptions({ name: 'NotificationBell' })

const router = useRouter()
const notificationStore = useNotificationStore()

// 未读数量
const unreadCount = computed(() => notificationStore.unreadCount)
// 最近通知列表
const recentNotifications = computed(() => notificationStore.recentNotifications)

// 来源标签映射
const sourceTagMap: Record<string, { label: string; type: any }> = {
  system: { label: '系统', type: 'info' },
  auth: { label: '认证', type: 'warning' },
  admin: { label: '管理', type: 'danger' },
  workflow: { label: '工作流', type: 'success' },
  approval: { label: '审批', type: 'primary' },
}

const getSourceTag = (source: string) => {
  return sourceTagMap[source] || { label: source || '其他', type: 'info' }
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

// 跳转到通知列表页
const goToList = () => {
  router.push('/notifications')
}

// 点击单条通知：未读则标记已读，并跳转到列表页
const handleClickNotification = async (notification: AppNotification) => {
  if (!notification.is_read) {
    try {
      await notificationStore.markAsRead(notification.id)
    } catch (error) {
      console.error('[NotificationBell] markAsRead failed:', error)
    }
  }
  goToList()
}

// 全部已读
const handleMarkAllAsRead = async () => {
  if (unreadCount.value === 0) return
  try {
    await notificationStore.markAllAsRead()
    ElMessage.success('已标记全部通知为已读')
  } catch (error) {
    console.error('[NotificationBell] markAllAsRead failed:', error)
    ElMessage.error('标记全部已读失败')
  }
}

onMounted(() => {
  notificationStore.refresh()
})
</script>

<template>
  <el-popover
    placement="bottom-end"
    :width="380"
    trigger="click"
    popper-class="notification-bell-popover"
  >
    <template #reference>
      <el-badge
        :value="unreadCount"
        :hidden="unreadCount === 0"
        :max="99"
        class="notification-badge"
      >
        <el-button type="primary" plain circle title="通知">
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>
    </template>

    <div class="notification-panel">
      <!-- 头部：标题 + 全部已读 -->
      <div class="panel-header">
        <span class="panel-title">通知</span>
        <el-button
          link
          type="primary"
          :disabled="unreadCount === 0"
          @click="handleMarkAllAsRead"
        >
          全部已读
        </el-button>
      </div>

      <!-- 列表区 -->
      <div class="panel-list">
        <div v-if="recentNotifications.length === 0" class="empty-state">
          暂无通知
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
          查看全部通知
        </el-button>
      </div>
    </div>
  </el-popover>
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
</style>
