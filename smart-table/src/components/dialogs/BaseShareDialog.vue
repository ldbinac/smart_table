<template>
  <el-dialog
    v-model="dialogVisible"
    title="分享 Base"
    width="700px"
    :close-on-click-modal="false"
    class="base-share-dialog">
    
    <div v-loading="loading" class="share-content">
      <!-- 创建分享 -->
      <div class="create-share-section">
        <h3 class="section-title">创建分享链接</h3>
        <el-form
          ref="shareFormRef"
          :model="shareForm"
          :rules="shareFormRules"
          label-width="100px">
          <el-form-item label="权限" prop="permission">
            <el-radio-group v-model="shareForm.permission">
              <el-radio value="view">仅查看</el-radio>
              <el-radio value="edit">可编辑</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="有效期" prop="expiresAt">
            <el-select v-model="shareForm.expiresAtType" placeholder="请选择有效期">
              <el-option label="永久有效" value="permanent" />
              <el-option label="7 天" value="7days" />
              <el-option label="30 天" value="30days" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="shareForm.expiresAtType === 'custom'" label="过期时间">
            <el-date-picker
              v-model="shareForm.customExpiresAt"
              type="datetime"
              placeholder="选择过期时间"
              :disabled-date="disabledDate"
              value-format="X" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="creating" @click="handleCreateShare">
              创建分享链接
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 分享列表 -->
      <div class="share-list-section" v-if="shares.length > 0">
        <h3 class="section-title">我的分享</h3>
        <div class="share-list">
          <div
            v-for="share in shares"
            :key="share.id"
            class="share-item"
            :class="{ 'is-expired': isExpired(share) }">
            <div class="share-info">
              <div class="share-permission">
                <el-tag :type="share.permission === 'edit' ? 'warning' : 'info'" size="small">
                  {{ share.permission === 'edit' ? '可编辑' : '仅查看' }}
                </el-tag>
                <span class="share-status" v-if="isExpired(share)">已过期</span>
                <span class="share-status" v-else-if="!share.is_active">已禁用</span>
              </div>
              <div class="share-link">
                <el-input
                  :model-value="shareUrl(share.share_token)"
                  readonly
                  size="small"
                  class="share-link-input" />
              </div>
              <div class="share-meta">
                <span>访问 {{ share.access_count }} 次</span>
                <span>创建于 {{ formatDate(share.created_at) }}</span>
                <span v-if="share.expires_at">过期时间：{{ formatExpiresAt(share.expires_at) }}</span>
              </div>
            </div>
            <div class="share-actions">
              <el-button size="small" @click="copyShareLink(share.share_token)">
                复制链接
              </el-button>
              <el-button
                size="small"
                :type="share.is_active ? 'warning' : 'success'"
                @click="toggleShareStatus(share)">
                {{ share.is_active ? '禁用' : '启用' }}
              </el-button>
              <el-button size="small" type="danger" @click="handleDeleteShare(share.id)">
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="empty-state">
        <el-icon :size="64" color="#C0C4CC"><Share /></el-icon>
        <h3>暂无分享</h3>
        <p>您还没有创建任何分享链接</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="closeDialog">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Share } from '@element-plus/icons-vue';
import type { FormInstance, FormRules } from 'element-plus';
import { useBaseStore, type BaseShare } from '@/stores/baseStore';

const props = defineProps<{
  baseId: string;
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'share-changed'): void;
}>();

const baseStore = useBaseStore();

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
    { required: true, message: '请选择权限', trigger: 'change' }
  ],
  expiresAtType: [
    { required: true, message: '请选择有效期', trigger: 'change' }
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
    const data = await baseStore.fetchShares(props.baseId);
    shares.value = data;
  } catch (error) {
    console.error('加载分享列表失败:', error);
    ElMessage.error('加载分享列表失败');
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
  return Date.now() > share.expires_at;
}

// 格式化日期
function formatDate(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) return '今天';
  if (days === 1) return '昨天';
  if (days < 7) return `${days}天前`;
  return date.toLocaleDateString('zh-CN');
}

// 格式化过期时间
function formatExpiresAt(timestamp: number) {
  return new Date(timestamp).toLocaleDateString('zh-CN');
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
    
    await baseStore.createShare(props.baseId, shareForm.permission, expiresAt);
    ElMessage.success('分享链接创建成功');
    
    await loadShares();
    emit('share-changed');
    
    // 重置表单
    shareForm.permission = 'view';
    shareForm.expiresAtType = 'permanent';
    shareForm.customExpiresAt = null;
  } catch (error) {
    if (error !== 'cancel') {
      console.error('创建分享链接失败:', error);
      ElMessage.error('创建分享链接失败');
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
    ElMessage.success('链接已复制到剪贴板');
  } catch (error) {
    ElMessage.error('复制失败，请手动复制');
  }
}

// 切换分享状态
async function toggleShareStatus(share: BaseShare) {
  try {
    const newStatus = !share.is_active;
    const action = newStatus ? '启用' : '禁用';
    
    await ElMessageBox.confirm(
      `确定要${action}此分享链接吗？${newStatus ? '启用后将可以再次通过该链接访问' : '禁用后将无法通过该链接访问'}`,
      `确认${action}`,
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    await baseStore.updateShare(share.id, { is_active: newStatus });
    ElMessage.success(`${action}成功`);
    await loadShares();
    emit('share-changed');
  } catch (error) {
    if (error !== 'cancel') {
      console.error('切换分享状态失败:', error);
      ElMessage.error('操作失败');
    }
  }
}

// 删除分享
async function handleDeleteShare(shareId: string) {
  try {
    await ElMessageBox.confirm(
      '确定要删除此分享链接吗？删除后将无法通过该链接访问。',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    await baseStore.deleteShare(shareId);
    ElMessage.success('分享链接已删除');
    await loadShares();
    emit('share-changed');
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除分享失败:', error);
      ElMessage.error('删除分享失败');
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
