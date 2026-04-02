<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";
import { FormulaEngine } from "@/utils/formula/engine";

interface Props {
  fields: FieldEntity[];
  records: RecordEntity[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "updateRecord", recordId: string, values: Record<string, unknown>): void;
  (e: "deleteRecord", recordId: string): void;
  (e: "editRecord", recordId: string): void;
}>();

const imageFieldId = ref<string>("");
const titleFieldId = ref<string>("");
const previewVisible = ref(false);
const previewImages = ref<Array<{ url: string; name: string }>>([]);
const previewIndex = ref(0);
const imageLoadingMap = ref<Map<string, boolean>>(new Map());

const attachmentFields = computed(() => {
  return props.fields.filter((f) => f.type === FieldType.ATTACHMENT);
});

const titleFields = computed(() => {
  return props.fields.filter(
    (f) =>
      f.type === FieldType.TEXT ||
      f.type === FieldType.NUMBER ||
      f.type === FieldType.SINGLE_SELECT ||
      f.type === FieldType.FORMULA,
  );
});

const titleField = computed(() => {
  if (titleFieldId.value) {
    return props.fields.find((f) => f.id === titleFieldId.value);
  }
  return props.fields.find((f) => f.isPrimary) || props.fields[0];
});

interface GalleryCard {
  id: string;
  title: string;
  images: Array<{ url: string; name: string }>;
  record: RecordEntity;
}

// 获取记录标题（支持公式字段）
const getRecordTitle = (record: RecordEntity): string => {
  const field = titleField.value;
  if (!field) return "无标题";

  // 如果是公式字段，实时计算
  if (field.type === FieldType.FORMULA) {
    const formula = field.options?.formula as string;
    if (formula && props.fields.length > 0) {
      try {
        const engine = new FormulaEngine(props.fields);
        const result = engine.calculate(record, formula);
        if (result !== "#ERROR") {
          return String(result);
        }
      } catch (error) {
        console.error("Gallery formula calculation error:", error);
      }
    }
    return "计算错误";
  }

  // 单选字段：返回选项名称而不是ID
  if (field.type === FieldType.SINGLE_SELECT && field.options?.options) {
    const value = record.values[field.id];
    const options = field.options.options;
    const selectedOption = options.find((opt: any) => opt.id === value);
    return selectedOption?.name || String(value || "无标题");
  }

  // 普通字段直接返回值
  return String(record.values[field.id] || "无标题");
};

const cards = computed<GalleryCard[]>(() => {
  if (!imageFieldId.value) {
    return props.records.map((record) => ({
      id: record.id,
      title: getRecordTitle(record),
      images: [],
      record,
    }));
  }

  return props.records
    .filter((record) => {
      const images = record.values[imageFieldId.value];
      return images && Array.isArray(images) && images.length > 0;
    })
    .map((record) => {
      const images = record.values[imageFieldId.value] as Array<{
        url?: string;
        name?: string;
        thumbnail?: string;
      }>;
      const title = getRecordTitle(record);

      return {
        id: record.id,
        title,
        images: images
          .map((img) => ({
            url: img.url || img.thumbnail || "",
            name: img.name || "未命名",
          }))
          .filter((img) => img.url),
        record,
      };
    })
    .filter((card) => card.images.length > 0);
});

function handleImageLoad(cardId: string) {
  imageLoadingMap.value.set(cardId, false);
}

function isImageLoading(cardId: string): boolean {
  return imageLoadingMap.value.get(cardId) ?? true;
}

function handleImageClick(card: GalleryCard, event: MouseEvent) {
  const target = event.target as HTMLElement;
  const actionsArea = target.closest(".card-actions");
  if (actionsArea) {
    return;
  }

  if (card.images.length > 0) {
    previewImages.value = card.images;
    previewIndex.value = 0;
    previewVisible.value = true;
  }
}

function handleCardClick(card: GalleryCard, event: MouseEvent) {
  const target = event.target as HTMLElement;
  const actionsArea = target.closest(".card-actions");
  if (actionsArea) {
    return;
  }

  const imageArea = target.closest(".card-image-wrapper");
  if (imageArea && card.images.length > 0) {
    previewImages.value = card.images;
    previewIndex.value = 0;
    previewVisible.value = true;
  } else {
    emit("editRecord", card.id);
  }
}

function handleEdit(card: GalleryCard) {
  emit("editRecord", card.id);
}

function handleDelete(card: GalleryCard) {
  emit("deleteRecord", card.id);
}

onMounted(() => {
  if (attachmentFields.value.length > 0) {
    imageFieldId.value = attachmentFields.value[0].id;
  }
});
</script>

<template>
  <div class="gallery-view">
    <!-- 工具栏 -->
    <div class="gallery-toolbar">
      <div class="toolbar-left">
        <div class="toolbar-icon">
          <el-icon><Picture /></el-icon>
        </div>
        <span class="toolbar-title">画册视图</span>
        <span class="toolbar-count">{{ cards.length }} 个项目</span>
      </div>
      <div class="toolbar-right">
        <el-select
          v-model="imageFieldId"
          placeholder="选择图片字段"
          class="field-select">
          <template #prefix>
            <el-icon><Picture /></el-icon>
          </template>
          <el-option
            v-for="field in attachmentFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
        <el-select
          v-model="titleFieldId"
          placeholder="选择标题字段"
          class="field-select">
          <template #prefix>
            <el-icon><EditPen /></el-icon>
          </template>
          <el-option
            v-for="field in titleFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="gallery-content">
      <!-- 网格布局 -->
      <div v-if="cards.length > 0" class="gallery-grid">
        <div
          v-for="card in cards"
          :key="card.id"
          class="gallery-card"
          @click="handleCardClick(card, $event)">
          <!-- 图片区域 -->
          <div
            class="card-image-wrapper"
            @click.stop="handleImageClick(card, $event)">
            <!-- 骨架屏 -->
            <div v-if="isImageLoading(card.id)" class="image-skeleton">
              <el-skeleton animated>
                <template #template>
                  <el-skeleton-item
                    variant="image"
                    style="width: 100%; height: 100%" />
                </template>
              </el-skeleton>
            </div>

            <!-- 实际图片 -->
            <img
              v-if="card.images[0]?.url"
              :src="card.images[0].url"
              :alt="card.images[0].name"
              class="card-image"
              @load="handleImageLoad(card.id)"
              @error="handleImageLoad(card.id)" />

            <!-- 无图片占位 -->
            <div v-else class="no-image">
              <el-icon><Picture /></el-icon>
            </div>

            <!-- 图片数量标记 -->
            <div v-if="card.images.length > 1" class="image-count">
              <el-icon><Picture /></el-icon>
              <span>+{{ card.images.length - 1 }}</span>
            </div>

            <!-- 悬停操作按钮 -->
            <div class="card-overlay">
              <div class="card-actions" @click.stop>
                <el-button
                  circle
                  class="action-btn edit-btn"
                  @click="handleEdit(card)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button
                  circle
                  class="action-btn delete-btn"
                  @click="handleDelete(card)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>

          <!-- 卡片信息 -->
          <div class="card-info">
            <div class="card-title-wrapper">
              <el-icon class="title-icon"><Document /></el-icon>
              <span class="card-title" :title="card.title">{{
                card.title
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-gallery">
        <div class="empty-illustration">
          <div class="empty-icon-wrapper">
            <el-icon><Picture /></el-icon>
          </div>
          <div class="empty-decoration">
            <div class="decoration-dot dot-1"></div>
            <div class="decoration-dot dot-2"></div>
            <div class="decoration-dot dot-3"></div>
          </div>
        </div>
        <h3 class="empty-title">暂无图片数据</h3>
        <p class="empty-subtitle">
          <template v-if="!imageFieldId">
            请先选择一个图片字段来展示画册
          </template>
          <template v-else>
            当前选择的字段没有图片数据，请添加一些图片
          </template>
        </p>
        <el-button
          v-if="!imageFieldId && attachmentFields.length > 0"
          type="primary"
          class="empty-action"
          @click="imageFieldId = attachmentFields[0].id">
          <el-icon><Check /></el-icon>
          选择 {{ attachmentFields[0].name }}
        </el-button>
      </div>
    </div>

    <!-- 图片预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      title="图片预览"
      width="60%"
      destroy-on-close
      class="preview-dialog">
      <div class="preview-container">
        <el-carousel
          :initial-index="previewIndex"
          indicator-position="outside"
          height="60vh"
          arrow="always">
          <el-carousel-item
            v-for="(image, index) in previewImages"
            :key="index">
            <div class="preview-image-wrapper">
              <img :src="image.url" :alt="image.name" />
              <span class="preview-image-name">{{ image.name }}</span>
            </div>
          </el-carousel-item>
        </el-carousel>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.gallery-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: linear-gradient(180deg, $bg-color 0%, $gray-50 100%);
}

// 工具栏
.gallery-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  background: $surface-color;
  border-bottom: 1px solid $gray-100;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.toolbar-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(
    135deg,
    $primary-light 0%,
    rgba($primary-color, 0.1) 100%
  );
  border-radius: $border-radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;

  .el-icon {
    font-size: 18px;
    color: $primary-color;
  }
}

.toolbar-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
}

.toolbar-count {
  font-size: $font-size-sm;
  color: $text-secondary;
  padding: $spacing-xs $spacing-sm;
  background: $gray-50;
  border-radius: $border-radius-full;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.field-select {
  width: 160px;

  :deep(.el-select__wrapper) {
    border-radius: $border-radius-lg;
    border: 1px solid $gray-200;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    transition: all 0.2s ease;

    &:hover {
      border-color: $primary-hover;
    }

    &.is-focused {
      border-color: $primary-color;
      box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
    }
  }

  :deep(.el-select__prefix) {
    color: $text-secondary;
    margin-right: $spacing-xs;
  }
}

// 内容区域
.gallery-content {
  flex: 1;
  padding: $spacing-lg;
  overflow-y: auto;
}

// 响应式网格布局
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: $spacing-lg;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }

  @media (max-width: 768px) {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: $spacing-md;
  }

  @media (max-width: 480px) {
    grid-template-columns: repeat(2, 1fr);
    gap: $spacing-sm;
  }
}

// 画册卡片
.gallery-card {
  background: $surface-color;
  border-radius: $border-radius-xl;
  overflow: hidden;
  border: 1px solid $gray-100;
  transition: all 0.3s $ease-out-cubic;
  cursor: pointer;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.04),
    0 4px 8px rgba(0, 0, 0, 0.02);

  &:hover {
    transform: translateY(-4px);
    box-shadow:
      0 12px 24px -8px rgba(0, 0, 0, 0.12),
      0 8px 16px -4px rgba(0, 0, 0, 0.08);
    border-color: rgba($primary-color, 0.2);

    .card-overlay {
      opacity: 1;
    }

    .card-image {
      transform: scale(1.05);
    }
  }
}

// 图片包装器
.card-image-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  background: linear-gradient(135deg, $gray-50 0%, $gray-100 100%);
  overflow: hidden;
  border-radius: $border-radius-xl $border-radius-xl 0 0;
}

// 骨架屏
.image-skeleton {
  position: absolute;
  inset: 0;
  padding: $spacing-md;
  background: $gray-50;

  :deep(.el-skeleton) {
    height: 100%;
  }

  :deep(.el-skeleton__item) {
    border-radius: $border-radius-lg;
  }
}

// 实际图片
.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s $ease-out-cubic;
}

// 无图片占位
.no-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, $gray-50 0%, $gray-100 100%);

  .el-icon {
    font-size: 48px;
    color: $gray-300;
  }
}

// 图片数量标记
.image-count {
  position: absolute;
  top: $spacing-sm;
  right: $spacing-sm;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  color: white;
  font-size: $font-size-xs;
  font-weight: 500;
  border-radius: $border-radius-full;
  transition: all 0.2s ease;

  .el-icon {
    font-size: 12px;
  }
}

// 悬停遮罩层
.card-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    transparent 40%,
    rgba(0, 0, 0, 0.4) 100%
  );
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: $spacing-md;
  opacity: 0;
  transition: opacity 0.3s ease;
}

// 操作按钮
.card-actions {
  display: flex;
  gap: $spacing-sm;
  transform: translateY(8px);
  transition: transform 0.3s $ease-out-cubic;

  .gallery-card:hover & {
    transform: translateY(0);
  }
}

.action-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba($surface-color, 0.95);
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.2s ease;

  &:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  }

  .el-icon {
    font-size: 16px;
  }

  &.edit-btn {
    color: $primary-color;

    &:hover {
      background: $primary-color;
      color: $surface-color;
    }
  }

  &.delete-btn {
    color: $error-color;

    &:hover {
      background: $error-color;
      color: $surface-color;
    }
  }
}

// 卡片信息
.card-info {
  padding: $spacing-md;
  background: $surface-color;
}

.card-title-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.title-icon {
  font-size: 14px;
  color: $text-disabled;
  flex-shrink: 0;
}

.card-title {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

// 空状态
.empty-gallery {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-4xl $spacing-xl;
  min-height: 400px;
}

.empty-illustration {
  position: relative;
  margin-bottom: $spacing-xl;
}

.empty-icon-wrapper {
  width: 140px;
  height: 140px;
  background: linear-gradient(135deg, $gray-50 0%, $gray-100 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    inset 0 2px 8px rgba(0, 0, 0, 0.05),
    0 4px 20px rgba(0, 0, 0, 0.05);

  .el-icon {
    font-size: 64px;
    color: $gray-300;
  }
}

.empty-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.decoration-dot {
  position: absolute;
  border-radius: 50%;
  background: $primary-light;

  &.dot-1 {
    width: 16px;
    height: 16px;
    top: 10px;
    right: 10px;
    animation: float 3s ease-in-out infinite;
  }

  &.dot-2 {
    width: 10px;
    height: 10px;
    bottom: 20px;
    left: 5px;
    animation: float 3s ease-in-out infinite 0.5s;
  }

  &.dot-3 {
    width: 8px;
    height: 8px;
    top: 50%;
    right: -10px;
    animation: float 3s ease-in-out infinite 1s;
  }
}

.empty-title {
  font-size: $font-size-xl;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-sm;
}

.empty-subtitle {
  font-size: $font-size-base;
  color: $text-secondary;
  margin: 0 0 $spacing-xl;
  text-align: center;
  max-width: 320px;
  line-height: 1.6;
}

.empty-action {
  height: 44px;
  padding: 0 $spacing-xl;
  border-radius: $border-radius-lg;
  font-weight: 600;
  background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%);
  border: none;
  box-shadow: 0 4px 12px rgba($primary-color, 0.35);
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 6px 20px rgba($primary-color, 0.45);
    transform: translateY(-1px);
  }

  .el-icon {
    margin-right: 6px;
  }
}

// 预览对话框
.preview-dialog {
  :deep(.el-dialog__header) {
    padding: $spacing-lg;
    border-bottom: 1px solid $gray-100;
    margin-right: 0;

    .el-dialog__title {
      font-weight: 600;
      color: $text-primary;
    }
  }

  :deep(.el-dialog__body) {
    padding: $spacing-sm;
  }
}

.preview-container {
  display: flex;
  align-items: center;
  justify-content: center;

  :deep(.el-carousel__container) {
    width: 60vw;
  }
}

.preview-image-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-md;

  img {
    max-width: 90vw;
    max-height: calc(100vh - 40px);
    object-fit: contain;
    border-radius: $border-radius-lg;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }
}

.preview-image-name {
  font-size: $font-size-sm;
  color: $text-secondary;
  padding: $spacing-xs $spacing-md;
  background: $gray-50;
  border-radius: $border-radius-full;
}

// 动画
@keyframes float {
  0%,
  100% {
    transform: translateY(0);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

// 响应式适配
@media (max-width: 768px) {
  .gallery-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: $spacing-sm;
    padding: $spacing-sm;
  }

  .toolbar-left {
    justify-content: center;
  }

  .toolbar-right {
    justify-content: center;
  }

  .field-select {
    flex: 1;
  }

  .gallery-content {
    padding: $spacing-md;
  }

  .empty-icon-wrapper {
    width: 100px;
    height: 100px;

    .el-icon {
      font-size: 48px;
    }
  }

  .empty-title {
    font-size: $font-size-lg;
  }
}
</style>
