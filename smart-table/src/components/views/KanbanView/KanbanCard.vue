<script setup lang="ts">
import { computed } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import FieldComponentFactory from '@/components/fields/FieldComponentFactory.vue'

interface Props {
  record: RecordEntity
  fields: FieldEntity[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'edit'): void
  (e: 'delete'): void
}>()

const primaryField = computed(() => {
  return props.fields.find(f => f.isPrimary) || props.fields[0]
})

const primaryValue = computed(() => {
  if (!primaryField.value) return ''
  return props.record.values[primaryField.value.id]
})

function handleClick() {
  emit('edit')
}
</script>

<template>
  <div class="kanban-card" @click="handleClick">
    <div class="card-header">
      <span class="card-title">
        {{ primaryValue || '无标题' }}
      </span>
      <el-dropdown trigger="click" @click.stop>
        <el-button link size="small" class="card-menu-btn">
          <el-icon><MoreFilled /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="$emit('edit')">
              <el-icon><Edit /></el-icon>
              编辑
            </el-dropdown-item>
            <el-dropdown-item divided @click="$emit('delete')">
              <el-icon><Delete /></el-icon>
              删除
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    
    <div class="card-fields">
      <div
        v-for="field in fields.filter(f => !f.isPrimary)"
        :key="field.id"
        class="card-field"
      >
        <span class="field-label">{{ field.name }}</span>
        <div class="field-value">
          <FieldComponentFactory
            :model-value="record.values[field.id]"
            :field="field"
            :readonly="true"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.kanban-card {
  padding: $spacing-sm;
  margin-bottom: $spacing-sm;
  background-color: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: $primary-color;
    box-shadow: $shadow-sm;

    .card-menu-btn {
      opacity: 1;
    }
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: $spacing-sm;
}

.card-title {
  font-weight: 500;
  color: $text-primary;
  word-break: break-word;
}

.card-menu-btn {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.card-fields {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.card-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-label {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.field-value {
  font-size: $font-size-sm;
  color: $text-primary;
}
</style>
