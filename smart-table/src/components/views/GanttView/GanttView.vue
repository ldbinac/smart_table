<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import { FieldType } from '@/types'
import dayjs from 'dayjs'

interface Props {
  fields: FieldEntity[]
  records: RecordEntity[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'updateRecord', recordId: string, values: Record<string, unknown>): void
  (e: 'addRecord', values: Record<string, unknown>): void
  (e: 'deleteRecord', recordId: string): void
}>()

const startDateFieldId = ref<string>('')
const endDateFieldId = ref<string>('')
const titleFieldId = ref<string>('')
const progressFieldId = ref<string>('')
const currentDate = ref(new Date())
const viewMode = ref<'day' | 'week' | 'month'>('week')

const dateFields = computed(() => {
  return props.fields.filter(f => 
    f.type === FieldType.DATE || 
    f.type === FieldType.CREATED_TIME || 
    f.type === FieldType.UPDATED_TIME
  )
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

interface GanttTask {
  id: string
  title: string
  start: Date
  end: Date
  progress: number
  record: RecordEntity
  duration: number
  left: number
  width: number
}

const tasks = computed<GanttTask[]>(() => {
  if (!startDateFieldId.value) return []
  
  return props.records
    .filter(record => record.values[startDateFieldId.value])
    .map(record => {
      const startValue = record.values[startDateFieldId.value]
      const endValue = endDateFieldId.value ? record.values[endDateFieldId.value] : null
      const titleValue = titleField.value ? record.values[titleField.value!.id] : ''
      const progressValue = progressFieldId.value ? record.values[progressFieldId.value] : 0
      
      const start = new Date(Number(startValue) as number)
      const end = endValue ? new Date(Number(endValue) as number) : new Date(start.getTime() + 24 * 60 * 60 * 1000)
      
      return {
        id: record.id,
        title: String(titleValue || '无标题'),
        start,
        end,
        progress: Number(progressValue) || 0,
        record,
        duration: Math.ceil((end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000)),
        left: 0,
        width: 0
      }
    })
    .filter(task => !isNaN(task.start.getTime()) && !isNaN(task.end.getTime()))
    .sort((a, b) => a.start.getTime() - b.start.getTime())
})

const timelineStart = computed(() => {
  if (tasks.value.length === 0) {
    return dayjs(currentDate.value).startOf('month').toDate()
  }
  const minDate = new Date(Math.min(...tasks.value.map(t => t.start.getTime())))
  return dayjs(minDate).startOf(viewMode.value).toDate()
})

const timelineEnd = computed(() => {
  if (tasks.value.length === 0) {
    return dayjs(currentDate.value).endOf('month').toDate()
  }
  const maxDate = new Date(Math.max(...tasks.value.map(t => t.end.getTime())))
  return dayjs(maxDate).endOf(viewMode.value).toDate()
})

const timeline = computed(() => {
  const days: Date[] = []
  const current = new Date(timelineStart.value)
  
  while (current <= timelineEnd.value) {
    days.push(new Date(current))
    current.setDate(current.getDate() + 1)
  }
  
  return days
})

const cellWidth = 40

function getTaskStyle(task: GanttTask): Record<string, string> {
  const startOffset = Math.floor((task.start.getTime() - timelineStart.value.getTime()) / (24 * 60 * 60 * 1000))
  const duration = Math.max(1, task.duration)
  
  return {
    left: `${startOffset * cellWidth}px`,
    width: `${duration * cellWidth}px`
  }
}

function formatDate(date: Date): string {
  return dayjs(date).format('MM/DD')
}

function isToday(date: Date): boolean {
  return dayjs(date).isSame(dayjs(), 'day')
}

function isWeekend(date: Date): boolean {
  const day = date.getDay()
  return day === 0 || day === 6
}

function handleTaskClick(task: GanttTask) {
  console.log('Task clicked:', task)
}

onMounted(() => {
  if (dateFields.value.length > 0) {
    startDateFieldId.value = dateFields.value[0].id
    if (dateFields.value.length > 1) {
      endDateFieldId.value = dateFields.value[1].id
    }
  }
})
</script>

<template>
  <div class="gantt-view">
    <div class="gantt-toolbar">
      <div class="toolbar-left">
        <el-select v-model="startDateFieldId" placeholder="开始日期字段" class="field-select">
          <el-option
            v-for="field in dateFields"
            :key="field.id"
            :label="field.name"
            :value="field.id"
          />
        </el-select>
        <el-select v-model="endDateFieldId" placeholder="结束日期字段" class="field-select">
          <el-option
            v-for="field in dateFields"
            :key="field.id"
            :label="field.name"
            :value="field.id"
          />
        </el-select>
        <el-select v-model="titleFieldId" placeholder="标题字段" class="field-select">
          <el-option
            v-for="field in titleFields"
            :key="field.id"
            :label="field.name"
            :value="field.id"
          />
        </el-select>
      </div>
      
      <div class="toolbar-right">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="day">日</el-radio-button>
          <el-radio-button value="week">周</el-radio-button>
          <el-radio-button value="month">月</el-radio-button>
        </el-radio-group>
      </div>
    </div>
    
    <div class="gantt-body">
      <div class="gantt-header">
        <div class="header-left">
          <div class="task-header">任务名称</div>
        </div>
        <div class="header-right">
          <div class="timeline-header">
            <div
              v-for="day in timeline"
              :key="day.getTime()"
              class="timeline-cell"
              :class="{
                today: isToday(day),
                weekend: isWeekend(day)
              }"
              :style="{ width: `${cellWidth}px` }"
            >
              {{ formatDate(day) }}
            </div>
          </div>
        </div>
      </div>
      
      <div class="gantt-content">
        <div class="task-list">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="task-row"
          >
            <div class="task-name">{{ task.title }}</div>
          </div>
          <div v-if="tasks.length === 0" class="empty-tasks">
            暂无任务数据
          </div>
        </div>
        
        <div class="timeline-body">
          <div class="timeline-grid">
            <div
              v-for="day in timeline"
              :key="day.getTime()"
              class="grid-cell"
              :class="{
                today: isToday(day),
                weekend: isWeekend(day)
              }"
              :style="{ width: `${cellWidth}px` }"
            />
          </div>
          
          <div class="task-bars">
            <div
              v-for="task in tasks"
              :key="task.id"
              class="task-bar"
              :style="getTaskStyle(task)"
              @click="handleTaskClick(task)"
            >
              <div class="bar-progress" :style="{ width: `${task.progress}%` }" />
              <span class="bar-title">{{ task.title }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.gantt-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $surface-color;
}

.gantt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  border-bottom: 1px solid $border-color;
  
  .toolbar-left {
    display: flex;
    gap: $spacing-sm;
  }
  
  .field-select {
    width: 150px;
  }
}

.gantt-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.gantt-header {
  display: flex;
  border-bottom: 1px solid $border-color;
  background-color: $bg-color;
  
  .header-left {
    width: 200px;
    min-width: 200px;
    border-right: 1px solid $border-color;
  }
  
  .header-right {
    flex: 1;
    overflow-x: auto;
  }
}

.task-header {
  padding: $spacing-sm $spacing-md;
  font-weight: 500;
  color: $text-primary;
}

.timeline-header {
  display: flex;
}

.timeline-cell {
  padding: $spacing-sm 4px;
  text-align: center;
  font-size: $font-size-xs;
  color: $text-secondary;
  border-right: 1px solid $border-color;
  
  &.today {
    background-color: rgba($primary-color, 0.1);
    color: $primary-color;
    font-weight: 500;
  }
  
  &.weekend {
    background-color: rgba($text-disabled, 0.05);
  }
}

.gantt-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.task-list {
  width: 200px;
  min-width: 200px;
  border-right: 1px solid $border-color;
  overflow-y: auto;
}

.task-row {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 $spacing-md;
  border-bottom: 1px solid $border-color;
  
  &:hover {
    background-color: $bg-color;
  }
}

.task-name {
  font-size: $font-size-sm;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-tasks {
  padding: $spacing-xl;
  text-align: center;
  color: $text-disabled;
}

.timeline-body {
  flex: 1;
  overflow: auto;
  position: relative;
}

.timeline-grid {
  display: flex;
  position: absolute;
  top: 0;
  left: 0;
}

.grid-cell {
  height: 100%;
  border-right: 1px solid $border-color;
  
  &.today {
    background-color: rgba($primary-color, 0.05);
  }
  
  &.weekend {
    background-color: rgba($text-disabled, 0.03);
  }
}

.task-bars {
  position: relative;
  padding-top: 8px;
}

.task-bar {
  position: absolute;
  height: 28px;
  margin-bottom: 12px;
  background-color: rgba($primary-color, 0.2);
  border-radius: $border-radius-sm;
  border-left: 3px solid $primary-color;
  cursor: pointer;
  overflow: hidden;
  
  &:hover {
    background-color: rgba($primary-color, 0.3);
  }
}

.bar-progress {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: $primary-color;
  opacity: 0.5;
}

.bar-title {
  position: relative;
  z-index: 1;
  display: block;
  padding: 4px 8px;
  font-size: $font-size-xs;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
