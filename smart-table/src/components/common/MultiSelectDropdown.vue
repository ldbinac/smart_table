<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import type { FieldOption } from '@/types/fields'

interface Props {
  modelValue: string[]
  options: FieldOption[]
  placeholder?: string
  showSearch?: boolean
  showSelectAll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  placeholder: '请选择',
  showSearch: true,
  showSelectAll: true
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const isOpen = ref(false)
const searchQuery = ref('')
const triggerRef = ref<HTMLElement>()
const panelRef = ref<HTMLElement>()
const panelStyle = ref({
  position: 'fixed' as const,
  top: '0px',
  left: '0px',
  width: '200px',
  zIndex: 9999
})

// 本地值副本
const localValue = ref<string[]>([...props.modelValue])

// 同步外部值变化
watch(() => props.modelValue, (newVal) => {
  localValue.value = [...newVal]
}, { deep: true })

// 过滤后的选项
const filteredOptions = computed(() => {
  if (!searchQuery.value.trim()) return props.options
  const query = searchQuery.value.toLowerCase()
  return props.options.filter(opt => 
    opt.name.toLowerCase().includes(query)
  )
})

// 是否全选
const isAllSelected = computed(() => {
  return filteredOptions.value.length > 0 && 
    filteredOptions.value.every(opt => localValue.value.includes(opt.id))
})

// 是否部分选中
const isIndeterminate = computed(() => {
  const selectedCount = filteredOptions.value.filter(opt => 
    localValue.value.includes(opt.id)
  ).length
  return selectedCount > 0 && selectedCount < filteredOptions.value.length
})

// 已选选项
const selectedOptions = computed(() => {
  return props.options.filter(opt => localValue.value.includes(opt.id))
})

// 更新面板位置
const updatePanelPosition = async () => {
  if (!triggerRef.value || !isOpen.value) return
  
  await nextTick()
  
  const rect = triggerRef.value.getBoundingClientRect()
  const panelHeight = 320 // 最大高度
  const windowHeight = window.innerHeight
  const windowWidth = window.innerWidth
  
  // 计算面板宽度（与触发器相同或最小200px）
  const panelWidth = Math.max(rect.width, 200)
  
  // 判断下方是否有足够空间
  const spaceBelow = windowHeight - rect.bottom
  const spaceAbove = rect.top
  
  let top: number
  let left: number
  
  // 优先显示在下方，如果空间不足则显示在上方
  if (spaceBelow >= panelHeight || spaceBelow >= spaceAbove) {
    top = rect.bottom + 4
  } else {
    top = rect.top - panelHeight - 4
  }
  
  // 确保不超出视口左右边界
  left = rect.left
  if (left + panelWidth > windowWidth) {
    left = windowWidth - panelWidth - 8
  }
  if (left < 8) {
    left = 8
  }
  
  // 确保不超出视口底部
  if (top + panelHeight > windowHeight) {
    top = windowHeight - panelHeight - 8
  }
  // 确保不超出视口顶部
  if (top < 8) {
    top = 8
  }
  
  panelStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    width: `${panelWidth}px`,
    zIndex: 9999
  }
}

// 切换选项
const toggleOption = (optionId: string) => {
  const idx = localValue.value.indexOf(optionId)
  if (idx > -1) {
    localValue.value.splice(idx, 1)
  } else {
    localValue.value.push(optionId)
  }
  // 确保发送的是纯 JavaScript 数组
  const plainArray = JSON.parse(JSON.stringify([...localValue.value]))
  emit('update:modelValue', plainArray)
}

// 全选/取消全选
const toggleSelectAll = () => {
  if (isAllSelected.value) {
    // 取消全选（只取消过滤后的）
    const filteredIds = filteredOptions.value.map(opt => opt.id)
    localValue.value = localValue.value.filter(id => !filteredIds.includes(id))
  } else {
    // 全选
    const filteredIds = filteredOptions.value.map(opt => opt.id)
    const newSelection = [...new Set([...localValue.value, ...filteredIds])]
    localValue.value = newSelection
  }
  // 确保发送的是纯 JavaScript 数组
  const plainArray = JSON.parse(JSON.stringify([...localValue.value]))
  emit('update:modelValue', plainArray)
}

// 确认选择
const confirmSelection = () => {
  // 确保发送的是纯 JavaScript 数组，避免响应式对象导致的克隆错误
  const plainArray = JSON.parse(JSON.stringify([...localValue.value]))
  emit('update:modelValue', plainArray)
  emit('confirm')
  isOpen.value = false
}

// 取消选择
const cancelSelection = () => {
  localValue.value = [...props.modelValue]
  // 确保发送的是纯 JavaScript 数组
  const plainArray = JSON.parse(JSON.stringify([...localValue.value]))
  emit('update:modelValue', plainArray)
  emit('cancel')
  isOpen.value = false
}

// 点击外部关闭
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Node
  // 检查点击是否在下拉面板或触发器内
  if (panelRef.value?.contains(target) || triggerRef.value?.contains(target)) {
    return
  }
  if (isOpen.value) {
    cancelSelection()
  }
}

// 键盘事件处理
const handleKeydown = (event: KeyboardEvent) => {
  if (!isOpen.value) return
  
  if (event.key === 'Escape') {
    event.preventDefault()
    cancelSelection()
  } else if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    confirmSelection()
  }
}

// 处理窗口大小变化
const handleResize = () => {
  if (isOpen.value) {
    updatePanelPosition()
  }
}

// 处理滚动
const handleScroll = () => {
  if (isOpen.value) {
    updatePanelPosition()
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
  window.addEventListener('scroll', handleScroll, true)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('scroll', handleScroll, true)
})

// 打开下拉框
const open = async () => {
  isOpen.value = true
  searchQuery.value = ''
  await updatePanelPosition()
}

// 关闭下拉框
const close = () => {
  isOpen.value = false
}

// 切换下拉框
const toggle = async () => {
  if (isOpen.value) {
    close()
  } else {
    await open()
  }
}

defineExpose({
  open,
  close,
  toggle,
  isOpen
})
</script>

<template>
  <div class="multi-select-dropdown">
    <!-- 触发区域 -->
    <div 
      ref="triggerRef"
      class="dropdown-trigger" 
      :class="{ 'is-open': isOpen }"
      @click.stop="toggle">
      <div class="trigger-content">
        <template v-if="selectedOptions.length > 0">
          <span 
            v-for="opt in selectedOptions.slice(0, 3)" 
            :key="opt.id"
            class="selected-tag"
            :style="{ backgroundColor: opt.color + '20', color: opt.color, borderColor: opt.color + '40' }">
            {{ opt.name }}
          </span>
          <span v-if="selectedOptions.length > 3" class="more-tag">
            +{{ selectedOptions.length - 3 }}
          </span>
        </template>
        <span v-else class="placeholder">{{ placeholder }}</span>
      </div>
      <el-icon class="trigger-icon" :class="{ 'is-open': isOpen }">
        <ArrowDown />
      </el-icon>
    </div>

    <!-- 下拉面板 - 使用 Teleport 渲染到 body -->
    <Teleport to="body">
      <Transition name="dropdown">
        <div 
          v-show="isOpen" 
          ref="panelRef"
          class="dropdown-panel" 
          :style="panelStyle"
          @click.stop>
          <!-- 搜索框 -->
          <div v-if="showSearch" class="search-box">
            <el-icon class="search-icon"><Search /></el-icon>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索选项..."
              class="search-input"
              @keydown.stop
            />
            <el-icon v-if="searchQuery" class="clear-icon" @click="searchQuery = ''">
              <CircleClose />
            </el-icon>
          </div>

          <!-- 全选按钮 -->
          <div v-if="showSelectAll && filteredOptions.length > 0" class="select-all-bar">
            <label class="select-all-label" @click="toggleSelectAll">
              <input 
                type="checkbox" 
                :checked="isAllSelected"
                :indeterminate="isIndeterminate"
                @click.stop
                @change="toggleSelectAll"
              />
              <span>{{ isAllSelected ? '取消全选' : '全选' }}</span>
              <span class="option-count">({{ localValue.length }}/{{ options.length }})</span>
            </label>
          </div>

          <!-- 选项列表 -->
          <div class="options-list">
            <template v-if="filteredOptions.length > 0">
              <label
                v-for="opt in filteredOptions"
                :key="opt.id"
                class="option-item"
                :class="{ 'is-selected': localValue.includes(opt.id) }"
                @click.stop="toggleOption(opt.id)">
                <input
                  type="checkbox"
                  :checked="localValue.includes(opt.id)"
                  @click.stop
                  @change="toggleOption(opt.id)"
                />
                <span 
                  class="option-color-dot"
                  :style="{ backgroundColor: opt.color }">
                </span>
                <span class="option-name">{{ opt.name }}</span>
              </label>
            </template>
            <div v-else class="no-options">
              未找到匹配的选项
            </div>
          </div>

          <!-- 底部按钮 -->
          <div class="dropdown-footer">
            <button class="btn-cancel" @click="cancelSelection">取消</button>
            <button class="btn-confirm" @click="confirmSelection">
              确定 ({{ localValue.length }})
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.multi-select-dropdown {
  position: relative;
  width: 100%;
}

.dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  min-height: 28px;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  background: $surface-color;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: $primary-color;
  }

  &.is-open {
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.2);
  }
}

.trigger-content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.selected-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: $font-size-xs;
  font-weight: 500;
  border: 1px solid;
  white-space: nowrap;
}

.more-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: $font-size-xs;
  color: $text-secondary;
  background: $bg-color;
}

.placeholder {
  color: $text-disabled;
  font-size: $font-size-sm;
}

.trigger-icon {
  margin-left: 4px;
  color: $text-secondary;
  transition: transform 0.2s;
  flex-shrink: 0;

  &.is-open {
    transform: rotate(180deg);
  }
}

.dropdown-panel {
  background: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  max-height: 320px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-box {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid $border-color;
  gap: 8px;
  flex-shrink: 0;

  .search-icon {
    color: $text-secondary;
    font-size: 14px;
  }

  .search-input {
    flex: 1;
    border: none;
    outline: none;
    font-size: $font-size-sm;
    color: $text-primary;
    background: transparent;

    &::placeholder {
      color: $text-disabled;
    }
  }

  .clear-icon {
    color: $text-secondary;
    font-size: 14px;
    cursor: pointer;

    &:hover {
      color: $text-primary;
    }
  }
}

.select-all-bar {
  padding: 8px 12px;
  border-bottom: 1px solid $border-color;
  background: $bg-color;
  flex-shrink: 0;
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: $font-size-sm;
  color: $text-primary;
  user-select: none;

  input[type="checkbox"] {
    cursor: pointer;
  }

  .option-count {
    color: $text-secondary;
    font-size: $font-size-xs;
  }
}

.options-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
  min-height: 0;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.15s;
  user-select: none;

  &:hover {
    background-color: $bg-color;
  }

  &.is-selected {
    background-color: rgba($primary-color, 0.05);
  }

  input[type="checkbox"] {
    cursor: pointer;
    flex-shrink: 0;
  }
}

.option-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.option-name {
  flex: 1;
  font-size: $font-size-sm;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-options {
  padding: 20px;
  text-align: center;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.dropdown-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid $border-color;
  background: $bg-color;
  flex-shrink: 0;
}

.btn-cancel,
.btn-confirm {
  padding: 6px 16px;
  border-radius: $border-radius-sm;
  font-size: $font-size-sm;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: $surface-color;
  border: 1px solid $border-color;
  color: $text-primary;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
  }
}

.btn-confirm {
  background: $primary-color;
  border: 1px solid $primary-color;
  color: #fff;

  &:hover {
    background: color-mix(in srgb, $primary-color 90%, black);
  }
}

// 动画
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
