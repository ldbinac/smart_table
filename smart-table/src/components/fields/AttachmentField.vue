<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile } from "element-plus";
import type { FieldEntity } from "@/db/schema";
import type { CellValue } from "@/types";
import {
  UploadFilled,
  Document,
  Picture,
  Delete,
  Download,
} from "@element-plus/icons-vue";

interface AttachmentFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url?: string;
  thumbnail?: string;
}

interface Props {
  modelValue: CellValue;
  field: FieldEntity;
  readonly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

const files = ref<AttachmentFile[]>([]);
const uploading = ref(false);

watch(
  () => props.modelValue,
  (newVal) => {
    if (Array.isArray(newVal)) {
      files.value = newVal as AttachmentFile[];
    } else {
      files.value = [];
    }
  },
  { immediate: true },
);

const acceptTypes = computed(() => {
  const types = props.field.options?.acceptTypes as string[];
  return types ? types.join(",") : "*/*";
});

const maxSize = computed(() => {
  return (props.field.options?.maxSize as number) || 10 * 1024 * 1024;
});

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function getFileIcon(type: string): typeof Document {
  if (type.startsWith("image/")) return Picture;
  return Document;
}

async function handleUpload(uploadFile: UploadFile) {
  const file = uploadFile.raw;

  if (!file) {
    ElMessage.error("文件不存在");
    return;
  }

  if (file.size > maxSize.value) {
    ElMessage.error(`文件大小超过限制 (${formatFileSize(maxSize.value)})`);
    return;
  }

  uploading.value = true;

  try {
    const reader = new FileReader();

    const fileData = await new Promise<AttachmentFile>((resolve, reject) => {
      reader.onload = () => {
        const attachment: AttachmentFile = {
          id: `file-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          name: file.name,
          size: file.size,
          type: file.type,
          url: reader.result as string,
        };

        if (file.type.startsWith("image/")) {
          attachment.thumbnail = reader.result as string;
        }

        resolve(attachment);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    files.value.push(fileData);
    emit("update:modelValue", files.value);
    ElMessage.success("文件上传成功");
  } catch (error) {
    ElMessage.error("文件上传失败");
  } finally {
    uploading.value = false;
  }
}

function handleRemove(fileId: string) {
  files.value = files.value.filter((f) => f.id !== fileId);
  emit("update:modelValue", files.value);
}

function handleDownload(file: AttachmentFile) {
  if (file.url) {
    const link = document.createElement("a");
    link.href = file.url;
    link.download = file.name;
    link.click();
  }
}

function handlePreview(file: AttachmentFile) {
  if (file.type.startsWith("image/") && file.url) {
    ElMessageBox.alert(
      `<img src="${file.url}" style="max-width: 100%;">`,
      file.name,
      {
        dangerouslyUseHTMLString: true,
        showConfirmButton: false,
      },
    );
  }
}
</script>

<template>
  <div class="attachment-field">
    <div v-if="!readonly" class="upload-area">
      <el-upload
        :auto-upload="false"
        :show-file-list="false"
        :accept="acceptTypes"
        :on-change="handleUpload"
        drag
        multiple>
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">拖拽文件到此处或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">
            最大文件大小: {{ formatFileSize(maxSize) }}
          </div>
        </template>
      </el-upload>
    </div>

    <div v-if="files.length > 0" class="file-list">
      <div v-for="file in files" :key="file.id" class="file-item">
        <div class="file-preview" @click="handlePreview(file)">
          <img
            v-if="file.thumbnail"
            :src="file.thumbnail"
            class="file-thumbnail" />
          <el-icon v-else class="file-icon">
            <component :is="getFileIcon(file.type)" />
          </el-icon>
        </div>

        <div class="file-info">
          <span class="file-name" :title="file.name">{{ file.name }}</span>
          <span class="file-size">{{ formatFileSize(file.size) }}</span>
        </div>

        <div class="file-actions">
          <el-button link size="small" @click="handleDownload(file)">
            <el-icon><Download /></el-icon>
          </el-button>
          <el-button
            v-if="!readonly"
            link
            size="small"
            type="danger"
            @click="handleRemove(file.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <div v-else-if="readonly" class="empty-state">无附件</div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.attachment-field {
  width: 100%;
}

.upload-area {
  margin-bottom: $spacing-sm;

  :deep(.el-upload-dragger) {
    padding: $spacing-lg;
    border-radius: $border-radius-md;
  }

  .upload-icon {
    font-size: 32px;
    color: $text-disabled;
    margin-bottom: $spacing-sm;
  }

  .upload-text {
    font-size: $font-size-sm;
    color: $text-secondary;

    em {
      color: $primary-color;
      font-style: normal;
    }
  }

  .upload-tip {
    font-size: $font-size-xs;
    color: $text-disabled;
    margin-top: $spacing-xs;
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

  &:hover {
    border-color: $primary-color;
  }
}

.file-preview {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: $surface-color;
  border-radius: $border-radius-sm;
  cursor: pointer;
  overflow: hidden;
}

.file-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-icon {
  font-size: 20px;
  color: $text-secondary;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.file-name {
  font-size: $font-size-sm;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: $font-size-xs;
  color: $text-disabled;
}

.file-actions {
  display: flex;
  gap: $spacing-xs;
}

.empty-state {
  font-size: $font-size-sm;
  color: $text-disabled;
}
</style>
