<template>
  <div class="document-version-history">
    <div class="version-history__header">
      <h3 class="version-history__title">版本历史</h3>
      <el-button text @click="handleClose">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <div v-if="loading" class="version-history__loading">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="versions.length === 0" class="version-history__empty">
      <el-empty description="暂无版本历史" />
    </div>

    <div v-else class="version-history__list">
      <div
        v-for="version in versions"
        :key="version.id"
        class="version-item"
        :class="{ 'is-current': currentVersionId === version.id }"
        @click="handlePreview(version)"
      >
        <div class="version-item__info">
          <div class="version-item__name">{{ version.name }}</div>
          <div class="version-item__meta">
            <span class="version-item__number">#{{ version.versionNumber || version.version_number }}</span>
            <span class="version-item__summary">{{ version.changeSummary || version.change_summary }}</span>
          </div>
          <div class="version-item__time">
            <el-icon><Clock /></el-icon>
            {{ formatDate(version.createdAt || version.created_at || 0) }}
            <span v-if="version.createdByName || version.createdBy || version.created_by" class="version-item__creator">
              by {{ version.createdByName || getUserName(version.createdBy || version.created_by) }}
            </span>
          </div>
        </div>
        <div class="version-item__actions">
          <el-button
            v-if="currentVersionId !== version.id"
            type="primary"
            link
            size="small"
            @click.stop="handleRestore(version)"
          >
            恢复此版本
          </el-button>
          <el-tag v-else type="success" size="small">当前版本</el-tag>
        </div>
      </div>
    </div>

    <!-- 版本预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewVersion?.name"
      width="800px"
      destroy-on-close
      @open="handleDialogOpen"
    >
      <div class="version-preview">
        <div class="version-preview__meta">
          <el-tag size="small">#{{ previewVersion?.versionNumber || previewVersion?.version_number }}</el-tag>
          <span>{{ previewVersion?.changeSummary || previewVersion?.change_summary }}</span>
          <span v-if="previewVersion?.createdByName || previewVersion?.createdBy || previewVersion?.created_by" class="version-preview__creator">
            by {{ previewVersion?.createdByName || getUserName(previewVersion?.createdBy || previewVersion?.created_by) }}
          </span>
          <span class="version-preview__time">{{ formatDate(previewVersion?.createdAt || previewVersion?.created_at || 0) }}</span>
        </div>
        
        <!-- 编辑器容器始终在 DOM 中 -->
        <div ref="previewRef" class="version-preview__content"></div>
        
        <!-- 加载和错误状态覆盖层 -->
        <div v-if="previewLoading" class="version-preview__loading-overlay">
          <el-skeleton :rows="6" animated />
        </div>
        <div v-else-if="previewError" class="version-preview__error-overlay">
          <el-empty description="内容加载失败">
            <p>{{ previewError }}</p>
            <el-button type="primary" @click="reloadPreview">重新加载</el-button>
          </el-empty>
        </div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button
          v-if="previewVersion && previewVersion.id !== currentVersionId"
          type="primary"
          @click="handleRestore(previewVersion)"
        >
          恢复此版本
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue';
import { Close, Clock } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import FluentEditor from '@opentiny/fluent-editor';
import '@opentiny/fluent-editor/style.css';
import { documentVersionApiService } from '@/services/api/documentVersionApiService';
import type { DocumentVersion } from '@/types/documentVersion';
import { formatDateTime, initDayjsPlugins } from "@/utils/timezone";
import { useUserCacheStore } from '@/stores/userCacheStore';

const props = defineProps<{
  documentId: string;
  currentVersionId?: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'restore', version: DocumentVersion): void;
}>();

// 用户缓存存储
const userCacheStore = useUserCacheStore();

const versions = ref<DocumentVersion[]>([]);
const loading = ref(false);
const previewVisible = ref(false);
const previewVersion = ref<DocumentVersion | null>(null);
const previewRef = ref<HTMLDivElement>();
const previewLoading = ref(false);
const previewError = ref<string | null>(null);
let previewEditor: FluentEditor | null = null;

// 获取用户名的辅助函数
const getUserName = (userId?: string): string => {
  if (!userId) return '';
  const cachedUser = userCacheStore.getCachedUser(userId);
  return cachedUser?.name || userId;
};

const fetchVersions = async () => {
  loading.value = true;
  try {
    const { items } = await documentVersionApiService.getList(props.documentId);
    versions.value = items;
    
    // 收集所有创建者ID
    const userIds = items
      .map(version => version.createdBy || version.created_by)
      .filter((id): id is string => !!id);
    
    // 批量获取用户信息并缓存
    if (userIds.length > 0) {
      await userCacheStore.fetchUsers(userIds);
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '获取版本历史失败');
  } finally {
    loading.value = false;
  }
};

const handleClose = () => {
  emit('close');
};

const handlePreview = (version: DocumentVersion) => {
  previewVersion.value = version;
  previewVisible.value = true;
};

const handleRestore = async (version: DocumentVersion) => {
  try {
    await ElMessageBox.confirm(
      `确定要恢复到版本 "${version.name}" 吗？当前内容将被覆盖。`,
      '恢复版本',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );

    await documentVersionApiService.restore(props.documentId, version.id);
    ElMessage.success('版本恢复成功');
    previewVisible.value = false;
    emit('restore', version);
    await fetchVersions();
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '恢复版本失败');
    }
  }
};

const formatDate = (dateValue: any) => {
  return formatDateTime(dateValue, "YYYY-MM-DD HH:mm");
};

// 对话框打开事件
const handleDialogOpen = async () => {
  console.log('[DocumentVersionHistory] 对话框打开');
  await initPreviewEditor();
};

// 初始化或更新预览编辑器
const initPreviewEditor = async () => {
  if (!previewVersion.value) return;

  previewLoading.value = true;
  previewError.value = null;

  try {
    console.log('[DocumentVersionHistory] 开始初始化预览编辑器');
    
    // 简单等待，让 el-dialog 完全渲染
    await nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));
    
    if (!previewRef.value) {
      previewError.value = '编辑器容器未找到';
      console.error('[DocumentVersionHistory] 未能找到编辑器容器');
      return;
    }

    console.log('[DocumentVersionHistory] 初始化预览编辑器', {
      versionId: previewVersion.value.id,
      content: previewVersion.value.content,
      contentFormat: previewVersion.value.contentFormat || previewVersion.value.content_format
    });

    // 销毁旧编辑器
    previewEditor = null;

    // 创建新的编辑器实例
    previewEditor = new FluentEditor(previewRef.value, {
      theme: 'snow',
      readOnly: true,
      modules: {
        toolbar: false
      }
    });

    // 加载内容
    if (previewVersion.value.content) {
      const contentFormat = previewVersion.value.contentFormat || previewVersion.value.content_format || 'delta';
      
      try {
        let content;
        if (contentFormat === 'delta') {
          content = JSON.parse(previewVersion.value.content);
        } else {
          content = previewVersion.value.content;
        }
        
        console.log('[DocumentVersionHistory] 加载预览内容', { contentFormat, content });
        previewEditor.setContents(content);
      } catch (parseError) {
        console.error('[DocumentVersionHistory] 解析内容失败:', parseError);
        previewError.value = '内容解析失败';
      }
    } else {
      console.log('[DocumentVersionHistory] 版本内容为空');
    }
  } catch (error) {
    console.error('[DocumentVersionHistory] 初始化预览编辑器失败:', error);
    previewError.value = error instanceof Error ? error.message : '加载失败';
  } finally {
    previewLoading.value = false;
  }
};

// 重新加载预览
const reloadPreview = () => {
  if (previewVersion.value) {
    initPreviewEditor();
  }
};

// 监听对话框关闭进行清理
watch(previewVisible, (visible) => {
  if (!visible) {
    // 对话框关闭时清理
    previewEditor = null;
    previewError.value = null;
    previewLoading.value = false;
  }
});

onMounted(() => {
  initDayjsPlugins();
  fetchVersions();
});
</script>

<style scoped lang="scss">
.document-version-history {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--el-bg-color);
}

.version-history__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.version-history__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.version-history__loading {
  padding: 20px;
}

.version-history__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.version-history__list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.version-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--el-fill-color-light);
  }

  &.is-current {
    background-color: var(--el-color-success-light-9);
    border: 1px solid var(--el-color-success-light-5);
  }
}

.version-item__info {
  flex: 1;
  min-width: 0;
}

.version-item__name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.version-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.version-item__number {
  font-size: 12px;
  color: var(--el-color-primary);
  font-weight: 500;
}

.version-item__summary {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.version-item__time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);

  .el-icon {
    font-size: 12px;
  }
}

.version-item__creator {
  margin-left: 4px;
}

.version-item__actions {
  flex-shrink: 0;
  margin-left: 12px;
}

.version-preview {
  position: relative;
  
  &__meta {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--el-border-color-light);
  }

  &__creator {
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }

  &__time {
    margin-left: auto;
    color: var(--el-text-color-placeholder);
    font-size: 13px;
  }

  &__content {
    min-height: 300px;
    max-height: 500px;
    overflow-y: auto;

    :deep(.ql-toolbar) {
      display: none;
    }

    :deep(.ql-container) {
      border: none;
    }
  }

  &__loading-overlay,
  &__error-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    min-height: 300px;
    max-height: 500px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--el-bg-color);
    z-index: 10;
  }
}
</style>
