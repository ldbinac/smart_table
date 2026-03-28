<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";

interface Props {
  tableId: string;
  viewId: string;
  fields: FieldEntity[];
  records: RecordEntity[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "updateRecord", recordId: string, values: Record<string, unknown>): void;
  (e: "addRecord", values: Record<string, unknown>): void;
  (e: "deleteRecord", recordId: string): void;
  (e: "editRecord", recordId: string): void;
}>();

const dateFieldId = ref<string>("");
const endDateFieldId = ref<string>("");
const titleFieldId = ref<string>("");
const currentView = ref<"month" | "week" | "day">("month");
const currentDate = ref(new Date());

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

const titleField = computed(() => {
  if (titleFieldId.value) {
    return props.fields.find((f) => f.id === titleFieldId.value);
  }
  // 默认使用第一个字段（主字段或第一个可用字段）
  return props.fields.find((f) => f.isPrimary) || props.fields[0];
});

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end?: Date;
  allDay: boolean;
  record: RecordEntity;
  color?: string;
}

const events = computed<CalendarEvent[]>(() => {
  if (!dateFieldId.value) return [];

  return props.records
    .filter((record) => record.values[dateFieldId.value])
    .map((record) => {
      const startValue = record.values[dateFieldId.value];
      const endValue = endDateFieldId.value
        ? record.values[endDateFieldId.value]
        : null;
      const titleValue = titleField.value
        ? record.values[titleField.value!.id]
        : "";

      // 支持多种日期格式：数字时间戳、ISO字符串、Date对象
      const start = parseDateValue(startValue);
      const end = endValue ? parseDateValue(endValue) : undefined;

      return {
        id: record.id,
        title: String(titleValue || "无标题"),
        start: start!,
        end: end || undefined,
        allDay: true,
        record,
        color: "#3370FF",
      };
    })
    .filter((event) => event.start && !isNaN(event.start.getTime()));
});

// 解析日期值，支持数字时间戳、ISO字符串、Date对象
function parseDateValue(value: unknown): Date | null {
  if (!value) return null;

  // 如果是数字，直接作为时间戳
  if (typeof value === "number") {
    return new Date(value);
  }

  // 如果是字符串，可能是ISO格式或数字字符串
  if (typeof value === "string") {
    // 尝试解析为数字时间戳
    const numValue = Number(value);
    if (!isNaN(numValue) && value.trim() !== "") {
      return new Date(numValue);
    }
    // 否则作为ISO字符串解析
    const date = new Date(value);
    if (!isNaN(date.getTime())) {
      return date;
    }
  }

  // 如果已经是Date对象
  if (value instanceof Date) {
    return value;
  }

  return null;
}

const weekDays = ["日", "一", "二", "三", "四", "五", "六"];

const calendarDays = computed(() => {
  const year = currentDate.value.getFullYear();
  const month = currentDate.value.getMonth();

  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);

  const days: Array<{
    date: Date;
    isCurrentMonth: boolean;
    isToday: boolean;
    events: CalendarEvent[];
  }> = [];

  const startPadding = firstDay.getDay();
  for (let i = startPadding - 1; i >= 0; i--) {
    const date = new Date(year, month, -i);
    days.push({
      date,
      isCurrentMonth: false,
      isToday: isSameDay(date, new Date()),
      events: getEventsForDate(date),
    });
  }

  for (let i = 1; i <= lastDay.getDate(); i++) {
    const date = new Date(year, month, i);
    days.push({
      date,
      isCurrentMonth: true,
      isToday: isSameDay(date, new Date()),
      events: getEventsForDate(date),
    });
  }

  const endPadding = 42 - days.length;
  for (let i = 1; i <= endPadding; i++) {
    const date = new Date(year, month + 1, i);
    days.push({
      date,
      isCurrentMonth: false,
      isToday: isSameDay(date, new Date()),
      events: getEventsForDate(date),
    });
  }

  return days;
});

const currentMonthYear = computed(() => {
  return `${currentDate.value.getFullYear()}年${currentDate.value.getMonth() + 1}月`;
});

function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
}

function getEventsForDate(date: Date): CalendarEvent[] {
  return events.value.filter((event) => {
    const eventStart = new Date(event.start);
    eventStart.setHours(0, 0, 0, 0);

    const checkDate = new Date(date);
    checkDate.setHours(0, 0, 0, 0);

    if (event.end) {
      const eventEnd = new Date(event.end);
      eventEnd.setHours(23, 59, 59, 999);
      return checkDate >= eventStart && checkDate <= eventEnd;
    }

    return isSameDay(eventStart, checkDate);
  });
}

function prevMonth() {
  currentDate.value = new Date(
    currentDate.value.getFullYear(),
    currentDate.value.getMonth() - 1,
    1,
  );
}

function nextMonth() {
  currentDate.value = new Date(
    currentDate.value.getFullYear(),
    currentDate.value.getMonth() + 1,
    1,
  );
}

function goToToday() {
  currentDate.value = new Date();
}

function handleEventClick(event: CalendarEvent) {
  emit("editRecord", event.id);
}

function handleDateClick(date: Date) {
  const newDate = date.getTime();
  emit("addRecord", { [dateFieldId.value]: newDate });
}

onMounted(() => {
  if (dateFields.value.length > 0) {
    dateFieldId.value = dateFields.value[0].id;
  }
  // 默认使用第一个字段作为标题字段
  if (props.fields.length > 0 && !titleFieldId.value) {
    titleFieldId.value = props.fields[0].id;
  }
});
</script>

<template>
  <div class="calendar-view">
    <div class="calendar-toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="dateFieldId"
          placeholder="选择日期字段"
          class="field-select">
          <el-option
            v-for="field in dateFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
        <el-select
          v-model="titleFieldId"
          placeholder="选择标题字段"
          class="field-select">
          <el-option
            v-for="field in titleFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
      </div>

      <div class="toolbar-center">
        <div class="nav-button-group">
          <button class="nav-btn" @click="prevMonth">
            <el-icon><ArrowLeft /></el-icon>
          </button>
          <button class="nav-btn today-btn" @click="goToToday">今天</button>
          <button class="nav-btn" @click="nextMonth">
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>
        <span class="current-month">{{ currentMonthYear }}</span>
      </div>

      <div class="toolbar-right">
        <div class="view-switcher">
          <button
            class="view-btn"
            :class="{ active: currentView === 'month' }"
            @click="currentView = 'month'">
            月
          </button>
          <button
            class="view-btn"
            :class="{ active: currentView === 'week' }"
            @click="currentView = 'week'">
            周
          </button>
          <button
            class="view-btn"
            :class="{ active: currentView === 'day' }"
            @click="currentView = 'day'">
            日
          </button>
        </div>
      </div>
    </div>

    <div class="calendar-body">
      <div class="calendar-header">
        <div v-for="day in weekDays" :key="day" class="weekday-cell">
          {{ day }}
        </div>
      </div>

      <div class="calendar-grid">
        <div
          v-for="(day, index) in calendarDays"
          :key="index"
          class="calendar-cell"
          :class="{
            'other-month': !day.isCurrentMonth,
            today: day.isToday,
          }"
          @click="handleDateClick(day.date)">
          <div class="cell-header">
            <span class="day-number">{{ day.date.getDate() }}</span>
          </div>
          <div class="cell-events">
            <div
              v-for="event in day.events.slice(0, 3)"
              :key="event.id"
              class="event-item"
              :style="{ borderLeftColor: event.color }"
              @click.stop="handleEventClick(event)">
              {{ event.title }}
            </div>
            <div v-if="day.events.length > 3" class="more-events">
              +{{ day.events.length - 3 }} 更多
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.calendar-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-color;
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  background: rgba($surface-color, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba($border-color, 0.6);

  .field-select {
    width: 150px;
    margin-right: $spacing-sm;
  }

  .toolbar-center {
    display: flex;
    align-items: center;
    gap: $spacing-lg;
  }

  .current-month {
    font-size: $font-size-xl;
    font-weight: 600;
    color: $text-primary;
    letter-spacing: -0.5px;
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

.calendar-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: $spacing-md;
}

.calendar-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: $spacing-sm;
  padding: 0 $spacing-xs;

  .weekday-cell {
    padding: $spacing-sm;
    text-align: center;
    font-weight: 500;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.calendar-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-template-rows: repeat(6, 1fr);
  gap: $spacing-xs;
  overflow: auto;
}

.calendar-cell {
  min-height: 100px;
  padding: $spacing-xs;
  background: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-lg;
  cursor: pointer;
  transition: all $transition-fast;

  &.other-month {
    background: rgba($surface-color, 0.6);

    .day-number {
      color: $text-disabled;
    }
  }

  &.today {
    background: linear-gradient(135deg, rgba($primary-color, 0.08) 0%, rgba($primary-color, 0.03) 100%);
    border-color: rgba($primary-color, 0.3);
    box-shadow: 0 0 0 1px rgba($primary-color, 0.1);

    .day-number {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 24px;
      height: 24px;
      padding: 0 6px;
      background: $primary-color;
      color: white;
      border-radius: $border-radius-md;
      font-weight: 600;
      box-shadow: 0 2px 8px rgba($primary-color, 0.35);
    }
  }

  &:hover {
    border-color: rgba($primary-color, 0.4);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-1px);
  }
}

.cell-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: $spacing-xs;
}

.day-number {
  font-size: $font-size-sm;
  color: $text-primary;
  font-weight: 500;
}

.cell-events {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.event-item {
  padding: 4px 8px;
  font-size: $font-size-xs;
  color: $text-primary;
  background: linear-gradient(135deg, rgba($primary-color, 0.12) 0%, rgba($primary-color, 0.06) 100%);
  border-left: 3px solid $primary-color;
  border-radius: $border-radius-md;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: all $transition-fast;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);

  &:hover {
    background: linear-gradient(135deg, rgba($primary-color, 0.2) 0%, rgba($primary-color, 0.1) 100%);
    transform: translateX(2px);
    box-shadow: 0 2px 6px rgba($primary-color, 0.15);
  }
}

.more-events {
  padding: 3px 8px;
  font-size: $font-size-xs;
  color: $text-secondary;
  cursor: pointer;
  border-radius: $border-radius-sm;
  transition: all $transition-fast;

  &:hover {
    color: $primary-color;
    background: rgba($primary-color, 0.08);
  }
}
</style>
