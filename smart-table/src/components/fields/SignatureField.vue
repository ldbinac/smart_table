<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Delete, ZoomIn } from '@element-plus/icons-vue';
import type { FieldEntity } from '@/db/schema';
import { attachmentService } from '@/db/services';
import { useBaseStore } from '@/stores';
import SignaturePad from './signature/SignaturePad.vue';

const baseStore = useBaseStore();
const { t } = useI18n();

interface Props {
  modelValue: string | null;
  field: FieldEntity;
  readonly?: boolean;
  recordId?: string;
  formShareToken?: string;
  /** 为 true 时，挂载后自动打开签字面板（用于 VTableView 弹窗模式） */
  initialOpen?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  initialOpen: false,
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void;
}>();

// ============ 状态 ============
const dialogVisible = ref(false);
const thumbnailUrl = ref<string | null>(null);
const isLoading = ref(false);
const previewVisible = ref(false);
const previewUrl = ref<string | null>(null);

// 用于签字面板展示已有签字的 Image（Base64 / Blob URL）
const existingImageUrl = ref<string | null>(null);

// 追踪需要释放的 Blob URL
let activeBlobUrls: string[] = [];

function createBlobURL(blob: Blob): string {
  const url = URL.createObjectURL(blob);
  activeBlobUrls.push(url);
  return url;
}

function revokeAllBlobURLs() {
  activeBlobUrls.forEach((url) => {
    try {
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  });
  activeBlobUrls = [];
}

// 当前签字的附件 ID
const currentAttachmentId = computed(() => {
  return typeof props.modelValue === 'string' ? props.modelValue : null;
});

// 是否有签字
const hasSignature = computed(() => currentAttachmentId.value !== null);

// ============ 缩略图加载 ============
async function loadThumbnail() {
  if (!currentAttachmentId.value) {
    thumbnailUrl.value = null;
    existingImageUrl.value = null;
    return;
  }

  isLoading.value = true;
  try {
    const local = await attachmentService.getAttachment(currentAttachmentId.value);
    if (local?.data) {
      // 优先使用 IndexedDB 缓存
      const url = createBlobURL(local.data);
      thumbnailUrl.value = url;
      existingImageUrl.value = url;
    } else {
      // IndexedDB 没有 → 从后端下载（支持分享表单匿名提交的附件）
      const blob = await attachmentService.getAttachmentBlob(currentAttachmentId.value);
      const url = createBlobURL(blob);
      thumbnailUrl.value = url;
      existingImageUrl.value = url;
    }
  } catch (err) {
    console.error('加载签字缩略图失败:', err);
    thumbnailUrl.value = null;
    existingImageUrl.value = null;
  } finally {
    isLoading.value = false;
  }
}

watch(
  () => props.modelValue,
  () => {
    loadThumbnail();
  },
  { immediate: true }
);

// ============ 打开签字面板 ============
function openSignaturePad() {
  if (props.readonly) {
    // 只读模式下点击只预览
    if (hasSignature.value) {
      handlePreview();
    }
    return;
  }
  // 先刷新已有签字
  loadThumbnail();
  dialogVisible.value = true;
}

function closeDialog() {
  dialogVisible.value = false;
}

// ============ 保存签字 ============
async function handleSave(blob: Blob) {
  if (!props.recordId) {
    ElMessage.warning(t('view.attachment.saveRecordFirst'));
    dialogVisible.value = false;
    return;
  }

  isLoading.value = true;
  try {
    // 将 Blob 转为 File
    const fileName = `signature_${Date.now()}.png`;
    const file = new File([blob], fileName, { type: 'image/png' });

    const context = {
      recordId: props.recordId,
      fieldId: props.field.id,
      tableId: props.field.tableId,
      baseId: baseStore.currentBaseId || '',
      formShareToken: props.formShareToken,
    };

    const uploaded = await attachmentService.uploadFiles([file], context, undefined);

    if (uploaded.length > 0) {
      const newAttachmentId = uploaded[0].id;

      // 如果之前有旧签字，先删除旧附件
      const oldAttachmentId = currentAttachmentId.value;
      if (oldAttachmentId && oldAttachmentId !== newAttachmentId) {
        try {
          await attachmentService.deleteAttachment(oldAttachmentId);
        } catch (err) {
          console.error('删除旧签字附件失败:', err);
        }
      }

      emit('update:modelValue', newAttachmentId);
      ElMessage.success(t('field.signature.saveSuccess'));
      dialogVisible.value = false;
    }
  } catch (err: any) {
    ElMessage.error(err?.message || 'Failed to save signature');
    console.error('保存签字失败:', err);
  } finally {
    isLoading.value = false;
  }
}

// ============ 删除签字 ============
async function handleDelete() {
  if (!hasSignature.value || !currentAttachmentId.value) return;

  try {
    await ElMessageBox.confirm(
      t('field.signature.deleteConfirm'),
      t('common.confirmTitle') || 'Confirm',
      {
        confirmButtonText: t('common.confirmBtn') || 'Confirm',
        cancelButtonText: t('common.cancel') || 'Cancel',
        type: 'warning',
      }
    );

    await attachmentService.deleteAttachment(currentAttachmentId.value);
    emit('update:modelValue', null);
    dialogVisible.value = false;
    ElMessage.success(t('common.deleted') || 'Deleted');
  } catch (err) {
    // 用户取消
    if (err !== 'cancel') {
      console.error('删除签字失败:', err);
    }
  }
}

// ============ 预览 ============
async function handlePreview() {
  if (!currentAttachmentId.value) return;
  try {
    previewUrl.value = await attachmentService.getAttachmentUrl(currentAttachmentId.value);
    previewVisible.value = true;
  } catch (err) {
    console.error('加载预览失败:', err);
  }
}

// ============ 生命周期 ============
onMounted(() => {
  loadThumbnail();
  // initialOpen 模式（VTableView 弹窗）：加载完缩略图后自动打开签字面板
  if (props.initialOpen) {
    nextTick(() => {
      dialogVisible.value = true;
    });
  }
});

onUnmounted(() => {
  revokeAllBlobURLs();
});

// ============ 暴露方法 ============
defineExpose({
  openDialog: () => {
    dialogVisible.value = true;
  },
  closeDialog: () => {
    dialogVisible.value = false;
  },
});
</script>

<template>
  <div class="signature-field" :class="{ 'is-readonly': readonly }">
    <!-- 有签字：显示缩略图 -->
    <div
      v-if="hasSignature && thumbnailUrl"
      class="signature-thumbnail"
      :class="{ 'is-clickable': !readonly }"
      @click="!readonly && openSignaturePad()"
    >
      <img :src="thumbnailUrl" alt="signature" class="signature-img" />
      <!-- 悬浮操作层 -->
      <div v-if="!readonly" class="thumbnail-overlay">
        <el-icon class="overlay-icon"><ZoomIn /></el-icon>
        <el-icon class="overlay-icon" @click.stop="handleDelete">
          <Delete />
        </el-icon>
      </div>
    </div>

    <!-- 有签字但缩略图加载中 -->
    <div
      v-else-if="hasSignature && isLoading"
      class="signature-thumbnail is-loading"
    >
      <el-icon class="loading-icon"><Loading /></el-icon>
    </div>

    <!-- 有签字但缩略图加载失败 -->
    <div
      v-else-if="hasSignature"
      class="signature-thumbnail is-error"
      :class="{ 'is-clickable': !readonly }"
      @click="!readonly && openSignaturePad()"
    >
      <el-icon><Picture /></el-icon>
    </div>

    <!-- 无签字：空状态 -->
    <div
      v-else
      class="signature-empty"
      :class="{ 'is-clickable': !readonly }"
      @click="!readonly && openSignaturePad()"
    >
      <el-icon class="empty-icon"><EditPen /></el-icon>
      <span>{{ t('field.signature.emptyHint') }}</span>
    </div>

    <!-- 签字面板 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="t('field.signature.title')"
      width="600px"
      :close-on-click-modal="true"
      destroy-on-close
      @close="closeDialog"
    >
      <SignaturePad
        :existing-image="existingImageUrl"
        @save="handleSave"
        @cancel="closeDialog"
      />
    </el-dialog>

    <!-- 图片预览 Dialog -->
    <el-dialog
      v-model="previewVisible"
      width="80%"
      top="5vh"
      destroy-on-close
      class="signature-preview-dialog"
    >
      <img
        v-if="previewUrl"
        :src="previewUrl"
        class="preview-img"
        alt="signature preview"
      />
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { Loading, Picture, EditPen } from '@element-plus/icons-vue';
export default {
  components: { Loading, Picture, EditPen },
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.signature-field {
  width: 100%;
  min-height: 48px;
}

.signature-thumbnail {
  position: relative;
  width: 100%;
  max-width: 120px;
  height: 48px;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fff;

  &.is-clickable {
    cursor: pointer;

    &:hover .thumbnail-overlay {
      opacity: 1;
    }
  }

  &.is-loading,
  &.is-error {
    color: $text-disabled;
  }

  .loading-icon {
    animation: rotating 1s linear infinite;
  }
}

.signature-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.thumbnail-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  background-color: rgba(0, 0, 0, 0.5);
  opacity: 0;
  transition: opacity 0.2s ease;

  .overlay-icon {
    color: #fff;
    font-size: 18px;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;

    &:hover {
      background-color: rgba(255, 255, 255, 0.2);
    }
  }
}

.signature-empty {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-sm;
  border: 1px dashed $border-color;
  border-radius: $border-radius-sm;
  background-color: $bg-color;
  color: $text-disabled;
  font-size: $font-size-sm;

  &.is-clickable {
    cursor: pointer;

    &:hover {
      border-color: $primary-color;
      color: $primary-color;
      background-color: rgba($primary-color, 0.05);
    }
  }

  .empty-icon {
    font-size: 16px;
  }
}

.signature-preview-dialog {
  :deep(.el-dialog__body) {
    padding: $spacing-md;
    text-align: center;
    background-color: #f5f5f5;
  }

  .preview-img {
    max-width: 100%;
    max-height: 80vh;
    object-fit: contain;
    background-color: #fff;
    padding: $spacing-md;
    border-radius: $border-radius-md;
  }
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
