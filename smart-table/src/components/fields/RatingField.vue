<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FieldEntity } from '@/db/schema'
import type { CellValue } from '@/types'
import { Star, StarFilled } from '@element-plus/icons-vue'

interface Props {
  modelValue: CellValue
  field: FieldEntity
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: CellValue): void
}>()

const currentValue = ref(0)
const hoverValue = ref(0)

const maxRating = computed(() => {
  return (props.field.options?.maxRating as number) || 5
})

const allowHalf = computed(() => {
  return props.field.options?.allowHalf !== false
})

watch(() => props.modelValue, (newVal) => {
  currentValue.value = Number(newVal) || 0
}, { immediate: true })

function getStarType(index: number): 'full' | 'half' | 'empty' {
  const value = hoverValue.value || currentValue.value
  if (value >= index) return 'full'
  if (allowHalf.value && value >= index - 0.5) return 'half'
  return 'empty'
}

function handleClick(index: number, isHalf: boolean = false) {
  if (props.readonly) return
  
  let newValue = isHalf ? index - 0.5 : index
  
  if (newValue === currentValue.value) {
    newValue = 0
  }
  
  currentValue.value = newValue
  emit('update:modelValue', newValue)
}

function handleMouseMove(index: number, event: MouseEvent) {
  if (props.readonly) return
  
  const rect = (event.target as HTMLElement).getBoundingClientRect()
  const isHalf = allowHalf.value && event.clientX - rect.left < rect.width / 2
  
  hoverValue.value = isHalf ? index - 0.5 : index
}

function handleMouseLeave() {
  if (props.readonly) return
  hoverValue.value = 0
}
</script>

<template>
  <div class="rating-field" :class="{ readonly }">
    <div
      v-for="i in maxRating"
      :key="i"
      class="star-item"
      @mousemove="handleMouseMove(i, $event)"
      @mouseleave="handleMouseLeave"
      @click="handleClick(i, getStarType(i) === 'half')"
    >
      <el-icon class="star-icon" :class="getStarType(i)">
        <StarFilled v-if="getStarType(i) === 'full'" />
        <Star v-else />
      </el-icon>
    </div>
    <span v-if="currentValue > 0" class="rating-value">
      {{ currentValue.toFixed(1) }}
    </span>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.rating-field {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  
  &:not(.readonly) {
    .star-item {
      cursor: pointer;
    }
  }
}

.star-item {
  display: flex;
  align-items: center;
  justify-content: center;
}

.star-icon {
  font-size: 20px;
  transition: all 0.2s ease;
  
  &.full {
    color: #FBBF24;
  }
  
  &.half {
    color: #FBBF24;
    opacity: 0.5;
  }
  
  &.empty {
    color: $border-color;
  }
}

.rating-value {
  margin-left: $spacing-xs;
  font-size: $font-size-sm;
  color: $text-secondary;
}
</style>
