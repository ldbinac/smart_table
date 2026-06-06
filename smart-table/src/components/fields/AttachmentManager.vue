<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { UploadFile } from 'element-plus';
import {
  UploadFilled,
  Document,
  Picture,
  VideoCamera,
  Headset,
  Delete,
  Download,
  View,
  Loading,
  ZoomIn,
  ZoomOut,
  RefreshRight,
  Close
} from '@element-plus/icons-vue';
import type { FieldEntity } from '@/db/schema';
import type { CellValue } from '@/types';
import type { AttachmentFile, AttachmentFieldOptions } from '@/types/attachment';
import { formatFileSize, isImageFile, isVideoFile, isAudioFile } from '@/types/attachment';
import { attachmentService } from '@/db/services';
import { AttachmentError } from '@/utils/attachment';
import { useBaseStore } from '@/stores';

const baseStore = useBaseStore();

interface Props {
  field: FieldEntity;
  recordId?: string;
  modelValue: CellValue;
  position: { x: number; y: number };
}

const props = withDefaults(defineProps<Props>(), {});

const emit = defineEmits<{
  (e: 'update:modelValue', value: CellValue): void;
  (e: 'close'): void;
}>();

// 状态
const files = ref<AttachmentFile[]>([]);
const uploading = ref(false);
const uploadProgress = ref(0);
const currentUploadFile = ref('');
const previewVisible = ref(false);
const previewFile = ref<AttachmentFile | null>(null);

// 图片预览状态
const imageScale = ref(1);
const imagePosition = ref({ x: 0, y: 0 });
const isDragging = ref(false);
const dragStart = ref({ x: 0, y: 0 });

// 图片预览样式
const imagePreviewStyle = computed(() => ({
  transform: `scale(${imageScale.value}) translate(${imagePosition.value.x}px, ${imagePosition.value.y}px)`,
  cursor: isDragging.value ? 'grabbing' : 'grab'
}));

// 初始化预览
function initPreview() {
  imageScale.value = 1;
  imagePosition.value = { x: 0, y: 0 };
}

// 放大
function zoomIn() {
  if (imageScale.value < 5) {
    imageScale.value = Math.min(5, imageScale.value + 0.25);
  }
}

// 缩小
function zoomOut() {
  if (imageScale.value > 0.25) {
    imageScale.value = Math.max(0.25, imageScale.value - 0.25);
  }
}

// 重置缩放
function resetZoom() {
  imageScale.value = 1;
  imagePosition.value = { x: 0, y: 0 };
}

// 处理鼠标滚轮缩放
function handleImageWheel(e: WheelEvent) {
  e.preventDefault();
  if (e.deltaY < 0) {
    zoomIn();
  } else {
    zoomOut();
  }
}

// 开始拖拽
function startImageDrag(e: MouseEvent) {
  isDragging.value = true;
  dragStart.value = {
    x: e.clientX - imagePosition.value.x,
    y: e.clientY - imagePosition.value.y
  };
}

// 拖拽中
function handleImageDrag(e: MouseEvent) {
  if (!isDragging.value) return;
  imagePosition.value = {
    x: e.clientX - dragStart.value.x,
    y: e.clientY - dragStart.value.y
  };
}

// 停止拖拽
function stopImageDrag() {
  isDragging.value = false;
}

// 计算属性
const options = computed<AttachmentFieldOptions>(() => {
  return (props.field.options as AttachmentFieldOptions) || {};
});

const acceptTypes = computed(() => {
  const types = options.value.acceptTypes;
  return types?.join(',') || '*';
});

const maxSize = computed(() => {
  return options.value.maxSize || 10 * 1024 * 1024; // 默认 10MB
});

const maxCount = computed(() => {
  return options.value.maxCount || 20; // 默认 20 个文件
});

const canUpload = computed(() => {
  return files.value.length < maxCount.value;
});

// 监听值变化
watch(
  () => props.modelValue,
  async (newVal) => {
    if (Array.isArray(newVal)) {
      const processedFiles: AttachmentFile[] = [];

      for (const item of newVal) {
        if (typeof item === 'string') {
          try {
            const attachment = await attachmentService.getAttachment(item);
            if (attachment) {
              processedFiles.push({
                id: attachment.id,
                name: attachment.name,
                originalName: attachment.originalName,
                size: attachment.size,
                type: attachment.type,
                fileType: attachment.fileType as any,
                extension: attachment.extension,
                url: (attachment as any).url,
                thumbnail: attachment.thumbnail as any,
                createdAt: attachment.createdAt
              });
            }
          } catch (error) {
            console.error('获取附件详情失败:', item, error);
          }
        } else if (item && typeof item === 'object' && item.id) {
          processedFiles.push(item as AttachmentFile);
        }
      }

      files.value = processedFiles;
    } else {
      files.value = [];
    }
  },
  { immediate: true }
);

// 获取文件图标
function getFileIcon(file: AttachmentFile) {
  if (isImageFile(file)) return Picture;
  if (isVideoFile(file)) return VideoCamera;
  if (isAudioFile(file)) return Headset;
  return Document;
}

// 获取文件图标颜色
function getFileIconColor(file: AttachmentFile): string {
  if (isImageFile(file)) return '#67C23A';
  if (isVideoFile(file)) return '#409EFF';
  if (isAudioFile(file)) return '#E6A23C';
  return '#909399';
}

// 格式化上传时间
function formatUploadTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;

  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`;

  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  if (year === new Date(now).getFullYear()) {
    return `${month}-${day} ${hours}:${minutes}`;
  }
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

// 处理上传
async function handleUpload(uploadFile: UploadFile) {
  const file = uploadFile.raw;
  if (!file) return;

  if (!props.recordId) {
    ElMessage.error('请先保存记录后再上传附件');
    return;
  }

  uploading.value = true;
  uploadProgress.value = 0;
  currentUploadFile.value = file.name;

  try {
    const context = {
      recordId: props.recordId,
      fieldId: props.field.id,
      tableId: props.field.tableId,
      baseId: baseStore.currentBaseId || ''
    };

    const uploadedFiles = await attachmentService.uploadFiles(
      [file],
      context,
      options.value,
      (progress, name) => {
        uploadProgress.value = progress;
        currentUploadFile.value = name;
      }
    );

    files.value = [...files.value, ...uploadedFiles];
    emit('update:modelValue', files.value);

    ElMessage.success(`文件 "${file.name}" 上传成功`);
  } catch (error) {
    if (error instanceof AttachmentError) {
      ElMessage.error(error.message);
    } else {
      ElMessage.error('文件上传失败');
      console.error('Upload error:', error);
    }
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
    currentUploadFile.value = '';
  }
}

// 处理删除
async function handleRemove(fileId: string) {
  try {
    await ElMessageBox.confirm('确定要删除这个附件吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    });

    await attachmentService.deleteAttachment(fileId);

    files.value = files.value.filter(f => f.id !== fileId);
    emit('update:modelValue', files.value);

    ElMessage.success('附件已删除');
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
      console.error('Delete error:', error);
    }
  }
}

// 处理下载
async function handleDownload(file: AttachmentFile) {
  try {
    await attachmentService.downloadAttachment(file.id);
  } catch (error) {
    if (error instanceof AttachmentError) {
      ElMessage.error(error.message);
    } else {
      ElMessage.error('下载失败');
      console.error('Download error:', error);
    }
  }
}

// 处理预览
async function handlePreview(file: AttachmentFile) {
  previewFile.value = file;
  previewVisible.value = true;

  if ((isImageFile(file) || isVideoFile(file)) && !file.url) {
    try {
      const url = await attachmentService.getAttachmentUrl(file.id);
      file.url = url;
    } catch (error) {
      console.error('获取预览 URL 失败:', error);
    }
  }
}

// 判断是否可以预览
function canPreview(file: AttachmentFile): boolean {
  return isImageFile(file) || isVideoFile(file) || isAudioFile(file);
}

// 关闭面板
function closePanel() {
  emit('close');
}

// 处理 Escape 键
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    closePanel();
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <teleport to="body">
    <!-- 遮罩层 -->
    <div class="attachment-manager-overlay" @click.self="closePanel" />

    <!-- 面板 -->
    <div
      class="attachment-manager-panel"
      :style="{
        left: position.x + 'px',
        top: position.y + 'px'
      }"
      @click.stop
    >
      <!-- 面板头部 -->
      <div class="panel-header">
        <span class="panel-title">附件管理</span>
        <el-button
          class="panel-close-btn"
          link
          size="small"
          @click="closePanel"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <!-- 面板内容 -->
      <div class="panel-body">
        <!-- 上传区域 -->
        <div v-if="canUpload" class="upload-area">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :accept="acceptTypes"
            :on-change="handleUpload"
            :disabled="uploading"
            drag
            multiple
            class="attachment-uploader"
          >
            <el-icon class="upload-icon" :class="{ 'is-uploading': uploading }">
              <UploadFilled v-if="!uploading" />
              <Loading v-else class="is-loading" />
            </el-icon>
            <div class="upload-text">
              <template v-if="!uploading">
                拖拽文件到此处或<em>点击上传</em>
              </template>
              <template v-else>
                正在上传 {{ currentUploadFile }}... {{ uploadProgress }}%
              </template>
            </div>
            <template #tip>
              <div class="upload-tip">
                <div>最大文件大小: {{ formatFileSize(maxSize) }}</div>
                <div v-if="maxCount">最多 {{ maxCount }} 个文件</div>
              </div>
            </template>
          </el-upload>
        </div>

        <!-- 文件列表 -->
        <div v-if="files.length > 0" class="file-list">
          <div
            v-for="file in files"
            :key="file.id"
            class="file-item"
          >
            <!-- 文件预览图 -->
            <div
              class="file-preview"
              :class="{ 'is-clickable': canPreview(file) }"
              @click="canPreview(file) && handlePreview(file)"
            >
              <img
                v-if="file.thumbnail"
                :src="file.thumbnail"
                class="file-thumbnail"
                :alt="file.originalName"
              />
              <div
                v-else
                class="file-icon-wrapper"
                :style="{ backgroundColor: getFileIconColor(file) + '20' }"
              >
                <el-icon class="file-icon" :style="{ color: getFileIconColor(file) }">
                  <component :is="getFileIcon(file)" />
                </el-icon>
              </div>
            </div>

            <!-- 文件信息 -->
            <div class="file-info">
              <span class="file-name" :title="file.originalName">{{ file.originalName }}</span>
              <div class="file-meta">
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
                <span class="file-time">{{ formatUploadTime(file.createdAt) }}</span>
              </div>
            </div>

            <!-- 文件操作 -->
            <div class="file-actions">
              <el-button
                v-if="canPreview(file)"
                link
                size="small"
                @click="handlePreview(file)"
              >
                <el-icon><View /></el-icon>
              </el-button>
              <el-button link size="small" @click="handleDownload(file)">
                <el-icon><Download /></el-icon>
              </el-button>
              <el-button
                link
                size="small"
                type="danger"
                @click="handleRemove(file.id)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <el-icon class="empty-icon"><Document /></el-icon>
          <span class="empty-text">暂无附件</span>
        </div>
      </div>

      <!-- 预览对话框 -->
      <el-dialog
        v-model="previewVisible"
        :title="previewFile?.originalName || '预览'"
        width="90%"
        top="5vh"
        destroy-on-close
        class="attachment-preview-dialog"
        @opened="initPreview"
      >
        <div v-if="previewFile" class="preview-content">
          <!-- 图片预览 -->
          <div v-if="isImageFile(previewFile)" class="image-preview-container">
            <div class="image-preview-wrapper" @wheel="handleImageWheel">
              <img
                :src="previewFile.url || previewFile.thumbnail"
                class="preview-image"
                :alt="previewFile.originalName"
                :style="imagePreviewStyle"
                @mousedown="startImageDrag"
                @mousemove="handleImageDrag"
                @mouseup="stopImageDrag"
                @mouseleave="stopImageDrag"
              />
            </div>
            <div class="preview-toolbar">
              <el-button-group>
                <el-button size="small" @click="zoomOut">
                  <el-icon><ZoomOut /></el-icon>
                </el-button>
                <el-button size="small" disabled>{{ Math.round(imageScale * 100) }}%</el-button>
                <el-button size="small" @click="zoomIn">
                  <el-icon><ZoomIn /></el-icon>
                </el-button>
                <el-button size="small" @click="resetZoom">
                  <el-icon><RefreshRight /></el-icon> 重置
                </el-button>
              </el-button-group>
              <el-button size="small" type="primary" @click="handleDownload(previewFile)">
                <el-icon><Download /></el-icon> 下载
              </el-button>
            </div>
          </div>
          <!-- 视频预览 -->
          <video
            v-else-if="isVideoFile(previewFile)"
            controls
            class="preview-video"
          >
            <source :src="previewFile.url" :type="previewFile.type" />
            您的浏览器不支持视频播放
          </video>
          <!-- 音频预览 -->
          <audio
            v-else-if="isAudioFile(previewFile)"
            controls
            class="preview-audio"
          >
            <source :src="previewFile.url" :type="previewFile.type" />
            您的浏览器不支持音频播放
          </audio>
          <!-- 其他文件 -->
          <div v-else class="preview-other">
            <el-icon size="64"><Document /></el-icon>
            <p>该文件类型暂不支持预览</p>
            <el-button type="primary" @click="handleDownload(previewFile)">
              下载文件
            </el-button>
          </div>
        </div>
      </el-dialog>
    </div>
  </teleport>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.attachment-manager-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 9998;
}

.attachment-manager-panel {
  position: fixed;
  z-index: 9999;
  max-width: 420px;
  width: 380px;
  max-height: 480px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-xl;
  transform: translateY(0);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-color;
  flex-shrink: 0;
}

.panel-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
}

.panel-close-btn {
  color: $text-disabled;

  &:hover {
    color: $text-primary;
  }
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-md $spacing-lg;
}

.upload-area {
  margin-bottom: $spacing-md;

  :deep(.el-upload-dragger) {
    padding: $spacing-lg;
    border-radius: $border-radius-md;
    border-style: dashed;
    transition: all 0.3s ease;

    &:hover {
      border-color: $primary-color;
    }

    &.is-dragover {
      border-color: $primary-color;
      background-color: rgba($primary-color, 0.05);
    }
  }

  .upload-icon {
    font-size: 28px;
    color: $text-disabled;
    margin-bottom: $spacing-xs;
    transition: all 0.3s ease;

    &.is-uploading {
      color: $primary-color;
    }

    &.is-loading {
      animation: rotating 2s linear infinite;
    }
  }

  .upload-text {
    font-size: $font-size-sm;
    color: $text-secondary;
    text-align: center;

    em {
      color: $primary-color;
      font-style: normal;
      font-weight: 500;
      cursor: pointer;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .upload-tip {
    font-size: $font-size-xs;
    color: $text-disabled;
    margin-top: $spacing-xs;
    text-align: center;
    line-height: 1.5;
  }
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.file-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-sm;
  border: 1px solid $border-color;
  transition: all 0.2s ease;

  &:hover {
    border-color: $primary-color;
    background-color: rgba($primary-color, 0.02);
  }
}

.file-preview {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: $surface-color;
  border-radius: $border-radius-sm;
  overflow: hidden;
  flex-shrink: 0;

  &.is-clickable {
    cursor: pointer;

    &:hover {
      opacity: 0.8;
    }
  }
}

.file-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-icon-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $border-radius-sm;
}

.file-icon {
  font-size: 20px;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: $font-size-sm;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-size-xs;
  color: $text-disabled;
}

.file-time {
  &::before {
    content: '·';
    margin-right: $spacing-sm;
  }
}

.file-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s ease;

  .file-item:hover & {
    opacity: 1;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  padding: $spacing-3xl $spacing-md;
  color: $text-disabled;
}

.empty-icon {
  font-size: 40px;
}

.empty-text {
  font-size: $font-size-sm;
}

// 预览对话框样式
:deep(.attachment-preview-dialog) {
  .el-dialog__body {
    padding: 0;
  }
}

.preview-content {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  background-color: #f5f5f5;
  padding: $spacing-lg;
}

.preview-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.preview-video {
  max-width: 100%;
  max-height: 70vh;
}

.preview-audio {
  width: 100%;
  max-width: 500px;
}

.preview-other {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-md;
  color: $text-secondary;
}

// 图片预览容器
.image-preview-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-md;
  width: 100%;
  max-height: 80vh;
}

.image-preview-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 400px;
  overflow: hidden;
  background-color: #1a1a1a;
  border-radius: $border-radius-md;

  img {
    max-width: 100%;
    max-height: 70vh;
    object-fit: contain;
    transition: transform 0.1s ease;
    user-select: none;
  }
}

.preview-toolbar {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm $spacing-md;
  background-color: $surface-color;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
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