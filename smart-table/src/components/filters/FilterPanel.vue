<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FieldEntity } from '../../db/schema'
import type { FilterCondition } from '../../types'
import { createEmptyCondition, isValidCondition, getConditionDescription } from '../../utils/filter'
import { generateId } from '../../utils/id'
import FilterConditionComponent from './FilterCondition.vue'

interface Props {
  fields: FieldEntity[]
  modelValue: FilterCondition[]
  conjunction?: 'and' | 'or'
}

const props = withDefaults(defineProps<Props>(), {
  conjunction: 'and'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: FilterCondition[]): void
  (e: 'update:conjunction', value: 'and' | 'or'): void
  (e: 'apply'): void
  (e: 'reset'): void
}>()

const localConditions = ref<FilterCondition[]>([])
const localConjunction = ref<'and' | 'or'>(props.conjunction)

watch(() => props.modelValue, (newVal) => {
  localConditions.value = newVal.map(c => ({ ...c }))
}, { immediate: true, deep: true })

watch(() => props.conjunction, (newVal) => {
  localConjunction.value = newVal
})

watch(localConditions, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

watch(localConjunction, (newVal) => {
  emit('update:conjunction', newVal)
})

const hasConditions = computed(() => {
  return localConditions.value.length > 0
})

const validConditionsCount = computed(() => {
  return localConditions.value.filter(c => isValidCondition(c)).length
})

const conditionDescriptions = computed(() => {
  return localConditions.value
    .filter(c => isValidCondition(c))
    .map(c => getConditionDescription(c, props.fields))
})

function addCondition() {
  const firstField = props.fields[0]
  if (!firstField) return

  const newCondition = createEmptyCondition(firstField.id)
  localConditions.value.push(newCondition)
}

function updateCondition(index: number, condition: FilterCondition) {
  localConditions.value[index] = condition
}

function removeCondition(index: number) {
  localConditions.value.splice(index, 1)
}

function clearAllConditions() {
  localConditions.value = []
}

function handleApply() {
  emit('apply')
}

function handleReset() {
  localConditions.value = []
  emit('reset')
}

function saveFilterPreset() {
  const preset = {
    id: generateId(),
    name: `筛选预设 ${new Date().toLocaleString()}`,
    conditions: localConditions.value,
    conjunction: localConjunction.value,
    createdAt: Date.now()
  }
  
  const presets = JSON.parse(localStorage.getItem('filterPresets') || '[]')
  presets.push(preset)
  localStorage.setItem('filterPresets', JSON.stringify(presets))
}
</script>

<template>
  <div class="filter-panel">
    <div class="panel-header">
      <div class="header-title">
        <span class="title">筛选条件</span>
        <span v-if="validConditionsCount > 0" class="condition-count">
          {{ validConditionsCount }} 个条件
        </span>
      </div>
      <div class="header-actions">
        <el-button
          text
          size="small"
          @click="saveFilterPreset"
          :disabled="!hasConditions"
        >
          保存预设
        </el-button>
        <el-button
          text
          size="small"
          type="danger"
          @click="clearAllConditions"
          :disabled="!hasConditions"
        >
          清空
        </el-button>
      </div>
    </div>

    <div v-if="hasConditions" class="conjunction-toggle">
      <el-radio-group v-model="localConjunction" size="small">
        <el-radio-button value="and">且 (AND)</el-radio-button>
        <el-radio-button value="or">或 (OR)</el-radio-button>
      </el-radio-group>
    </div>

    <div class="conditions-list">
      <template v-if="hasConditions">
        <FilterConditionComponent
          v-for="(condition, index) in localConditions"
          :key="index"
          :condition="condition"
          :fields="fields"
          :removable="localConditions.length > 1"
          @update:condition="updateCondition(index, $event)"
          @remove="removeCondition(index)"
        />
      </template>
      <div v-else class="empty-state">
        <span>暂无筛选条件</span>
      </div>
    </div>

    <div class="panel-footer">
      <el-button
        type="primary"
        plain
        size="small"
        @click="addCondition"
      >
        添加条件
      </el-button>
      <div class="footer-actions">
        <el-button
          size="small"
          @click="handleReset"
        >
          重置
        </el-button>
        <el-button
          type="primary"
          size="small"
          @click="handleApply"
          :disabled="validConditionsCount === 0"
        >
          应用
        </el-button>
      </div>
    </div>

    <div v-if="conditionDescriptions.length > 0" class="condition-summary">
      <div class="summary-title">当前筛选：</div>
      <div class="summary-content">
        <el-tag
          v-for="(desc, index) in conditionDescriptions"
          :key="index"
          size="small"
          type="info"
          class="summary-tag"
        >
          {{ desc }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  name: 'FilterPanel'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.filter-panel {
  background-color: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  min-width: 400px;
  max-width: 600px;
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

.condition-count {
  font-size: $font-size-xs;
  color: $text-secondary;
  background-color: $bg-color;
  padding: 2px $spacing-sm;
  border-radius: $border-radius-sm;
}

.header-actions {
  display: flex;
  gap: $spacing-xs;
}

.conjunction-toggle {
  margin-bottom: $spacing-md;
}

.conditions-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: $spacing-md;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  color: $text-secondary;
  font-size: $font-size-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
}

.panel-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: $spacing-sm;
  border-top: 1px solid $border-color;
}

.footer-actions {
  display: flex;
  gap: $spacing-sm;
}

.condition-summary {
  margin-top: $spacing-md;
  padding-top: $spacing-md;
  border-top: 1px solid $border-color;
}

.summary-title {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-bottom: $spacing-sm;
}

.summary-content {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.summary-tag {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
