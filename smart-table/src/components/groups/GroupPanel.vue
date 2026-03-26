<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { FieldEntity } from '../../db/schema'
import type { GroupNode, GroupConfig } from '../../utils/group'
import type { FieldTypeValue } from '../../types'
import { FieldType } from '../../types'
import {
  groupRecords,
  flattenGroupTree,
  toggleGroupExpansion,
  expandAllGroups,
  collapseAllGroups
} from '../../utils/group'
import Sortable from 'sortablejs'
import { ElMessage } from 'element-plus'

interface Props {
  fields: FieldEntity[]
  records: Record<string, unknown>[]
  groupBy?: string[]
  showAggregations?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  groupBy: () => [],
  showAggregations: false
})

const emit = defineEmits<{
  (e: 'update:groupBy', value: string[]): void
  (e: 'groupClick', node: GroupNode): void
}>()

const localGroupBy = ref<string[]>([...props.groupBy])
const groupNodes = ref<GroupNode[]>([])
const allExpanded = ref(true)
const fieldsListRef = ref<HTMLElement | null>(null)
let sortableInstance: Sortable | null = null

// 最大分组层级数
const MAX_GROUP_LEVELS = 3

watch(() => props.groupBy, (newVal) => {
  localGroupBy.value = [...newVal]
}, { deep: true })

watch(localGroupBy, (newVal) => {
  emit('update:groupBy', newVal)
}, { deep: true })

// 监听字段列表变化，初始化拖拽排序
watch(() => localGroupBy.value.length, () => {
  nextTick(() => {
    initSortable()
  })
}, { immediate: true })

function initSortable() {
  if (sortableInstance) {
    sortableInstance.destroy()
  }

  if (fieldsListRef.value && localGroupBy.value.length > 1) {
    sortableInstance = new Sortable(fieldsListRef.value, {
      animation: 150,
      handle: '.drag-handle',
      onEnd: handleDragEnd
    })
  }
}

function handleDragEnd(evt: Sortable.SortableEvent) {
  if (evt.oldIndex === evt.newIndex) return

  const newGroupBy = [...localGroupBy.value]
  const [movedItem] = newGroupBy.splice(evt.oldIndex!, 1)
  newGroupBy.splice(evt.newIndex!, 0, movedItem)
  
  localGroupBy.value = newGroupBy
  updateGroups()
}

const groupableFieldTypes: FieldTypeValue[] = [
  FieldType.SINGLE_SELECT,
  FieldType.MULTI_SELECT,
  FieldType.CHECKBOX,
  FieldType.DATE,
  FieldType.CREATED_TIME,
  FieldType.UPDATED_TIME,
  FieldType.MEMBER,
  FieldType.TEXT,
  FieldType.NUMBER
]

const availableFields = computed(() => {
  return props.fields.filter(f => 
    groupableFieldTypes.includes(f.type as FieldTypeValue)
  )
})

const selectedGroupFields = computed(() => {
  return localGroupBy.value.map(id => props.fields.find(f => f.id === id)).filter(Boolean) as FieldEntity[]
})

const flattenedGroups = computed(() => {
  return flattenGroupTree(groupNodes.value)
})

const totalRecords = computed(() => {
  return props.records.length
})

const visibleRecords = computed(() => {
  let count = 0
  const countVisible = (nodes: GroupNode[]) => {
    for (const node of nodes) {
      if (node.isExpanded && node.children) {
        countVisible(node.children)
      } else {
        count += node.records.length
      }
    }
  }
  countVisible(groupNodes.value)
  return count
})

// 是否已达到最大分组层级
const isMaxLevelReached = computed(() => {
  return localGroupBy.value.length >= MAX_GROUP_LEVELS
})

// 是否还可以添加分组字段
const canAddMoreGroups = computed(() => {
  return availableFields.value.length > localGroupBy.value.length && !isMaxLevelReached.value
})

function addGroupField(fieldId: string) {
  if (localGroupBy.value.length >= MAX_GROUP_LEVELS) {
    ElMessage.warning(`最多支持 ${MAX_GROUP_LEVELS} 级分组`)
    return
  }
  
  if (!localGroupBy.value.includes(fieldId)) {
    localGroupBy.value.push(fieldId)
    updateGroups()
    ElMessage.success('分组字段已添加')
  }
}

function removeGroupField(index: number) {
  localGroupBy.value.splice(index, 1)
  updateGroups()
}

function toggleExpand(key: string) {
  groupNodes.value = toggleGroupExpansion(groupNodes.value, key)
  updateExpandState()
}

function expandAll() {
  groupNodes.value = expandAllGroups(groupNodes.value)
  allExpanded.value = true
}

function collapseAll() {
  groupNodes.value = collapseAllGroups(groupNodes.value)
  allExpanded.value = false
}

function updateExpandState() {
  const checkExpanded = (nodes: GroupNode[]): boolean => {
    return nodes.every(n => n.isExpanded && (!n.children || checkExpanded(n.children)))
  }
  allExpanded.value = checkExpanded(groupNodes.value)
}

function updateGroups() {
  if (localGroupBy.value.length === 0) {
    groupNodes.value = []
    return
  }

  const config: GroupConfig = {
    fieldIds: localGroupBy.value,
    showAggregations: props.showAggregations
  }

  groupNodes.value = groupRecords(
    props.records as any[],
    config,
    props.fields
  )
}

watch(() => [props.records, props.groupBy], () => {
  updateGroups()
}, { deep: true, immediate: true })

function getGroupIcon(field: FieldEntity) {
  switch (field.type) {
    case FieldType.SINGLE_SELECT:
    case FieldType.MULTI_SELECT:
      return 'CollectionTag'
    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return 'Calendar'
    case FieldType.CHECKBOX:
      return 'Check'
    case FieldType.MEMBER:
      return 'User'
    case FieldType.NUMBER:
      return 'Sort'
    default:
      return 'Folder'
  }
}

function getIndentStyle(level: number) {
  return {
    paddingLeft: `${level * 24 + 8}px`
  }
}
</script>

<template>
  <div class="group-panel">
    <div class="panel-header">
      <div class="header-title">
        <span class="title">分组设置</span>
        <span v-if="localGroupBy.length > 0" class="group-count">
          {{ localGroupBy.length }} / {{ MAX_GROUP_LEVELS }} 级
        </span>
      </div>
      <div class="header-actions">
        <el-button
          v-if="groupNodes.length > 0"
          text
          size="small"
          @click="allExpanded ? collapseAll() : expandAll()"
        >
          {{ allExpanded ? '全部折叠' : '全部展开' }}
        </el-button>
      </div>
    </div>

    <div class="group-fields">
      <div class="fields-label">
        分组字段：
        <span v-if="isMaxLevelReached" class="limit-hint">(已达最大层级)</span>
      </div>
      <div ref="fieldsListRef" class="fields-list">
        <template v-if="localGroupBy.length > 0">
          <div
            v-for="(fieldId, index) in localGroupBy"
            :key="fieldId"
            class="field-tag-wrapper"
          >
            <span class="drag-handle" title="拖拽排序">
              <el-icon><Rank /></el-icon>
            </span>
            <el-tag
              closable
              size="small"
              class="field-tag"
              @close="removeGroupField(index)"
            >
              <el-icon class="tag-icon">
                <component :is="getGroupIcon(selectedGroupFields[index])" />
              </el-icon>
              {{ selectedGroupFields[index]?.name }}
            </el-tag>
            <span v-if="index < localGroupBy.length - 1" class="level-arrow">
              <el-icon><ArrowRight /></el-icon>
            </span>
          </div>
        </template>
        <span v-else class="no-fields">未设置分组</span>
      </div>
    </div>

    <div class="add-group">
      <el-dropdown
        trigger="click"
        :disabled="!canAddMoreGroups"
        @command="addGroupField"
      >
        <el-button 
          type="primary" 
          plain 
          size="small"
          :disabled="!canAddMoreGroups"
        >
          <el-icon><Plus /></el-icon>
          添加分组
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="field in availableFields.filter(f => !localGroupBy.includes(f.id))"
              :key="field.id"
              :command="field.id"
              :disabled="localGroupBy.length >= MAX_GROUP_LEVELS"
            >
              <el-icon>
                <component :is="getGroupIcon(field)" />
              </el-icon>
              {{ field.name }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <span v-if="isMaxLevelReached" class="limit-tip">
        最多 {{ MAX_GROUP_LEVELS }} 级分组
      </span>
    </div>

    <div v-if="groupNodes.length > 0" class="group-tree">
      <div class="tree-header">
        <span class="header-text">分组预览</span>
        <span class="header-count">
          共 {{ totalRecords }} 条，显示 {{ visibleRecords }} 条
        </span>
      </div>
      <div class="tree-content">
        <div
          v-for="item in flattenedGroups"
          :key="`${item.node.key}-${item.level}`"
          class="group-node"
          :style="getIndentStyle(item.level)"
        >
          <div class="node-content" @click="toggleExpand(item.node.key)">
            <el-icon
              v-if="item.node.children && item.node.children.length > 0"
              class="expand-icon"
              :class="{ expanded: item.node.isExpanded }"
            >
              <ArrowRight />
            </el-icon>
            <span v-else class="expand-placeholder" />
            
            <span class="node-value">{{ item.node.value }}</span>
            <span class="node-count">({{ item.node.count }})</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="localGroupBy.length === 0" class="empty-state">
      <el-icon class="empty-icon"><FolderOpened /></el-icon>
      <span>选择字段进行分组</span>
    </div>
  </div>
</template>

<script lang="ts">
import { Plus, ArrowRight, FolderOpened, Rank } from '@element-plus/icons-vue'
export default {
  name: 'GroupPanel'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.group-panel {
  background-color: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  min-width: 350px;
  max-width: 450px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
  padding-bottom: $spacing-sm;
  border-bottom: 1px solid $border-color;
}

.header-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.title {
  font-size: $font-size-base;
  font-weight: 500;
  color: $text-primary;
}

.group-count {
  font-size: $font-size-xs;
  color: $text-secondary;
  background-color: $bg-color;
  padding: 2px $spacing-sm;
  border-radius: $border-radius-sm;
}

.group-fields {
  margin-bottom: $spacing-md;
}

.fields-label {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-bottom: $spacing-xs;
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.limit-hint {
  color: $warning-color;
  font-size: $font-size-xs;
}

.fields-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  align-items: center;
}

.field-tag-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
}

.drag-handle {
  cursor: grab;
  color: $text-secondary;
  display: flex;
  align-items: center;
  padding: 2px;
  border-radius: $border-radius-sm;
  transition: all $transition-fast;

  &:hover {
    background-color: $bg-color;
    color: $text-primary;
  }

  &:active {
    cursor: grabbing;
  }
}

.field-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tag-icon {
  font-size: 12px;
}

.level-arrow {
  color: $text-secondary;
  display: flex;
  align-items: center;
  font-size: 12px;
}

.no-fields {
  font-size: $font-size-sm;
  color: $text-disabled;
}

.add-group {
  margin-bottom: $spacing-md;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.limit-tip {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.group-tree {
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  overflow: hidden;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-sm $spacing-md;
  background-color: $bg-color;
  border-bottom: 1px solid $border-color;
}

.header-text {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
}

.header-count {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.tree-content {
  max-height: 250px;
  overflow-y: auto;
}

.group-node {
  border-bottom: 1px solid $border-color;

  &:last-child {
    border-bottom: none;
  }
}

.node-content {
  display: flex;
  align-items: center;
  padding: $spacing-sm $spacing-sm;
  cursor: pointer;
  transition: background-color $transition-fast;

  &:hover {
    background-color: $bg-color;
  }
}

.expand-icon {
  font-size: 12px;
  color: $text-secondary;
  transition: transform $transition-fast;
  margin-right: $spacing-xs;

  &.expanded {
    transform: rotate(90deg);
  }
}

.expand-placeholder {
  width: 16px;
  margin-right: $spacing-xs;
}

.node-value {
  font-size: $font-size-sm;
  color: $text-primary;
  flex: 1;
}

.node-count {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-xl;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: $spacing-sm;
  color: $text-disabled;
}

// 响应式适配
@media (max-width: 768px) {
  .group-panel {
    min-width: 280px;
    max-width: 100%;
  }
  
  .fields-list {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .field-tag-wrapper {
    width: 100%;
  }
}
</style>
