<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";
import dayjs from "dayjs";
import {
  Calendar,
  EditPen,
  DataAnalysis,
  ZoomIn,
  ZoomOut,
  Link,
} from "@element-plus/icons-vue";

interface Props {
  tableId: string;
  viewId: string;
  fields: FieldEntity[];
  records: RecordEntity[];
  readonly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
});
const emit = defineEmits<{
  (e: "updateRecord", recordId: string, values: Record<string, unknown>): void;
  (e: "addRecord", values: Record<string, unknown>): void;
  (e: "deleteRecord", recordId: string): void;
  (e: "editRecord", recordId: string): void;
}>();

const startDateFieldId = ref<string>("");
const endDateFieldId = ref<string>("");
const titleFieldId = ref<string>("");
const progressFieldId = ref<string>("");
const dependencyFieldId = ref<string>("");
const currentDate = ref(new Date());
const viewMode = ref<"day" | "week" | "month">("week");

const timelineRef = ref<HTMLElement | null>(null);
const ganttContentRef = ref<HTMLElement | null>(null);
const headerRightWrapperRef = ref<HTMLElement | null>(null);
const isDragging = ref(false);
const dragTask = ref<GanttTask | null>(null);
const dragType = ref<"move" | "resize-left" | "resize-right">("move");
const dragStartX = ref(0);
const dragStartLeft = ref(0);
const dragStartWidth = ref(0);
const dragStartDate = ref<Date | null>(null);
const dragEndDate = ref<Date | null>(null);
const hoveredTask = ref<GanttTask | null>(null);

const dateFields = computed(() => {
  return props.fields.filter(
    (f) =>
      f.type === FieldType.DATE ||
      f.type === FieldType.CREATED_TIME ||
      f.type === FieldType.UPDATED_TIME,
  );
});

const titleFields = computed(() => {
  return props.fields.filter(
    (f) =>
      f.type === FieldType.TEXT ||
      f.type === FieldType.NUMBER ||
      f.type === FieldType.SINGLE_SELECT,
  );
});

const progressFields = computed(() => {
  return props.fields.filter(
    (f) => f.type === FieldType.PROGRESS || f.type === FieldType.NUMBER,
  );
});

const titleField = computed(() => {
  if (titleFieldId.value) {
    return props.fields.find((f) => f.id === titleFieldId.value);
  }
  return props.fields.find((f) => f.isPrimary) || props.fields[0];
});

interface GanttTask {
  id: string;
  title: string;
  start: Date;
  end: Date;
  progress: number;
  record: RecordEntity;
  duration: number;
  dependencies: string[];
}

interface DependencyLine {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
}

const tasks = computed<GanttTask[]>(() => {
  if (!startDateFieldId.value) return [];

  return props.records
    .filter((record) => record.values[startDateFieldId.value])
    .map((record) => {
      const startValue = record.values[startDateFieldId.value];
      const endValue = endDateFieldId.value
        ? record.values[endDateFieldId.value]
        : null;
      let titleValue = titleField.value
        ? record.values[titleField.value!.id]
        : "";

      // 处理单选字段，显示选项名称而不是ID
      if (
        titleField.value &&
        titleField.value.type === FieldType.SINGLE_SELECT &&
        titleField.value.options?.choices
      ) {
        const options = titleField.value.options.choices;
        const selectedOption = options.find(
          (opt: any) => opt.id === titleValue,
        );
        titleValue = selectedOption?.name || titleValue || "";
      }
      const progressValue = progressFieldId.value
        ? record.values[progressFieldId.value]
        : 0;

      const start = parseDateValue(startValue);
      const end = endValue
        ? parseDateValue(endValue)
        : new Date(start.getTime() + 24 * 60 * 60 * 1000);

      const dependencies: string[] = [];
      if (dependencyFieldId.value) {
        const depValue = record.values[dependencyFieldId.value];
        if (depValue && Array.isArray(depValue)) {
          depValue.forEach((dep: any) => {
            if (typeof dep === "string") {
              dependencies.push(dep);
            } else if (dep && dep.id) {
              dependencies.push(dep.id);
            }
          });
        }
      }

      return {
        id: record.id,
        title: String(titleValue || "无标题"),
        start,
        end,
        progress: Math.min(100, Math.max(0, Number(progressValue) || 0)),
        record,
        duration: Math.max(
          1,
          Math.ceil((end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000)),
        ),
        dependencies,
      };
    })
    .filter(
      (task) => !isNaN(task.start.getTime()) && !isNaN(task.end.getTime()),
    )
    .sort((a, b) => a.start.getTime() - b.start.getTime());
});

function parseDateValue(value: unknown): Date {
  if (!value) return new Date();

  if (typeof value === "number") {
    return new Date(value);
  }

  if (typeof value === "string") {
    const numValue = Number(value);
    if (!isNaN(numValue) && value.trim() !== "") {
      return new Date(numValue);
    }
    const date = new Date(value);
    if (!isNaN(date.getTime())) {
      return date;
    }
  }

  if (value instanceof Date) {
    return value;
  }

  return new Date();
}

const timelineStart = computed(() => {
  if (tasks.value.length === 0) {
    return dayjs(currentDate.value).startOf("week").toDate();
  }
  const minDate = new Date(
    Math.min(...tasks.value.map((t) => t.start.getTime())),
  );
  return dayjs(minDate).subtract(3, "day").toDate();
});

const timelineEnd = computed(() => {
  if (tasks.value.length === 0) {
    return dayjs(currentDate.value).endOf("week").toDate();
  }
  const maxDate = new Date(
    Math.max(...tasks.value.map((t) => t.end.getTime())),
  );
  return dayjs(maxDate).add(7, "day").toDate();
});

const totalDays = computed(() => {
  return Math.ceil(
    (timelineEnd.value.getTime() - timelineStart.value.getTime()) /
      (24 * 60 * 60 * 1000),
  );
});

const timeline = computed(() => {
  const days: Date[] = [];
  const current = new Date(timelineStart.value);

  while (current <= timelineEnd.value) {
    days.push(new Date(current));
    current.setDate(current.getDate() + 1);
  }

  return days;
});

const cellWidth = computed(() => {
  switch (viewMode.value) {
    case "day":
      return 60;
    case "week":
      return 40;
    case "month":
      return 30;
    default:
      return 40;
  }
});

const timelineWidth = computed(() => {
  return totalDays.value * cellWidth.value;
});

function getTaskStyle(task: GanttTask): Record<string, string> {
  const startOffset = Math.floor(
    (task.start.getTime() - timelineStart.value.getTime()) /
      (24 * 60 * 60 * 1000),
  );
  const duration = Math.max(1, task.duration);

  return {
    left: `${startOffset * cellWidth.value}px`,
    width: `${duration * cellWidth.value - 4}px`,
  };
}

function getTaskRowStyle(index: number): Record<string, string> {
  return {
    top: `${index * 48 + 10}px`,
  };
}

function formatDate(date: Date): string {
  return dayjs(date).format("MM/DD");
}

function isToday(date: Date): boolean {
  return dayjs(date).isSame(dayjs(), "day");
}

function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6;
}

function isFirstDayOfMonth(date: Date): boolean {
  return date.getDate() === 1;
}

function getMonthLabel(date: Date): string {
  return dayjs(date).format("YYYY年M月");
}

function handleTaskClick(task: GanttTask) {
  emit("editRecord", task.id);
}

function handleMouseDown(
  event: MouseEvent,
  task: GanttTask,
  type: "move" | "resize-left" | "resize-right",
) {
  event.preventDefault();
  event.stopPropagation();

  isDragging.value = true;
  dragTask.value = task;
  dragType.value = type;
  dragStartX.value = event.clientX;

  const taskEl = event.currentTarget as HTMLElement;
  const rect = taskEl.getBoundingClientRect();
  const parentRect = taskEl.parentElement?.getBoundingClientRect();

  if (parentRect) {
    dragStartLeft.value = rect.left - parentRect.left;
    dragStartWidth.value = rect.width;
  }

  dragStartDate.value = new Date(task.start);
  dragEndDate.value = new Date(task.end);

  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);
}

function handleMouseMove(event: MouseEvent) {
  if (!isDragging.value || !dragTask.value) return;

  const deltaX = event.clientX - dragStartX.value;
  const dayDelta = Math.round(deltaX / cellWidth.value);

  if (dragType.value === "move") {
    const newStart = new Date(dragStartDate.value!);
    newStart.setDate(newStart.getDate() + dayDelta);
    const newEnd = new Date(dragEndDate.value!);
    newEnd.setDate(newEnd.getDate() + dayDelta);

    dragTask.value.start = newStart;
    dragTask.value.end = newEnd;
  } else if (dragType.value === "resize-right") {
    const newWidth = Math.max(cellWidth.value, dragStartWidth.value + deltaX);
    const newDuration = Math.round(newWidth / cellWidth.value);
    const newEnd = new Date(dragStartDate.value!);
    newEnd.setDate(newEnd.getDate() + newDuration);

    dragTask.value.end = newEnd;
    dragTask.value.duration = newDuration;
  } else if (dragType.value === "resize-left") {
    const newWidth = Math.max(cellWidth.value, dragStartWidth.value - deltaX);
    const newDuration = Math.round(newWidth / cellWidth.value);
    const newStart = new Date(dragEndDate.value!);
    newStart.setDate(newStart.getDate() - newDuration);

    dragTask.value.start = newStart;
    dragTask.value.duration = newDuration;
  }
}

function handleMouseUp() {
  if (isDragging.value && dragTask.value) {
    const updates: Record<string, unknown> = {};

    if (startDateFieldId.value) {
      updates[startDateFieldId.value] = dragTask.value.start.getTime();
    }
    if (endDateFieldId.value) {
      updates[endDateFieldId.value] = dragTask.value.end.getTime();
    }

    emit("updateRecord", dragTask.value.id, updates);
  }

  isDragging.value = false;
  dragTask.value = null;

  document.removeEventListener("mousemove", handleMouseMove);
  document.removeEventListener("mouseup", handleMouseUp);
}

const dependencyLines = computed<DependencyLine[]>(() => {
  const lines: DependencyLine[] = [];

  if (!timelineRef.value) return lines;

  const taskElements = timelineRef.value.querySelectorAll(".task-bar");
  const taskPositions = new Map<
    string,
    { x: number; y: number; width: number }
  >();

  taskElements.forEach((el, index) => {
    const task = tasks.value[index];
    if (task) {
      const rect = el.getBoundingClientRect();
      const parentRect = timelineRef.value!.getBoundingClientRect();
      taskPositions.set(task.id, {
        x: rect.left - parentRect.left,
        y: rect.top - parentRect.top + rect.height / 2,
        width: rect.width,
      });
    }
  });

  tasks.value.forEach((task) => {
    task.dependencies.forEach((depId) => {
      const fromPos = taskPositions.get(depId);
      const toPos = taskPositions.get(task.id);

      if (fromPos && toPos) {
        lines.push({
          fromX: fromPos.x + fromPos.width,
          fromY: fromPos.y,
          toX: toPos.x,
          toY: toPos.y,
        });
      }
    });
  });

  return lines;
});

function goToToday() {
  currentDate.value = new Date();
}

function zoomIn() {
  if (viewMode.value === "month") {
    viewMode.value = "week";
  } else if (viewMode.value === "week") {
    viewMode.value = "day";
  }
}

function zoomOut() {
  if (viewMode.value === "day") {
    viewMode.value = "week";
  } else if (viewMode.value === "week") {
    viewMode.value = "month";
  }
}

onMounted(() => {
  if (dateFields.value.length > 0) {
    startDateFieldId.value = dateFields.value[0].id;
    if (dateFields.value.length > 1) {
      endDateFieldId.value = dateFields.value[1].id;
    }
  }

  // 设置横向滚动同步
  setupScrollSync();
});

function setupScrollSync() {
  const contentEl = ganttContentRef.value;
  const headerEl = headerRightWrapperRef.value;

  if (!contentEl || !headerEl) return;

  // 内容区域滚动时同步表头
  contentEl.addEventListener("scroll", () => {
    headerEl.scrollLeft = contentEl.scrollLeft;
  });
}

watch(
  () => props.records,
  () => {
    nextTick(() => {
      // Force recompute dependency lines after DOM update
    });
  },
  { deep: true },
);
</script>

<template>
  <div class="gantt-view">
    <div class="gantt-toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="startDateFieldId"
          placeholder="开始日期字段"
          class="field-select">
          <template #prefix>
            <el-icon><Calendar /></el-icon>
          </template>
          <el-option
            v-for="field in dateFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
        <el-select
          v-model="endDateFieldId"
          placeholder="结束日期字段"
          class="field-select">
          <template #prefix>
            <el-icon><Calendar /></el-icon>
          </template>
          <el-option
            v-for="field in dateFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
        <el-select
          v-model="titleFieldId"
          placeholder="标题字段"
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
        <el-select
          v-model="progressFieldId"
          placeholder="进度字段"
          class="field-select"
          clearable>
          <template #prefix>
            <el-icon><DataAnalysis /></el-icon>
          </template>
          <el-option
            v-for="field in progressFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
      </div>

      <div class="toolbar-center">
        <div class="nav-button-group">
          <button class="nav-btn" @click="zoomOut">
            <el-icon><ZoomOut /></el-icon>
          </button>
          <button class="nav-btn today-btn" @click="goToToday">今天</button>
          <button class="nav-btn" @click="zoomIn">
            <el-icon><ZoomIn /></el-icon>
          </button>
        </div>
      </div>

      <div class="toolbar-right">
        <div class="view-switcher">
          <button
            class="view-btn"
            :class="{ active: viewMode === 'day' }"
            @click="viewMode = 'day'">
            日
          </button>
          <button
            class="view-btn"
            :class="{ active: viewMode === 'week' }"
            @click="viewMode = 'week'">
            周
          </button>
          <button
            class="view-btn"
            :class="{ active: viewMode === 'month' }"
            @click="viewMode = 'month'">
            月
          </button>
        </div>
      </div>
    </div>

    <div class="gantt-body">
      <!-- 表头 -->
      <div class="gantt-header">
        <div class="header-left">
          <div class="task-header">任务名称</div>
        </div>
        <div class="header-right-wrapper" ref="headerRightWrapperRef">
          <div class="header-right" :style="{ width: `${timelineWidth}px` }">
            <!-- 月份标签 -->
            <div class="month-header">
              <div
                v-for="(day, dayIndex) in timeline"
                :key="`month-${day.getTime()}`"
                v-show="isFirstDayOfMonth(day) || dayIndex === 0"
                class="month-cell"
                :style="{ left: `${dayIndex * cellWidth}px` }">
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
                  weekend: isWeekend(day),
                }"
                :style="{ width: `${cellWidth}px` }">
                <span class="day-number">{{ day.getDate() }}</span>
                <span class="day-week">{{
                  ["日", "一", "二", "三", "四", "五", "六"][day.getDay()]
                }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 内容区域 -->
      <div class="gantt-content" ref="ganttContentRef">
        <!-- 任务列表 -->
        <div class="task-list">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="task-row"
            @click="handleTaskClick(task)">
            <div class="task-info">
              <div class="task-name" :title="task.title">{{ task.title }}</div>
              <div class="task-date">
                {{ formatDate(task.start) }} - {{ formatDate(task.end) }}
              </div>
            </div>
          </div>
          <div v-if="tasks.length === 0" class="empty-tasks">
            <el-empty description="暂无任务数据" :image-size="80" />
          </div>
        </div>

        <!-- 时间线区域 -->
        <div
          ref="timelineRef"
          class="timeline-body"
          :style="{ width: `${timelineWidth}px` }">
          <!-- 背景网格 -->
          <div class="timeline-grid">
            <div
              v-for="day in timeline"
              :key="day.getTime()"
              class="grid-cell"
              :class="{
                today: isToday(day),
                weekend: isWeekend(day),
              }"
              :style="{ width: `${cellWidth}px` }" />
          </div>

          <!-- 当前日期指示线 -->
          <div
            v-if="
              isToday(new Date()) &&
              new Date() >= timelineStart &&
              new Date() <= timelineEnd
            "
            class="current-time-line"
            :style="{
              left: `${Math.floor((new Date().getTime() - timelineStart.getTime()) / (24 * 60 * 60 * 1000)) * cellWidth + cellWidth / 2}px`,
            }" />

          <!-- 依赖关系线条 -->
          <svg class="dependency-layer" v-if="dependencyLines.length > 0">
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto">
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
              marker-end="url(#arrowhead)" />
          </svg>

          <!-- 任务条 -->
          <div class="task-bars">
            <div
              v-for="(task, index) in tasks"
              :key="task.id"
              class="task-bar-wrapper"
              :style="getTaskRowStyle(index)">
              <div
                class="task-bar"
                :class="{
                  'is-dragging': isDragging && dragTask?.id === task.id,
                  'is-hovered': hoveredTask?.id === task.id,
                }"
                :style="getTaskStyle(task)"
                @mousedown="(e) => handleMouseDown(e, task, 'move')"
                @click.stop="handleTaskClick(task)"
                @mouseenter="hoveredTask = task"
                @mouseleave="hoveredTask = null">
                <!-- 左侧调整手柄 -->
                <div
                  class="resize-handle resize-left"
                  @mousedown.stop="
                    (e) => handleMouseDown(e, task, 'resize-left')
                  " />

                <!-- 进度条 -->
                <div
                  class="bar-progress"
                  :style="{ width: `${task.progress}%` }" />

                <!-- 任务标题 -->
                <span class="bar-title">{{ task.title }}</span>

                <!-- 右侧调整手柄 -->
                <div
                  class="resize-handle resize-right"
                  @mousedown.stop="
                    (e) => handleMouseDown(e, task, 'resize-right')
                  " />
              </div>

              <!-- 悬停详情卡片 -->
              <div
                v-if="hoveredTask?.id === task.id && !isDragging"
                class="task-tooltip"
                :style="{ left: `${getTaskStyle(task).left}` }">
                <div class="tooltip-header">{{ task.title }}</div>
                <div class="tooltip-body">
                  <div class="tooltip-row">
                    <span class="tooltip-label">开始:</span>
                    <span class="tooltip-value">{{
                      formatDate(task.start)
                    }}</span>
                  </div>
                  <div class="tooltip-row">
                    <span class="tooltip-label">结束:</span>
                    <span class="tooltip-value">{{
                      formatDate(task.end)
                    }}</span>
                  </div>
                  <div class="tooltip-row">
                    <span class="tooltip-label">进度:</span>
                    <span class="tooltip-value">{{ task.progress }}%</span>
                  </div>
                  <div class="tooltip-progress-bar">
                    <div
                      class="tooltip-progress-fill"
                      :style="{ width: `${task.progress}%` }" />
                  </div>
                </div>
              </div>

              <!-- 依赖关系指示器 -->
              <div
                v-if="task.dependencies.length > 0"
                class="dependency-indicator"
                :title="`依赖: ${task.dependencies.length} 个任务`">
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
@use "@/assets/styles/variables" as *;

.gantt-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background-color: $bg-color;
  overflow: hidden;
}

.gantt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  background: rgba($surface-color, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba($border-color, 0.6);
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
}

// 导航按钮组 - 圆角设计
.nav-button-group {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  background: $gray-100;
  padding: 3px;
  border-radius: $border-radius-lg;

  .nav-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    color: $text-secondary;
    border-radius: $border-radius-md;
    cursor: pointer;
    transition: all $transition-fast;

    &:hover {
      background: $surface-color;
      color: $primary-color;
      box-shadow: $shadow-sm;
    }

    &:active {
      transform: scale(0.95);
    }

    &.today-btn {
      width: auto;
      padding: 0 $spacing-md;
      font-size: $font-size-sm;
      font-weight: 500;
    }
  }
}

// 视图切换器 - 分段控制器样式
.view-switcher {
  display: flex;
  align-items: center;
  background: $gray-100;
  padding: 3px;
  border-radius: $border-radius-lg;

  .view-btn {
    padding: $spacing-xs $spacing-lg;
    border: none;
    background: transparent;
    color: $text-secondary;
    font-size: $font-size-sm;
    font-weight: 500;
    border-radius: $border-radius-md;
    cursor: pointer;
    transition: all $transition-fast;

    &:hover {
      color: $text-primary;
    }

    &.active {
      background: $surface-color;
      color: $primary-color;
      box-shadow: $shadow-sm;
    }
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
  background: rgba($surface-color, 0.95);
  flex-shrink: 0;

  .header-left {
    width: 240px;
    min-width: 240px;
    border-right: 1px solid $border-color;
    flex-shrink: 0;
  }

  .header-right-wrapper {
    flex: 1;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
    -ms-overflow-style: none;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  .header-right {
    flex-shrink: 0;
  }
}

.task-header {
  padding: $spacing-sm $spacing-md;
  font-weight: 600;
  color: $text-primary;
  font-size: $font-size-sm;
}

.month-header {
  position: relative;
  height: 24px;
  border-bottom: 1px solid $border-color;
  background: $gray-50;
}

.month-cell {
  position: absolute;
  top: 0;
  padding: 4px 10px;
  font-size: $font-size-xs;
  color: $text-secondary;
  font-weight: 600;
  white-space: nowrap;
}

.timeline-header {
  display: flex;
  height: 44px;
}

.timeline-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4px 2px;
  font-size: $font-size-xs;
  color: $text-secondary;
  border-right: 1px solid $border-color;
  background: $surface-color;
  transition: all $transition-fast;

  .day-number {
    font-weight: 600;
    font-size: 13px;
  }

  .day-week {
    font-size: 10px;
    margin-top: 2px;
    opacity: 0.8;
  }

  &.today {
    background: linear-gradient(
      135deg,
      rgba($primary-color, 0.12) 0%,
      rgba($primary-color, 0.06) 100%
    );
    color: $primary-color;

    .day-number {
      font-weight: 700;
    }
  }

  &.weekend {
    background: rgba($gray-100, 0.8);
    color: $text-disabled;
  }
}

.gantt-content {
  flex: 1;
  display: flex;
  overflow-x: auto;
  overflow-y: auto;
}

.task-list {
  width: 240px;
  min-width: 240px;
  border-right: 1px solid $border-color;
  background: $surface-color;
  flex-shrink: 0;
  position: sticky;
  left: 0;
  z-index: 10;
}

.task-row {
  height: 48px;
  padding: $spacing-xs $spacing-md;
  border-bottom: 1px solid rgba($border-color, 0.6);
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: rgba($primary-color, 0.04);
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
  margin-top: 3px;
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
  transition: all $transition-fast;

  &.today {
    background: linear-gradient(
      180deg,
      rgba($primary-color, 0.06) 0%,
      rgba($primary-color, 0.02) 100%
    );
  }

  &.weekend {
    background: rgba($gray-100, 0.5);
  }
}

// 当前日期指示线 - 主色
.current-time-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(
    180deg,
    $primary-color 0%,
    rgba($primary-color, 0.3) 100%
  );
  z-index: 10;
  pointer-events: none;
  box-shadow: 0 0 8px rgba($primary-color, 0.4);

  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: -5px;
    width: 12px;
    height: 12px;
    background: $primary-color;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba($primary-color, 0.4);
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
  height: 48px;
  display: flex;
  align-items: center;
}

// 任务条样式 - 圆角6px，渐变色
.task-bar {
  position: absolute;
  height: 32px;
  background: linear-gradient(
    135deg,
    rgba($primary-color, 0.9) 0%,
    rgba($primary-color, 0.7) 100%
  );
  border-radius: 6px;
  cursor: grab;
  overflow: hidden;
  display: flex;
  align-items: center;
  transition: all $transition-normal;
  user-select: none;
  box-shadow: 0 2px 6px rgba($primary-color, 0.25);

  &:hover {
    box-shadow: 0 4px 12px rgba($primary-color, 0.35);
    z-index: 10;
    transform: translateY(-1px);
  }

  &.is-dragging {
    cursor: grabbing;
    box-shadow: 0 6px 20px rgba($primary-color, 0.45);
    z-index: 20;
    opacity: 0.9;
    transform: scale(1.02);
  }

  &.is-hovered {
    box-shadow: 0 4px 14px rgba($primary-color, 0.4);
  }
}

.resize-handle {
  position: absolute;
  top: 0;
  width: 10px;
  height: 100%;
  cursor: col-resize;
  opacity: 0;
  transition: all $transition-fast;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;

  &::after {
    content: "";
    width: 3px;
    height: 14px;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 2px;
  }

  &:hover {
    opacity: 1;
    background: rgba(255, 255, 255, 0.15);
  }

  &.resize-left {
    left: 0;
    border-radius: 6px 0 0 6px;
  }

  &.resize-right {
    right: 0;
    border-radius: 0 6px 6px 0;
  }
}

.task-bar:hover .resize-handle {
  opacity: 0.6;
}

.bar-progress {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.25) 0%,
    rgba(255, 255, 255, 0.1) 100%
  );
  transition: width 0.3s ease;
}

.bar-title {
  position: relative;
  z-index: 1;
  display: block;
  padding: 4px 10px;
  font-size: $font-size-xs;
  color: white;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

// 悬停详情卡片
.task-tooltip {
  position: absolute;
  top: -95px;
  left: 0;
  min-width: 180px;
  background: $surface-color;
  border-radius: $border-radius-lg;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  padding: $spacing-md;
  z-index: 100;
  pointer-events: none;
  animation: tooltipFadeIn 0.2s ease;

  &::after {
    content: "";
    position: absolute;
    bottom: -6px;
    left: 20px;
    width: 12px;
    height: 12px;
    background: $surface-color;
    transform: rotate(45deg);
  }
}

@keyframes tooltipFadeIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tooltip-header {
  font-weight: 600;
  font-size: $font-size-sm;
  color: $text-primary;
  margin-bottom: $spacing-sm;
  padding-bottom: $spacing-xs;
  border-bottom: 1px solid $border-color;
}

.tooltip-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  font-size: $font-size-xs;
}

.tooltip-label {
  color: $text-secondary;
}

.tooltip-value {
  color: $text-primary;
  font-weight: 500;
}

.tooltip-progress-bar {
  height: 4px;
  background: $gray-200;
  border-radius: 2px;
  margin-top: 4px;
  overflow: hidden;
}

.tooltip-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, $primary-color 0%, $primary-hover 100%);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.dependency-indicator {
  position: absolute;
  right: -24px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-secondary;
  font-size: $font-size-xs;
  background: $gray-100;
  border-radius: 50%;
  transition: all $transition-fast;

  &:hover {
    color: $primary-color;
    background: rgba($primary-color, 0.1);
  }
}
</style>
