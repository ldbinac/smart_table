<template>
  <el-dialog
    v-model="dialogVisible"
    :title="t('view.share.shareBaseTitle')"
    width="700px"
    :close-on-click-modal="false"
    class="base-share-dialog">

    <div v-loading="loading" class="share-content">
      <!-- 创建分享 -->
      <div class="create-share-section">
        <h3 class="section-title">{{ t('view.share.createShareLink') }}</h3>
        <el-form
          ref="shareFormRef"
          :model="shareForm"
          :rules="shareFormRules"
          label-width="100px">
          <el-form-item :label="t('view.share.permission')" prop="permission">
            <el-radio-group v-model="shareForm.permission">
              <el-radio value="view">{{ t('view.share.permissionView') }}</el-radio>
              <el-radio value="edit">{{ t('view.share.permissionEdit') }}</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item :label="t('view.share.validity')" prop="expiresAt">
            <el-select v-model="shareForm.expiresAtType" :placeholder="t('view.share.selectValidity')">
              <el-option :label="t('view.share.permanent')" value="permanent" />
              <el-option :label="t('view.share.days7')" value="7days" />
              <el-option :label="t('view.share.days30')" value="30days" />
              <el-option :label="t('view.share.custom')" value="custom" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="shareForm.expiresAtType === 'custom'" :label="t('view.share.expireTime')">
            <el-date-picker
              v-model="shareForm.customExpiresAt"
              type="datetime"
              :placeholder="t('view.share.selectExpireTime')"
              :disabled-date="disabledDate"
              value-format="X" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="creating" @click="handleCreateShare">
              {{ t('view.share.createShareLink') }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 分享列表 -->
      <div class="share-list-section" v-if="shares.length > 0">
        <h3 class="section-title">{{ t('view.share.myShares') }}</h3>
        <div class="share-list">
          <div
            v-for="share in shares"
            :key="share.id"
            class="share-item"
            :class="{ 'is-expired': isExpired(share) }">
            <div class="share-info">
              <div class="share-permission">
                <el-tag :type="share.permission === 'edit' ? 'warning' : 'info'" size="small">
                  {{ share.permission === 'edit' ? t('view.share.shareEdit') : t('view.share.shareView') }}
                </el-tag>
                <span class="share-status" v-if="isExpired(share)">{{ t('view.share.shareExpired') }}</span>
                <span class="share-status" v-else-if="!share.is_active">{{ t('view.share.shareDisabled') }}</span>
              </div>
              <div class="share-link">
                <el-input
                  :model-value="shareUrl(share.share_token)"
                  readonly
                  size="small"
                  class="share-link-input" />
              </div>
              <div class="share-meta">
                <span>{{ t('view.share.visitCount', { count: share.access_count }) }}</span>
                <span>{{ t('view.share.createdAt', { date: formatDate(share.created_at) }) }}</span>
                <span v-if="share.expires_at">{{ t('view.share.expiryAt', { date: formatExpiresAt(share.expires_at) }) }}</span>
              </div>
            </div>
            <div class="share-actions">
              <el-button size="small" @click="copyShareLink(share.share_token)">
                {{ t('view.share.copyLink') }}
              </el-button>
              <el-button
                size="small"
                :type="share.is_active ? 'warning' : 'success'"
                @click="toggleShareStatus(share)">
                {{ share.is_active ? t('view.share.disable') : t('view.share.enable') }}
              </el-button>
              <el-button size="small" type="danger" @click="handleDeleteShare(share.id)">
                {{ t('view.delete') }}
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="empty-state">
        <el-icon :size="64" color="#C0C4CC"><Share /></el-icon>
        <h3>{{ t('view.share.noShares') }}</h3>
        <p>{{ t('view.share.noSharesDesc') }}</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="closeDialog">{{ t('view.close') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Share } from '@element-plus/icons-vue';
import type { FormInstance, FormRules } from 'element-plus';
import { useShareStore, type BaseShare } from '@/stores/shareStore';

const { t } = useI18n();

const props = defineProps<{
  baseId: string;
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'share-changed'): void;
}>();

const shareStore = useShareStore();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const loading = ref(false);
const creating = ref(false);

const shares = ref<BaseShare[]>([]);

const shareFormRef = ref<FormInstance>();
const shareForm = reactive({
  permission: 'view' as 'view' | 'edit',
  expiresAtType: 'permanent' as 'permanent' | '7days' | '30days' | 'custom',
  customExpiresAt: null as number | null
});

const shareFormRules: FormRules = {
  permission: [
    { required: true, message: t('view.base.selectPermission'), trigger: 'change' }
  ],
  expiresAtType: [
    { required: true, message: t('view.base.selectExpiry'), trigger: 'change' }
  ]
};

// 监听对话框打开，加载分享列表
watch(() => props.visible, async (newVal) => {
  if (newVal && props.baseId) {
    await loadShares();
  }
});

// 禁用过去的日期
function disabledDate(date: Date) {
  return date.getTime() < Date.now();
}

// 加载分享列表
async function loadShares() {
  loading.value = true;
  try {
    const data = await shareStore.fetchShares(props.baseId);
    shares.value = data;
  } catch (error) {
    console.error('加载分享列表失败:', error);
    ElMessage.error(t('view.share.shareListLoadFailed'));
  } finally {
    loading.value = false;
  }
}

// 生成分享链接
function shareUrl(token: string) {
  return `${window.location.origin}/#/share/${token}`;
}

// 检查是否过期
function isExpired(share: BaseShare) {
  if (!share.expires_at) return false;
  // 后端返回的 expires_at 是秒级时间戳，Date.now() 是毫秒级，需要转换
  return Date.now() > share.expires_at * 1000;
}

import { formatDate as tzFormatDate } from "@/utils/timezone";

// 格式化日期
function formatDate(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return t('view.today');
  if (days === 1) return t('view.yesterday');
  if (days < 7) return t('view.daysAgo', { count: days });
  return tzFormatDate(dateString, "YYYY-MM-DD");
}

// 格式化过期时间
function formatExpiresAt(timestamp: number) {
  // 后端返回的 expires_at 是秒级时间戳，dayjs 需要毫秒级
  return tzFormatDate(timestamp * 1000, "YYYY-MM-DD");
}

// 创建分享链接
async function handleCreateShare() {
  if (!shareFormRef.value) return;
  
  try {
    await shareFormRef.value.validate();
    creating.value = true;
    
    let expiresAt: number | undefined;
    if (shareForm.expiresAtType === '7days') {
      expiresAt = Date.now() + 7 * 24 * 60 * 60 * 1000;
    } else if (shareForm.expiresAtType === '30days') {
      expiresAt = Date.now() + 30 * 24 * 60 * 60 * 1000;
    } else if (shareForm.expiresAtType === 'custom' && shareForm.customExpiresAt) {
      expiresAt = shareForm.customExpiresAt;
    }
    
    await shareStore.createShare(props.baseId, shareForm.permission, expiresAt);
    ElMessage.success(t('view.share.shareCreated'));
    
    await loadShares();
    emit('share-changed');
    
    // 重置表单
    shareForm.permission = 'view';
    shareForm.expiresAtType = 'permanent';
    shareForm.customExpiresAt = null;
  } catch (error) {
    if (error !== 'cancel') {
      console.error('创建分享链接失败:', error);
      ElMessage.error(t('view.share.createShareFailed'));
    }
  } finally {
    creating.value = false;
  }
}

// 复制分享链接
async function copyShareLink(token: string) {
  const url = shareUrl(token);
  try {
    await navigator.clipboard.writeText(url);
    ElMessage.success(t('view.share.linkCopied'));
  } catch (error) {
    ElMessage.error(t('view.share.copyFailedManual'));
  }
}

// 切换分享状态
async function toggleShareStatus(share: BaseShare) {
  try {
    const newStatus = !share.is_active;
    const action = newStatus ? t('view.share.enable') : t('view.share.disable');

    await ElMessageBox.confirm(
      t('view.share.toggleShareConfirm', {
        action,
        hint: newStatus ? t('view.share.enableHint') : t('view.share.disableHint'),
      }),
      t('view.share.toggleShareTitle', { action }),
      {
        confirmButtonText: t('view.confirm'),
        cancelButtonText: t('view.cancel'),
        type: 'warning'
      }
    );

    await shareStore.updateShare(share.id, { is_active: newStatus });
    ElMessage.success(t('view.share.toggleSuccess', { action }));
    await loadShares();
    emit('share-changed');
  } catch (error: any) {
    // ElMessageBox.confirm 取消时 reject 'cancel'，点 X 关闭时 reject 'close'
    if (error !== 'cancel' && error !== 'close') {
      console.error('切换分享状态失败:', error);
      const msg = error?.message || error?.response?.data?.message || t('view.base.toggleFailed');
      ElMessage.error(msg);
    }
  }
}

// 删除分享
async function handleDeleteShare(shareId: string) {
  try {
    await ElMessageBox.confirm(
      t('view.share.deleteShareConfirm'),
      t('view.share.deleteShareTitle'),
      {
        confirmButtonText: t('view.confirm'),
        cancelButtonText: t('view.cancel'),
        type: 'warning'
      }
    );

    await shareStore.deleteShare(shareId);
    ElMessage.success(t('view.share.shareDeleted'));
    await loadShares();
    emit('share-changed');
  } catch (error: any) {
    // ElMessageBox.confirm 取消时 reject 'cancel'，点 X 关闭时 reject 'close'
    if (error !== 'cancel' && error !== 'close') {
      console.error('删除分享失败:', error);
      const msg = error?.message || error?.response?.data?.message || t('view.share.deleteShareFailed');
      ElMessage.error(msg);
    }
  }
}

function closeDialog() {
  dialogVisible.value = false;
}
</script>

<style lang="scss" scoped>
.base-share-dialog {
  .share-content {
    min-height: 400px;
  }

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #e5e7eb;
  }

  .create-share-section {
    margin-bottom: 32px;
  }

  .share-list-section {
    .share-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .share-item {
      padding: 16px;
      background: #f9fafb;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
      transition: all 0.3s ease;

      &:hover {
        background: #f3f4f6;
      }

      &.is-expired {
        opacity: 0.6;
        background: #f3f4f6;
      }

      .share-info {
        margin-bottom: 12px;

        .share-permission {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;

          .share-status {
            font-size: 12px;
            color: #ef4444;
          }
        }

        .share-link-input {
          :deep(.el-input__inner) {
            background: white;
            font-size: 13px;
          }
        }

        .share-meta {
          margin-top: 8px;
          font-size: 12px;
          color: #6b7280;
          display: flex;
          gap: 16px;
        }
      }

      .share-actions {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
      }
    }
  }

  .empty-state {
    text-align: center;
    padding: 60px 20px;

    h3 {
      margin: 16px 0 8px;
      font-size: 18px;
      color: #374151;
    }

    p {
      margin: 0;
      font-size: 14px;
      color: #6b7280;
    }
  }
}
</style>
