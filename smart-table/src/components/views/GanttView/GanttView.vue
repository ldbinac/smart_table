<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import { FieldType } from '@/types'
import dayjs from 'dayjs'

interface Props {
  tableId: string
  viewId: string
  fields: FieldEntity[]
  records: RecordEntity[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'updateRecord', recordId: string, values: Record<string, unknown>): void
  (e: 'addRecord', values: Record<string, unknown>): void
  (e: 'deleteRecord', recordId: string): void
  (e: 'editRecord', recordId: string): void
}>()

const startDateFieldId = ref<string>('')
const endDateFieldId = ref<string>('')
const titleFieldId = ref<string>('')
const progressFieldId = ref<string>('')
const dependencyFieldId = ref<string>('')
const currentDate = ref(new Date())
const viewMode = ref<'day' | 'week' | 'month'>('week')

const timelineRef = ref<HTMLElement | null>(null)
const isDragging = ref(false)
const dragTask = ref<GanttTask | null>(null)
const dragType = ref<'move' | 'resize-left' | 'resize-right'>('move')
const dragStartX = ref(0)
const dragStartLeft = ref(0)
const dragStartWidth = ref(0)
const dragStartDate = ref<Date | null>(null)
const dragEndDate = ref<Date | null>(null)

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

const progressFields = computed(() => {
  return props.fields.filter(f =>
    f.type === FieldType.PROGRESS ||
    f.type === FieldType.NUMBER
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
  dependencies: string[]
}

interface DependencyLine {
  fromX: number
  fromY: number
  toX: number
  toY: number
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

      const start = parseDateValue(startValue)
      const end = endValue
        ? parseDateValue(endValue)
        : new Date(start.getTime() + 24 * 60 * 60 * 1000)

      const dependencies: string[] = []
      if (dependencyFieldId.value) {
        const depValue = record.values[dependencyFieldId.value]
        if (depValue && Array.isArray(depValue)) {
          depValue.forEach((dep: any) => {
            if (typeof dep === 'string') {
              dependencies.push(dep)
            } else if (dep && dep.id) {
              dependencies.push(dep.id)
            }
          })
        }
      }

      return {
        id: record.id,
        title: String(titleValue || '无标题'),
        start,
        end,
        progress: Math.min(100, Math.max(0, Number(progressValue) || 0)),
        record,
        duration: Math.max(1, Math.ceil((end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000))),
        dependencies
      }
    })
    .filter(task => !isNaN(task.start.getTime()) && !isNaN(task.end.getTime()))
    .sort((a, b) => a.start.getTime() - b.start.getTime())
})

function parseDateValue(value: unknown): Date {
  if (!value) return new Date()

  if (typeof value === 'number') {
    return new Date(value)
  }

  if (typeof value === 'string') {
    const numValue = Number(value)
    if (!isNaN(numValue) && value.trim() !== '') {
      return new Date(numValue)
    }
    const date = new Date(value)
    if (!isNaN(date.getTime())) {
      return date
    }
  }

  if (value instanceof Date) {
    return value
  }

  return new Date()
}

const timelineStart = computed(() => {
  if (tasks.value.length === 0) {
    return dayjs(currentDate.value).startOf('week').toDate()
  }
  const minDate = new Date(Math.min(...tasks.value.map(t => t.start.getTime())))
  return dayjs(minDate).subtract(3, 'day').toDate()
})

const timelineEnd = computed(() => {
  if (tasks.value.length === 0) {
    return dayjs(currentDate.value).endOf('week').toDate()
  }
  const maxDate = new Date(Math.max(...tasks.value.map(t => t.end.getTime())))
  return dayjs(maxDate).add(7, 'day').toDate()
})

const totalDays = computed(() => {
  return Math.ceil((timelineEnd.value.getTime() - timelineStart.value.getTime()) / (24 * 60 * 60 * 1000))
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

const cellWidth = computed(() => {
  switch (viewMode.value) {
    case 'day': return 60
    case 'week': return 40
    case 'month': return 30
    default: return 40
  }
})

const timelineWidth = computed(() => {
  return totalDays.value * cellWidth.value
})

function getTaskStyle(task: GanttTask): Record<string, string> {
  const startOffset = Math.floor((task.start.getTime() - timelineStart.value.getTime()) / (24 * 60 * 60 * 1000))
  const duration = Math.max(1, task.duration)

  return {
    left: `${startOffset * cellWidth.value}px`,
    width: `${duration * cellWidth.value - 4}px`
  }
}

function getTaskRowStyle(index: number): Record<string, string> {
  return {
    top: `${index * 44 + 8}px`
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

function isFirstDayOfMonth(date: Date): boolean {
  return date.getDate() === 1
}

function getMonthLabel(date: Date): string {
  return dayjs(date).format('YYYY年M月')
}

function handleTaskClick(task: GanttTask) {
  emit('editRecord', task.id)
}

function handleMouseDown(event: MouseEvent, task: GanttTask, type: 'move' | 'resize-left' | 'resize-right') {
  event.preventDefault()
  event.stopPropagation()

  isDragging.value = true
  dragTask.value = task
  dragType.value = type
  dragStartX.value = event.clientX

  const taskEl = event.currentTarget as HTMLElement
  const rect = taskEl.getBoundingClientRect()
  const parentRect = taskEl.parentElement?.getBoundingClientRect()

  if (parentRect) {
    dragStartLeft.value = rect.left - parentRect.left
    dragStartWidth.value = rect.width
  }

  dragStartDate.value = new Date(task.start)
  dragEndDate.value = new Date(task.end)

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

function handleMouseMove(event: MouseEvent) {
  if (!isDragging.value || !dragTask.value) return

  const deltaX = event.clientX - dragStartX.value
  const dayDelta = Math.round(deltaX / cellWidth.value)

  if (dragType.value === 'move') {
    const newStart = new Date(dragStartDate.value!)
    newStart.setDate(newStart.getDate() + dayDelta)
    const newEnd = new Date(dragEndDate.value!)
    newEnd.setDate(newEnd.getDate() + dayDelta)

    dragTask.value.start = newStart
    dragTask.value.end = newEnd
  } else if (dragType.value === 'resize-right') {
    const newWidth = Math.max(cellWidth.value, dragStartWidth.value + deltaX)
    const newDuration = Math.round(newWidth / cellWidth.value)
    const newEnd = new Date(dragStartDate.value!)
    newEnd.setDate(newEnd.getDate() + newDuration)

    dragTask.value.end = newEnd
    dragTask.value.duration = newDuration
  } else if (dragType.value === 'resize-left') {
    const newWidth = Math.max(cellWidth.value, dragStartWidth.value - deltaX)
    const newDuration = Math.round(newWidth / cellWidth.value)
    const newStart = new Date(dragEndDate.value!)
    newStart.setDate(newStart.getDate() - newDuration)

    dragTask.value.start = newStart
    dragTask.value.duration = newDuration
  }
}

function handleMouseUp() {
  if (isDragging.value && dragTask.value) {
    const updates: Record<string, unknown> = {}

    if (startDateFieldId.value) {
      updates[startDateFieldId.value] = dragTask.value.start.getTime()
    }
    if (endDateFieldId.value) {
      updates[endDateFieldId.value] = dragTask.value.end.getTime()
    }

    emit('updateRecord', dragTask.value.id, updates)
  }

  isDragging.value = false
  dragTask.value = null

  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
}

const dependencyLines = computed<DependencyLine[]>(() => {
  const lines: DependencyLine[] = []

  if (!timelineRef.value) return lines

  const taskElements = timelineRef.value.querySelectorAll('.task-bar')
  const taskPositions = new Map<string, { x: number; y: number; width: number }>()

  taskElements.forEach((el, index) => {
    const task = tasks.value[index]
    if (task) {
      const rect = el.getBoundingClientRect()
      const parentRect = timelineRef.value!.getBoundingClientRect()
      taskPositions.set(task.id, {
        x: rect.left - parentRect.left,
        y: rect.top - parentRect.top + rect.height / 2,
        width: rect.width
      })
    }
  })

  tasks.value.forEach((task) => {
    task.dependencies.forEach(depId => {
      const fromPos = taskPositions.get(depId)
      const toPos = taskPositions.get(task.id)

      if (fromPos && toPos) {
        lines.push({
          fromX: fromPos.x + fromPos.width,
          fromY: fromPos.y,
          toX: toPos.x,
          toY: toPos.y
        })
      }
    })
  })

  return lines
})

function goToToday() {
  currentDate.value = new Date()
}

function zoomIn() {
  if (viewMode.value === 'month') {
    viewMode.value = 'week'
  } else if (viewMode.value === 'week') {
    viewMode.value = 'day'
  }
}

function zoomOut() {
  if (viewMode.value === 'day') {
    viewMode.value = 'week'
  } else if (viewMode.value === 'week') {
    viewMode.value = 'month'
  }
}

onMounted(() => {
  if (dateFields.value.length > 0) {
    startDateFieldId.value = dateFields.value[0].id
    if (dateFields.value.length > 1) {
      endDateFieldId.value = dateFields.value[1].id
    }
  }
})

watch(() => props.records, () => {
  nextTick(() => {
    // Force recompute dependency lines after DOM update
  })
}, { deep: true })
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
        <el-select v-model="progressFieldId" placeholder="进度字段" class="field-select" clearable>
          <el-option
            v-for="field in progressFields"
            :key="field.id"
            :label="field.name"
            :value="field.id"
          />
        </el-select>
      </div>

      <div class="toolbar-center">
        <el-button-group>
          <el-button size="small" @click="zoomOut">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
          <el-button size="small" @click="goToToday">今天</el-button>
          <el-button size="small" @click="zoomIn">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
        </el-button-group>
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
      <!-- 表头 -->
      <div class="gantt-header">
        <div class="header-left">
          <div class="task-header">任务名称</div>
        </div>
        <div class="header-right" :style="{ width: `${timelineWidth}px` }">
          <!-- 月份标签 -->
          <div class="month-header">
            <div
              v-for="(day, dayIndex) in timeline"
              :key="`month-${day.getTime()}`"
              v-show="isFirstDayOfMonth(day) || dayIndex === 0"
              class="month-cell"
              :style="{ left: `${dayIndex * cellWidth}px` }"
            >
              {{ getMonthLabel(day) }}
            </div>
          </div>
          <!-- 日期标签 -->
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
              <span class="day-number">{{ day.getDate() }}</span>
              <span class="day-week">{{ ['日', '一', '二', '三', '四', '五', '六'][day.getDay()] }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 内容区域 -->
      <div class="gantt-content">
        <!-- 任务列表 -->
        <div class="task-list">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="task-row"
            @click="handleTaskClick(task)"
          >
            <div class="task-info">
              <div class="task-name" :title="task.title">{{ task.title }}</div>
              <div class="task-date">{{ formatDate(task.start) }} - {{ formatDate(task.end) }}</div>
            </div>
          </div>
          <div v-if="tasks.length === 0" class="empty-tasks">
            <el-empty description="暂无任务数据" :image-size="80" />
          </div>
        </div>

        <!-- 时间线区域 -->
        <div ref="timelineRef" class="timeline-body" :style="{ width: `${timelineWidth}px` }">
          <!-- 背景网格 -->
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

          <!-- 当前日期指示线 -->
          <div
            v-if="isToday(new Date()) && new Date() >= timelineStart && new Date() <= timelineEnd"
            class="current-time-line"
            :style="{ left: `${Math.floor((new Date().getTime() - timelineStart.getTime()) / (24 * 60 * 60 * 1000)) * cellWidth + cellWidth / 2}px` }"
          />

          <!-- 依赖关系线条 -->
          <svg class="dependency-layer" v-if="dependencyLines.length > 0">
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#909399" />
              </marker>
            </defs>
            <path
              v-for="(line, index) in dependencyLines"
              :key="index"
              :d="`M ${line.fromX} ${line.fromY} L ${line.toX - 5} ${line.toY}`"
              fill="none"
              stroke="#909399"
              stroke-width="1.5"
              marker-end="url(#arrowhead)"
            />
          </svg>

          <!-- 任务条 -->
          <div class="task-bars">
            <div
              v-for="(task, index) in tasks"
              :key="task.id"
              class="task-bar-wrapper"
              :style="getTaskRowStyle(index)"
            >
              <div
                class="task-bar"
                :class="{ 'is-dragging': isDragging && dragTask?.id === task.id }"
                :style="getTaskStyle(task)"
                @mousedown="(e) => handleMouseDown(e, task, 'move')"
                @click.stop="handleTaskClick(task)"
              >
                <!-- 左侧调整手柄 -->
                <div
                  class="resize-handle resize-left"
                  @mousedown.stop="(e) => handleMouseDown(e, task, 'resize-left')"
                />

                <!-- 进度条 -->
                <div class="bar-progress" :style="{ width: `${task.progress}%` }" />

                <!-- 任务标题 -->
                <span class="bar-title">{{ task.title }}</span>

                <!-- 右侧调整手柄 -->
                <div
                  class="resize-handle resize-right"
                  @mousedown.stop="(e) => handleMouseDown(e, task, 'resize-right')"
                />
              </div>

              <!-- 依赖关系指示器 -->
              <div
                v-if="task.dependencies.length > 0"
                class="dependency-indicator"
                :title="`依赖: ${task.dependencies.length} 个任务`"
              >
                <el-icon><Link /></el-icon>
              </div>
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
  overflow: hidden;
}

.gantt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  border-bottom: 1px solid $border-color;
  background-color: $surface-color;
  flex-shrink: 0;

  .toolbar-left {
    display: flex;
    gap: $spacing-sm;
  }

  .toolbar-center {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }

  .field-select {
    width: 140px;
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
  flex-shrink: 0;

  .header-left {
    width: 220px;
    min-width: 220px;
    border-right: 1px solid $border-color;
  }

  .header-right {
    flex: 1;
    overflow: hidden;
  }
}

.task-header {
  padding: $spacing-sm $spacing-md;
  font-weight: 500;
  color: $text-primary;
  font-size: $font-size-sm;
}

.month-header {
  position: relative;
  height: 20px;
  border-bottom: 1px solid $border-color;
  background-color: $bg-color;
}

.month-cell {
  position: absolute;
  top: 0;
  padding: 2px 8px;
  font-size: $font-size-xs;
  color: $text-secondary;
  font-weight: 500;
  white-space: nowrap;
}

.timeline-header {
  display: flex;
  height: 36px;
}

.timeline-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2px;
  font-size: $font-size-xs;
  color: $text-secondary;
  border-right: 1px solid $border-color;
  background-color: $bg-color;

  .day-number {
    font-weight: 500;
  }

  .day-week {
    font-size: 10px;
    transform: scale(0.9);
  }

  &.today {
    background-color: rgba($primary-color, 0.15);
    color: $primary-color;

    .day-number {
      font-weight: 600;
    }
  }

  &.weekend {
    background-color: rgba($text-disabled, 0.08);
  }
}

.gantt-content {
  flex: 1;
  display: flex;
  overflow: auto;
}

.task-list {
  width: 220px;
  min-width: 220px;
  border-right: 1px solid $border-color;
  background-color: $surface-color;
  flex-shrink: 0;
}

.task-row {
  height: 44px;
  padding: $spacing-xs $spacing-md;
  border-bottom: 1px solid $border-color;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: $bg-color;
  }
}

.task-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
}

.task-name {
  font-size: $font-size-sm;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.task-date {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: 2px;
}

.empty-tasks {
  padding: $spacing-xl;
}

.timeline-body {
  position: relative;
  min-height: 100%;
  flex-shrink: 0;
}

.timeline-grid {
  display: flex;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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

.current-time-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background-color: $error-color;
  z-index: 10;
  pointer-events: none;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -4px;
    width: 10px;
    height: 10px;
    background-color: $error-color;
    border-radius: 50%;
  }
}

.dependency-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 5;
}

.task-bars {
  position: relative;
  padding-top: 0;
  min-height: 100%;
}

.task-bar-wrapper {
  position: absolute;
  left: 0;
  right: 0;
  height: 44px;
  display: flex;
  align-items: center;
}

.task-bar {
  position: absolute;
  height: 28px;
  background: linear-gradient(135deg, rgba($primary-color, 0.2) 0%, rgba($primary-color, 0.3) 100%);
  border-radius: $border-radius-sm;
  border-left: 3px solid $primary-color;
  cursor: grab;
  overflow: hidden;
  display: flex;
  align-items: center;
  transition: box-shadow 0.2s, transform 0.1s;
  user-select: none;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    z-index: 10;
  }

  &.is-dragging {
    cursor: grabbing;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    z-index: 20;
    opacity: 0.9;
  }
}

.resize-handle {
  position: absolute;
  top: 0;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 5;

  &:hover {
    opacity: 1;
    background-color: rgba($primary-color, 0.3);
  }

  &.resize-left {
    left: 0;
  }

  &.resize-right {
    right: 0;
  }
}

.task-bar:hover .resize-handle {
  opacity: 0.5;
}

.bar-progress {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: $primary-color;
  opacity: 0.6;
  transition: width 0.3s ease;
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
  flex: 1;
}

.dependency-indicator {
  position: absolute;
  right: -20px;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-secondary;
  font-size: $font-size-xs;
}
</style>
