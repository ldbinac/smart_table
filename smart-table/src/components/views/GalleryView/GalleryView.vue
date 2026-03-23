<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import { FieldType } from '@/types'

interface Props {
  fields: FieldEntity[]
  records: RecordEntity[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'updateRecord', recordId: string, values: Record<string, unknown>): void
  (e: 'deleteRecord', recordId: string): void
}>()

const imageFieldId = ref<string>('')
const titleFieldId = ref<string>('')
const previewVisible = ref(false)
const previewImages = ref<Array<{ url: string; name: string }>>([])
const previewIndex = ref(0)

const attachmentFields = computed(() => {
  return props.fields.filter(f => f.type === FieldType.ATTACHMENT)
})

const titleFields = computed(() => {
  return props.fields.filter(f => 
    f.type === FieldType.TEXT || 
    f.type === FieldType.NUMBER ||
    f.type === FieldType.SINGLE_SELECT
  )
})

const titleField = computed(() => {
  if (titleFieldId.value) {
    return props.fields.find(f => f.id === titleFieldId.value)
  }
  return props.fields.find(f => f.isPrimary) || props.fields[0]
})

interface GalleryCard {
  id: string
  title: string
  images: Array<{ url: string; name: string }>
  record: RecordEntity
}

const cards = computed<GalleryCard[]>(() => {
  if (!imageFieldId.value) {
    return props.records.map(record => ({
      id: record.id,
      title: String(titleField.value ? record.values[titleField.value!.id] || '无标题' : '无标题'),
      images: [],
      record
    }))
  }
  
  return props.records
    .filter(record => {
      const images = record.values[imageFieldId.value]
      return images && Array.isArray(images) && images.length > 0
    })
    .map(record => {
      const images = record.values[imageFieldId.value] as Array<{ url?: string; name?: string; thumbnail?: string }>
      const title = String(titleField.value ? record.values[titleField.value!.id] || '无标题' : '无标题')
      
      return {
        id: record.id,
        title,
        images: images.map(img => ({
          url: img.url || img.thumbnail || '',
          name: img.name || '未命名'
        })).filter(img => img.url),
        record
      }
    })
    .filter(card => card.images.length > 0)
})

function handleCardClick(card: GalleryCard) {
  if (card.images.length > 0) {
    previewImages.value = card.images
    previewIndex.value = 0
    previewVisible.value = true
  }
}

function handleDelete(card: GalleryCard) {
  emit('deleteRecord', card.id)
}

onMounted(() => {
  if (attachmentFields.value.length > 0) {
    imageFieldId.value = attachmentFields.value[0].id
  }
})
</script>

<template>
  <div class="gallery-view">
    <div class="gallery-toolbar">
      <el-select v-model="imageFieldId" placeholder="选择图片字段" class="field-select">
        <el-option
          v-for="field in attachmentFields"
          :key="field.id"
          :label="field.name"
          :value="field.id"
        />
      </el-select>
      <el-select v-model="titleFieldId" placeholder="选择标题字段" class="field-select">
        <el-option
          v-for="field in titleFields"
          :key="field.id"
          :label="field.name"
          :value="field.id"
        />
      </el-select>
    </div>
    
    <div class="gallery-content">
      <div class="gallery-grid">
        <div
          v-for="card in cards"
          :key="card.id"
          class="gallery-card"
        >
          <div class="card-image" @click="handleCardClick(card)">
            <img
              v-if="card.images[0]?.url"
              :src="card.images[0].url"
              :alt="card.images[0].name"
            />
            <div v-else class="no-image">
              <el-icon><Picture /></el-icon>
            </div>
            
            <div v-if="card.images.length > 1" class="image-count">
              +{{ card.images.length - 1 }}
            </div>
            
            <div class="card-overlay">
              <el-button
                link
                type="danger"
                @click.stop="handleDelete(card)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          
          <div class="card-info">
            <span class="card-title">{{ card.title }}</span>
          </div>
        </div>
      </div>
      
      <div v-if="cards.length === 0" class="empty-gallery">
        <el-icon class="empty-icon"><Picture /></el-icon>
        <p>暂无图片数据</p>
      </div>
    </div>
    
    <el-dialog
      v-model="previewVisible"
      title="图片预览"
      width="80%"
      destroy-on-close
    >
      <div class="preview-container">
        <el-carousel
          :initial-index="previewIndex"
          indicator-position="outside"
          height="60vh"
        >
          <el-carousel-item
            v-for="(image, index) in previewImages"
            :key="index"
          >
            <div class="preview-image">
              <img :src="image.url" :alt="image.name" />
            </div>
          </el-carousel-item>
        </el-carousel>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.gallery-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-color;
}

.gallery-toolbar {
  display: flex;
  gap: $spacing-sm;
  padding: $spacing-md;
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  
  .field-select {
    width: 150px;
  }
}

.gallery-content {
  flex: 1;
  padding: $spacing-md;
  overflow-y: auto;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: $spacing-md;
}

.gallery-card {
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  overflow: hidden;
  border: 1px solid $border-color;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: $primary-color;
    box-shadow: $shadow-md;
    
    .card-overlay {
      opacity: 1;
    }
  }
}

.card-image {
  position: relative;
  width: 100%;
  height: 150px;
  background-color: $bg-color;
  cursor: pointer;
  overflow: hidden;
  
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.no-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
  
  .el-icon {
    font-size: 48px;
  }
}

.image-count {
  position: absolute;
  top: $spacing-sm;
  right: $spacing-sm;
  padding: 2px 8px;
  background-color: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: $font-size-xs;
  border-radius: $border-radius-sm;
}

.card-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.card-info {
  padding: $spacing-sm;
}

.card-title {
  font-size: $font-size-sm;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-gallery {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-xl * 2;
  color: $text-secondary;
  
  .empty-icon {
    font-size: 64px;
    margin-bottom: $spacing-md;
    color: $text-disabled;
  }
}

.preview-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  
  img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }
}
</style>
