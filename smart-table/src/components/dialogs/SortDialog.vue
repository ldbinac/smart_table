<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElDialog, ElButton, ElSelect, ElOption, ElRadioGroup, ElRadioButton, ElTag } from 'element-plus'
import { SortDirection, type SortConfig } from '@/types/filters'
import type { FieldEntity } from '@/db/schema'

const props = defineProps<{
  visible: boolean
  fields: FieldEntity[]
  initialSorts?: SortConfig[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'apply': [sorts: SortConfig[]]
  'clear': []
}>()

const sorts = ref<SortConfig[]>([])

function addSort() {
  const availableField = props.fields.find(f => !sorts.value.some(s => s.fieldId === f.id))
  if (!availableField) return
  
  sorts.value.push({
    fieldId: availableField.id,
    direction: SortDirection.ASC
  })
}

function removeSort(index: number) {
  sorts.value.splice(index, 1)
}

function moveSort(index: number, direction: 'up' | 'down') {
  if (direction === 'up' && index > 0) {
    const temp = sorts.value[index]
    sorts.value[index] = sorts.value[index - 1]
    sorts.value[index - 1] = temp
  } else if (direction === 'down' && index < sorts.value.length - 1) {
    const temp = sorts.value[index]
    sorts.value[index] = sorts.value[index + 1]
    sorts.value[index + 1] = temp
  }
}

function getFieldById(fieldId: string) {
  return props.fields.find(f => f.id === fieldId)
}

function getAvailableFields(currentIndex: number) {
  const usedFieldIds = sorts.value
    .filter((_, index) => index !== currentIndex)
    .map(s => s.fieldId)
  return props.fields.filter(f => !usedFieldIds.includes(f.id))
}

function applySorts() {
  emit('apply', [...sorts.value])
  emit('update:visible', false)
}

function clearSorts() {
  sorts.value = []
  emit('clear')
  emit('update:visible', false)
}

watch(() => props.visible, (visible) => {
  if (visible) {
    sorts.value = props.initialSorts ? [...props.initialSorts] : []
  }
})
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="排序"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="sort-dialog">
      <!-- 排序条件列表 -->
      <div class="sorts-list">
        <div
          v-for="(sort, index) in sorts"
          :key="index"
          class="sort-row"
        >
          <span class="sort-priority">{{ index + 1 }}</span>
          
          <!-- 字段选择 -->
          <ElSelect
            v-model="sort.fieldId"
            placeholder="选择字段"
            style="width: 180px"
          >
            <ElOption
              v-for="field in getAvailableFields(index)"
              :key="field.id"
              :label="field.name"
              :value="field.id"
            />
            <ElOption
              v-if="getFieldById(sort.fieldId)"
              :key="sort.fieldId"
              :label="getFieldById(sort.fieldId)!.name"
              :value="sort.fieldId"
            />
          </ElSelect>

          <!-- 排序方向 -->
          <ElRadioGroup v-model="sort.direction" size="small">
            <ElRadioButton :label="SortDirection.ASC">
              升序 ↑
            </ElRadioButton>
            <ElRadioButton :label="SortDirection.DESC">
              降序 ↓
            </ElRadioButton>
          </ElRadioGroup>

          <!-- 操作按钮 -->
          <div class="sort-actions">
            <ElButton
              link
              :disabled="index === 0"
              @click="moveSort(index, 'up')"
            >
              ↑
            </ElButton>
            <ElButton
              link
              :disabled="index === sorts.length - 1"
              @click="moveSort(index, 'down')"
            >
              ↓
            </ElButton>
            <ElButton
              link
              type="danger"
              @click="removeSort(index)"
            >
              删除
            </ElButton>
          </div>
        </div>
      </div>

      <!-- 添加排序按钮 -->
      <ElButton
        v-if="sorts.length < fields.length"
        link
        type="primary"
        class="add-sort-btn"
        @click="addSort"
      >
        + 添加排序条件
      </ElButton>

      <!-- 已选条件预览 -->
      <div v-if="sorts.length > 0" class="sort-preview">
        <div class="preview-label">当前排序：</div>
        <div class="preview-tags">
          <ElTag
            v-for="(sort, index) in sorts"
            :key="index"
            size="small"
            closable
            @close="removeSort(index)"
          >
            {{ getFieldById(sort.fieldId)?.name }}
            {{ sort.direction === SortDirection.ASC ? '升序' : '降序' }}
          </ElTag>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="sorts.length === 0" class="empty-sort">
        <p>暂无排序条件</p>
        <p class="hint">点击上方按钮添加排序条件</p>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <ElButton @click="$emit('update:visible', false)">取消</ElButton>
        <ElButton link type="danger" @click="clearSorts">清除排序</ElButton>
        <ElButton type="primary" @click="applySorts">应用排序</ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.sort-dialog {
  .sorts-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
  }

  .sort-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    background-color: $bg-color;
    border-radius: $border-radius-md;

    .sort-priority {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: $primary-color;
      color: white;
      border-radius: 50%;
      font-size: 12px;
      font-weight: 500;
    }

    .sort-actions {
      display: flex;
      gap: 4px;
      margin-left: auto;
    }
  }

  .add-sort-btn {
    margin-bottom: 16px;
  }

  .sort-preview {
    padding-top: 12px;
    border-top: 1px solid $border-color;

    .preview-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-bottom: 8px;
    }

    .preview-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
  }

  .empty-sort {
    text-align: center;
    padding: 32px;
    color: $text-secondary;

    p {
      margin: 0;
    }

    .hint {
      font-size: $font-size-sm;
      margin-top: 8px;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
