<script setup lang="ts">
import { ref, computed, onMounted, watch, onBeforeUnmount } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";
import { ArrowLeft, ArrowRight, Clock, Calendar, EditPen } from "@element-plus/icons-vue";
import { FormulaEngine } from "@/utils/formula/engine";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { realtimeEventEmitter } from "@/services/realtime/eventEmitter";
import type {
  DataRecordUpdatedBroadcast,
  DataRecordCreatedBroadcast,
  DataRecordDeletedBroadcast,
} from "@/services/realtime/eventTypes";

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

const dateFieldId = ref<string>("");
const endDateFieldId = ref<string>("");
const titleFieldId = ref<string>("");
const currentView = ref<"month" | "week" | "day">("month");
const currentDate = ref(new Date());

// 时间刻度（用于日视图和周视图）
const timeSlots = computed(() => {
  const slots = [];
  for (let i = 0; i < 24; i++) {
    slots.push(i);
  }
  return slots;
});

const dateFields = computed(() => {
  return props.fields.filter(
    (f) =>
      f.type === FieldType.DATE ||
      f.type === FieldType.CREATED_TIME ||
      f.type === FieldType.UPDATED_TIME,
  );
});

// 关联字段
const linkFields = computed(() => {
  return props.fields.filter((f) => f.type === FieldType.LINK);
});

// 获取记录的关联字段显示文本
const getRecordLinkSummary = (record: RecordEntity): string => {
  if (linkFields.value.length === 0) return "";
  
  const linkField = linkFields.value[0]; // 显示第一个关联字段
  const linkedIds = record.values[linkField.id] as string[] | undefined;
  
  if (!linkedIds || linkedIds.length === 0) return "";
  
  return `[${linkedIds.length}]`;
};

const titleFields = computed(() => {
  return props.fields.filter(
    (f) =>
      f.type === FieldType.SINGLE_LINE_TEXT ||
      f.type === FieldType.NUMBER ||
      f.type === FieldType.SINGLE_SELECT,
  );
});

const titleField = computed(() => {
  if (titleFieldId.value) {
    return props.fields.find((f) => f.id === titleFieldId.value);
  }
  return props.fields.find((f) => f.isPrimary) || props.fields[0];
});

// 获取单选字段的显示文本
const getSingleSelectDisplay = (
  field: FieldEntity,
  value: string,
): { name: string; color: string } | null => {
  if (!field.options?.choices) return null;
  const options = field.options.choices as Array<{
    id: string;
    name: string;
    color: string;
  }>;
  return options.find((opt) => opt.id === value) || null;
};

// 获取记录标题（支持公式字段和单选字段）
const getRecordTitle = (record: RecordEntity): string => {
  const field = titleField.value;
  if (!field) return "无标题";

  // 如果是公式字段，实时计算
  if (field.type === FieldType.FORMULA) {
    const formula = field.options?.formula as string;
    if (formula && props.fields.length > 0) {
      try {
        const engine = new FormulaEngine(props.fields);
        const result = engine.calculate(record, formula);
        if (result !== "#ERROR") {
          return String(result);
        }
      } catch (error) {
        console.error("Calendar formula calculation error:", error);
      }
    }
    return "计算错误";
  }

  // 单选字段：返回选项名称而不是ID
  if (field.type === FieldType.SINGLE_SELECT) {
    const value = record.values[field.id];
    if (value === null || value === undefined) return "无标题";
    const option = getSingleSelectDisplay(field, String(value));
    return option?.name || String(value);
  }

  // 普通字段直接返回值
  const value = record.values[field.id];
  return value !== null && value !== undefined ? String(value) : "无标题";
};

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

  const titleFieldObj = titleField.value;

  return props.records
    .filter((record) => record.values[dateFieldId.value])
    .map((record) => {
      const startValue = record.values[dateFieldId.value];
      const endValue = endDateFieldId.value
        ? record.values[endDateFieldId.value]
        : null;
      const titleValue = titleFieldObj ? getRecordTitle(record) : "";

      const start = parseDateValue(startValue);
      const end = endValue ? parseDateValue(endValue) : undefined;

      if (!start || isNaN(start.getTime())) {
        return null as unknown as CalendarEvent;
      }

      return {
        id: record.id,
        title: String(titleValue || "无标题"),
        start: start,
        end: end || undefined,
        allDay: true,
        record,
        color: "#3B82F6",
      };
    })
    .filter(
      (event): event is CalendarEvent =>
        event !== null && event.start && !isNaN(event.start.getTime()),
    );
});

function parseDateValue(value: unknown): Date | null {
  if (!value) return null;

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

  return null;
}

const weekDays = ["日", "一", "二", "三", "四", "五", "六"];
const weekDaysFull = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

// ========== 月视图计算属性 ==========
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

  // 计算月初前面的填充天数（上月日期）
  const startPadding = firstDay.getDay(); // 0-6，0是周日
  for (let i = startPadding - 1; i >= 0; i--) {
    const date = new Date(year, month, -i);
    days.push({
      date,
      isCurrentMonth: false,
      isToday: isSameDay(date, new Date()),
      events: getEventsForDate(date),
    });
  }

  // 当月日期
  for (let i = 1; i <= lastDay.getDate(); i++) {
    const date = new Date(year, month, i);
    days.push({
      date,
      isCurrentMonth: true,
      isToday: isSameDay(date, new Date()),
      events: getEventsForDate(date),
    });
  }

  // 计算月末后面的填充天数（下月日期）
  // 动态计算所需行数：最少4行，最多6行，根据实际日期分布决定
  const totalDaysNeeded = Math.ceil(days.length / 7) * 7;
  const endPadding = totalDaysNeeded - days.length;

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

// 计算月视图需要的行数（用于动态设置网格行数）
const monthViewRowCount = computed(() => {
  return Math.ceil(calendarDays.value.length / 7);
});

// ========== 周视图计算属性 ==========
const weekDaysData = computed(() => {
  const startOfWeek = getStartOfWeek(currentDate.value);
  const days = [];

  for (let i = 0; i < 7; i++) {
    const date = new Date(startOfWeek);
    date.setDate(startOfWeek.getDate() + i);
    days.push({
      date,
      isToday: isSameDay(date, new Date()),
      events: getEventsForDate(date),
    });
  }

  return days;
});

const currentWeekRange = computed(() => {
  const startOfWeek = getStartOfWeek(currentDate.value);
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);

  const startMonth = startOfWeek.getMonth() + 1;
  const startDay = startOfWeek.getDate();
  const endMonth = endOfWeek.getMonth() + 1;
  const endDay = endOfWeek.getDate();
  const year = startOfWeek.getFullYear();

  if (startMonth === endMonth) {
    return `${year}年${startMonth}月${startDay}日 - ${endDay}日`;
  } else {
    return `${year}年${startMonth}月${startDay}日 - ${endMonth}月${endDay}日`;
  }
});

// ========== 日视图计算属性 ==========
const currentDayData = computed(() => {
  return {
    date: currentDate.value,
    isToday: isSameDay(currentDate.value, new Date()),
    events: getEventsForDate(currentDate.value),
  };
});

const currentDayTitle = computed(() => {
  const year = currentDate.value.getFullYear();
  const month = currentDate.value.getMonth() + 1;
  const day = currentDate.value.getDate();
  const weekDay = weekDaysFull[currentDate.value.getDay()];
  return `${year}年${month}月${day}日 ${weekDay}`;
});

// ========== 标题计算属性 ==========
const currentTitle = computed(() => {
  switch (currentView.value) {
    case "month":
      return `${currentDate.value.getFullYear()}年${currentDate.value.getMonth() + 1}月`;
    case "week":
      return currentWeekRange.value;
    case "day":
      return currentDayTitle.value;
    default:
      return "";
  }
});

function isSameDay(
  date1: Date | string | number,
  date2: Date | string | number,
): boolean {
  const d1 = date1 instanceof Date ? date1 : new Date(date1);
  const d2 = date2 instanceof Date ? date2 : new Date(date2);

  if (isNaN(d1.getTime()) || isNaN(d2.getTime())) {
    return false;
  }

  return (
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate()
  );
}

function getStartOfWeek(date: Date): Date {
  if (!date || isNaN(date.getTime())) {
    return new Date();
  }
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day;
  return new Date(d.setDate(diff));
}

function getEventsForDate(date: Date): CalendarEvent[] {
  if (!date || isNaN(date.getTime())) return [];

  return events.value.filter((event) => {
    if (!event.start) return false;

    const eventStart =
      event.start instanceof Date ? event.start : new Date(event.start);
    if (isNaN(eventStart.getTime())) return false;

    const eventStartDay = new Date(eventStart);
    eventStartDay.setHours(0, 0, 0, 0);

    const checkDate = new Date(date);
    checkDate.setHours(0, 0, 0, 0);

    if (event.end) {
      const eventEnd =
        event.end instanceof Date ? event.end : new Date(event.end);
      if (!isNaN(eventEnd.getTime())) {
        const eventEndDay = new Date(eventEnd);
        eventEndDay.setHours(23, 59, 59, 999);
        return checkDate >= eventStartDay && checkDate <= eventEndDay;
      }
    }

    return isSameDay(eventStart, checkDate);
  });
}

// ========== 导航方法 ==========
function prev() {
  switch (currentView.value) {
    case "month":
      currentDate.value = new Date(
        currentDate.value.getFullYear(),
        currentDate.value.getMonth() - 1,
        1,
      );
      break;
    case "week":
      currentDate.value = new Date(
        currentDate.value.getFullYear(),
        currentDate.value.getMonth(),
        currentDate.value.getDate() - 7,
      );
      break;
    case "day":
      currentDate.value = new Date(
        currentDate.value.getFullYear(),
        currentDate.value.getMonth(),
        currentDate.value.getDate() - 1,
      );
      break;
  }
}

function next() {
  switch (currentView.value) {
    case "month":
      currentDate.value = new Date(
        currentDate.value.getFullYear(),
        currentDate.value.getMonth() + 1,
        1,
      );
      break;
    case "week":
      currentDate.value = new Date(
        currentDate.value.getFullYear(),
        currentDate.value.getMonth(),
        currentDate.value.getDate() + 7,
      );
      break;
    case "day":
      currentDate.value = new Date(
        currentDate.value.getFullYear(),
        currentDate.value.getMonth(),
        currentDate.value.getDate() + 1,
      );
      break;
  }
}

function goToToday() {
  currentDate.value = new Date();
}

function handleEventClick(event: CalendarEvent) {
  emit("editRecord", event.id);
}

function handleDateClick(date: Date) {
  if (props.readonly) return;
  const newDate = date.getTime();
  emit("addRecord", { [dateFieldId.value]: newDate });
}

function handleViewChange(view: "month" | "week" | "day") {
  currentView.value = view;
}

function formatTime(date: Date | string | number): string {
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) {
    return "--:--";
  }
  const hours = d.getHours().toString().padStart(2, "0");
  const minutes = d.getMinutes().toString().padStart(2, "0");
  return `${hours}:${minutes}`;
}

function getEventTimePosition(event: CalendarEvent): {
  top: number;
  height: number;
} {
  const start =
    event.start instanceof Date ? event.start : new Date(event.start);
  if (isNaN(start.getTime())) {
    return { top: 0, height: 60 };
  }

  const hour = start.getHours();
  const minute = start.getMinutes();
  const top = hour * 60 + minute;

  let height = 60;
  if (event.end) {
    const end = event.end instanceof Date ? event.end : new Date(event.end);
    if (!isNaN(end.getTime())) {
      const duration = (end.getTime() - start.getTime()) / (1000 * 60);
      height = Math.max(duration, 30);
    }
  }

  return { top, height };
}

// 初始化日期字段选择
function initDateField() {
  if (!dateFieldId.value && dateFields.value.length > 0) {
    dateFieldId.value = dateFields.value[0].id;
  }
}

// 初始化标题字段选择
function initTitleField() {
  if (!titleFieldId.value && props.fields.length > 0) {
    // 优先选择主字段，如果没有则选择第一个文本字段
    const primaryField = props.fields.find((f) => f.isPrimary);
    const textField = props.fields.find(
      (f) => f.type === FieldType.SINGLE_LINE_TEXT || f.type === FieldType.SINGLE_SELECT,
    );
    titleFieldId.value =
      primaryField?.id || textField?.id || props.fields[0]?.id || "";
  }
}

onMounted(() => {
  initDateField();
  initTitleField();
  setupRealtimeListenersForView();
});

onBeforeUnmount(() => {
  cleanupRealtimeListenersForView();
});

const collabStore = useCollaborationStore();
const realtimeHandlers: Array<{ event: string; handler: (...args: unknown[]) => void }> = [];

function setupRealtimeListenersForView() {
  if (!collabStore.isRealtimeAvailable) return;

  const onRecordUpdated = (data: DataRecordUpdatedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    const index = props.records.findIndex((r) => r.id === data.record_id);
    if (index !== -1) {
      const existing = props.records[index];
      const updatedValues = { ...existing.values };
      for (const change of data.changes) {
        updatedValues[change.field_id] = change.new_value;
      }
      Object.assign(props.records[index], { values: updatedValues, updatedAt: Date.now() });
    }
  };

  const onRecordCreated = (data: DataRecordCreatedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    const record = data.record as unknown as RecordEntity;
    if (record && !props.records.find((r) => r.id === record.id)) {
      props.records.push(record);
    }
  };

  const onRecordDeleted = (data: DataRecordDeletedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    const idx = props.records.findIndex((r) => r.id === data.record_id);
    if (idx !== -1) props.records.splice(idx, 1);
  };

  realtimeEventEmitter.on("data:record_updated", onRecordUpdated);
  realtimeEventEmitter.on("data:record_created", onRecordCreated);
  realtimeEventEmitter.on("data:record_deleted", onRecordDeleted);

  realtimeHandlers.push(
    { event: "data:record_updated", handler: onRecordUpdated as (...args: unknown[]) => void },
    { event: "data:record_created", handler: onRecordCreated as (...args: unknown[]) => void },
    { event: "data:record_deleted", handler: onRecordDeleted as (...args: unknown[]) => void },
  );
}

function cleanupRealtimeListenersForView() {
  for (const { event, handler } of realtimeHandlers) {
    realtimeEventEmitter.off(event as any, handler as any);
  }
  realtimeHandlers.length = 0;
}

// 监听 fields 变化，自动初始化选择
watch(
  () => props.fields,
  () => {
    initDateField();
    initTitleField();
  },
  { immediate: true },
);

// 监听 dateFields 变化，如果没有选择则自动选择第一个
watch(
  dateFields,
  (newDateFields) => {
    if (!dateFieldId.value && newDateFields.length > 0) {
      dateFieldId.value = newDateFields[0].id;
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="calendar-view">
    <!-- 工具栏 -->
    <div class="calendar-toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="dateFieldId"
          placeholder="选择日期字段"
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
          placeholder="选择标题字段"
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
      </div>

      <div class="toolbar-center">
        <div class="nav-button-group">
          <button class="nav-btn" @click="prev">
            <el-icon><ArrowLeft /></el-icon>
          </button>
          <button class="nav-btn today-btn" @click="goToToday">今天</button>
          <button class="nav-btn" @click="next">
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>
        <span class="current-title">{{ currentTitle }}</span>
      </div>

      <div class="toolbar-right">
        <div class="view-switcher">
          <button
            class="view-btn"
            :class="{ active: currentView === 'month' }"
            @click="handleViewChange('month')">
            月
          </button>
          <button
            class="view-btn"
            :class="{ active: currentView === 'week' }"
            @click="handleViewChange('week')">
            周
          </button>
          <button
            class="view-btn"
            :class="{ active: currentView === 'day' }"
            @click="handleViewChange('day')">
            日
          </button>
        </div>
      </div>
    </div>

    <!-- 月视图 -->
    <div v-if="currentView === 'month'" class="calendar-body month-view">
      <div class="calendar-header">
        <div v-for="day in weekDays" :key="day" class="weekday-cell">
          {{ day }}
        </div>
      </div>

      <div
        class="calendar-grid"
        :style="{ gridTemplateRows: `repeat(${monthViewRowCount}, 1fr)` }">
        <div
          v-for="(day, index) in calendarDays"
          :key="index"
          class="calendar-cell"
          :class="{
            'other-month': !day.isCurrentMonth,
            today: day.isToday,
            'has-more-events': day.events.length > 3,
          }"
          @click="handleDateClick(day.date)">
          <div class="cell-header">
            <span class="day-number"
              >{{ day.date.getMonth() + 1 }}.{{ day.date.getDate() }}</span
            >
          </div>
          <div class="cell-events">
            <div
              v-for="event in day.events.slice(0, 3)"
              :key="event.id"
              class="event-item"
              :style="{ borderLeftColor: event.color }"
              @click.stop="handleEventClick(event)">
              {{ event.title }} {{ getRecordLinkSummary(event.record) }}
            </div>
            <div v-if="day.events.length > 3" class="more-events">
              +{{ day.events.length - 3 }} 更多
            </div>
          </div>
          <!-- 悬停时显示所有事件的浮层 -->
          <div v-if="day.events.length > 0" class="events-tooltip">
            <div class="tooltip-header">
              <span class="tooltip-date"
                >{{ day.date.getMonth() + 1 }}月{{ day.date.getDate() }}日</span
              >
              <span class="tooltip-count">{{ day.events.length }} 个事件</span>
            </div>
            <div class="tooltip-events-list">
              <div
                v-for="event in day.events"
                :key="event.id"
                class="tooltip-event-item"
                :style="{ borderLeftColor: event.color }"
                @click.stop="handleEventClick(event)">
                {{ event.title }} {{ getRecordLinkSummary(event.record) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 周视图 -->
    <div v-else-if="currentView === 'week'" class="calendar-body week-view">
      <div class="week-header">
        <div class="time-column-header"></div>
        <div
          v-for="(day, index) in weekDaysData"
          :key="index"
          class="week-day-header"
          :class="{ today: day.isToday }"
          @click="handleDateClick(day.date)">
          <div class="weekday-name">{{ weekDaysFull[index] }}</div>
          <div class="weekday-date" :class="{ 'today-badge': day.isToday }">
            {{ day.date.getMonth() + 1 }}.{{ day.date.getDate() }}
          </div>
        </div>
      </div>

      <div class="week-grid">
        <div class="time-column">
          <div v-for="hour in timeSlots" :key="hour" class="time-slot">
            <span class="time-label"
              >{{ hour.toString().padStart(2, "0") }}:00</span
            >
          </div>
        </div>

        <div class="week-columns">
          <div
            v-for="(day, dayIndex) in weekDaysData"
            :key="dayIndex"
            class="week-day-column"
            :class="{ today: day.isToday }"
            @click="handleDateClick(day.date)">
            <div v-for="hour in timeSlots" :key="hour" class="hour-cell"></div>

            <div
              v-for="event in day.events"
              :key="event.id"
              class="week-event-item"
              :style="{
                borderLeftColor: event.color,
                top: `${getEventTimePosition(event).top}px`,
                height: `${Math.min(getEventTimePosition(event).height, 60)}px`,
              }"
              @click.stop="handleEventClick(event)">
              <div class="event-time">
                <el-icon><Clock /></el-icon>
                {{ formatTime(event.start) }}
              </div>
              <div class="event-title">{{ event.title }} {{ getRecordLinkSummary(event.record) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日视图 -->
    <div v-else-if="currentView === 'day'" class="calendar-body day-view">
      <div class="day-header" :class="{ today: currentDayData.isToday }">
        <div class="day-title">
          <span class="day-date">{{ currentDate.getDate() }}</span>
          <span class="day-info">
            <span class="day-weekday">{{
              weekDaysFull[currentDate.getDay()]
            }}</span>
            <span class="day-full-date">
              {{ currentDate.getFullYear() }}年{{
                currentDate.getMonth() + 1
              }}月
            </span>
          </span>
        </div>
        <div class="day-events-count">
          {{ currentDayData.events.length }} 个事件
        </div>
      </div>

      <div class="day-grid">
        <div class="time-column">
          <div v-for="hour in timeSlots" :key="hour" class="time-slot">
            <span class="time-label"
              >{{ hour.toString().padStart(2, "0") }}:00</span
            >
          </div>
        </div>

        <div class="day-content" @click="handleDateClick(currentDate)">
          <div v-for="hour in timeSlots" :key="hour" class="hour-cell"></div>

          <div
            v-for="event in currentDayData.events"
            :key="event.id"
            class="day-event-item"
            :style="{
              borderLeftColor: event.color,
              top: `${getEventTimePosition(event).top}px`,
              minHeight: `${Math.max(getEventTimePosition(event).height, 40)}px`,
            }"
            @click.stop="handleEventClick(event)">
            <div class="event-time">
              <el-icon><Clock /></el-icon>
              {{ formatTime(event.start) }}
              <span v-if="event.end" class="event-end-time">
                - {{ formatTime(event.end) }}
              </span>
            </div>
            <div class="event-title">{{ event.title }} {{ getRecordLinkSummary(event.record) }}</div>
          </div>

          <div v-if="currentDayData.events.length === 0" class="no-events">
            <el-empty description="暂无事件" :image-size="80">
              <template #description>
                <p>暂无事件</p>
                <p v-if="!readonly" class="sub-text">点击空白处添加新记录</p>
              </template>
            </el-empty>
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

// ========== 工具栏 ==========
.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  background: rgba($surface-color, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba($border-color, 0.6);
  flex-shrink: 0;

  .field-select {
    width: 160px;
    margin-right: $spacing-sm;

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

  .toolbar-center {
    display: flex;
    align-items: center;
    gap: $spacing-lg;
  }

  .current-title {
    font-size: $font-size-lg;
    font-weight: 600;
    color: $text-primary;
    letter-spacing: -0.3px;
    min-width: 200px;
    text-align: center;
  }
}

// 导航按钮组
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

// 视图切换器
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

// ========== 日历主体 ==========
.calendar-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: $spacing-md;
}

// ========== 月视图 ==========
.month-view {
  .calendar-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    margin-bottom: $spacing-md;
    padding: $spacing-md $spacing-xs;
    background: linear-gradient(135deg, $gray-100 0%, $gray-50 100%);
    border-radius: $border-radius-lg;
    border: 1px solid $border-color;

    .weekday-cell {
      padding: $spacing-sm $spacing-md;
      text-align: center;
      font-weight: 700;
      color: $text-secondary;
      font-size: $font-size-base;
      letter-spacing: 0.5px;
      text-transform: uppercase;

      // 周末特殊样式
      &:first-child,
      &:last-child {
        color: $primary-color;
        background: rgba($primary-color, 0.05);
        border-radius: $border-radius-md;
      }
    }
  }

  .calendar-grid {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    // grid-template-rows 由动态计算的 monthViewRowCount 决定
    gap: $spacing-xs;
    overflow: auto;
  }

  .calendar-cell {
    min-height: 90px;
    padding: 6px;
    background: $surface-color;
    border: 1px solid $border-color;
    border-radius: $border-radius-lg;
    cursor: pointer;
    transition: all $transition-fast;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: visible;

    &.other-month {
      background: rgba($surface-color, 0.5);

      .day-number {
        color: $text-disabled;
        font-weight: 400;
      }
    }

    &.today {
      background: rgba($primary-color, 0.12);
      border-color: $primary-color;
      border-width: 2px;

      .day-number {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 28px;
        background: $primary-color;
        color: white;
        border-radius: $border-radius-md;
        font-weight: 700;
        font-size: $font-size-base;
        box-shadow: 0 2px 8px rgba($primary-color, 0.35);
      }
    }

    &:hover {
      border-color: rgba($primary-color, 0.5);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
      transform: translateY(-2px);
      z-index: 10;

      .events-tooltip {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
      }
    }

    &.has-more-events:hover {
      z-index: 20;
    }
  }

  .cell-header {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 4px;
    flex-shrink: 0;
    height: 28px;
    line-height: 1;
    background-color: #cddcf461;
  }

  .day-number {
    font-size: $font-size-base;
    color: $text-primary;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    line-height: 1;
  }

  .cell-events {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    overflow: hidden;
    min-height: 0;
  }

  .event-item {
    padding: 3px 6px;
    font-size: 11px;
    color: $text-primary;
    background: linear-gradient(
      135deg,
      rgba($primary-color, 0.1) 0%,
      rgba($primary-color, 0.05) 100%
    );
    border-left: 2px solid $primary-color;
    border-radius: $border-radius-sm;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    transition: all $transition-fast;
    line-height: 1.3;

    &:hover {
      background: linear-gradient(
        135deg,
        rgba($primary-color, 0.18) 0%,
        rgba($primary-color, 0.08) 100%
      );
      transform: translateX(2px);
    }
  }

  .more-events {
    padding: 2px 6px;
    font-size: 10px;
    color: $text-secondary;
    cursor: pointer;
    border-radius: $border-radius-sm;
    transition: all $transition-fast;
    line-height: 1.3;

    &:hover {
      color: $primary-color;
      background: rgba($primary-color, 0.08);
    }
  }

  // 悬停显示所有事件的浮层
  .events-tooltip {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    min-width: 180px;
    max-width: 220px;
    background: $surface-color;
    border: 1px solid $border-color;
    border-radius: $border-radius-lg;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    padding: $spacing-md;
    z-index: 100;
    opacity: 0;
    visibility: hidden;
    transform: translateY(-4px);
    transition: all $transition-fast;

    // 防止超出视口右侧
    &.tooltip-right {
      left: auto;
      right: 0;
    }

    // 防止超出视口底部时的向上显示
    &.tooltip-top {
      top: auto;
      bottom: calc(100% + 4px);
    }

    .tooltip-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: $spacing-sm;
      padding-bottom: $spacing-sm;
      border-bottom: 1px solid $border-color;

      .tooltip-date {
        font-size: $font-size-sm;
        font-weight: 600;
        color: $text-primary;
      }

      .tooltip-count {
        font-size: $font-size-xs;
        color: $text-secondary;
        background: $gray-100;
        padding: 2px 8px;
        border-radius: $border-radius-full;
      }
    }

    .tooltip-events-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 200px;
      overflow-y: auto;
    }

    .tooltip-event-item {
      padding: 6px 10px;
      font-size: $font-size-sm;
      color: $text-primary;
      background: linear-gradient(
        135deg,
        rgba($primary-color, 0.08) 0%,
        rgba($primary-color, 0.04) 100%
      );
      border-left: 3px solid $primary-color;
      border-radius: $border-radius-md;
      cursor: pointer;
      transition: all $transition-fast;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;

      &:hover {
        background: linear-gradient(
          135deg,
          rgba($primary-color, 0.15) 0%,
          rgba($primary-color, 0.08) 100%
        );
        transform: translateX(4px);
      }
    }
  }
}

// ========== 周视图 ==========
.week-view {
  .week-header {
    display: flex;
    padding: $spacing-sm 0;
    border-bottom: 1px solid $border-color;
    background: $surface-color;
    border-radius: $border-radius-lg $border-radius-lg 0 0;

    .time-column-header {
      width: 60px;
      flex-shrink: 0;
    }

    .week-day-header {
      flex: 1;
      text-align: center;
      padding: $spacing-sm;
      cursor: pointer;
      transition: all $transition-fast;
      border-radius: $border-radius-md;

      &:hover {
        background: rgba($primary-color, 0.05);
      }

      &.today {
        .weekday-name {
          color: $primary-color;
          font-weight: 600;
        }
      }

      .weekday-name {
        font-size: $font-size-xs;
        color: $text-secondary;
        margin-bottom: 4px;
      }

      .weekday-date {
        font-size: $font-size-xl;
        font-weight: 600;
        color: $text-primary;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
        border-radius: 50%;

        &.today-badge {
          background: $primary-color;
          color: white;
          box-shadow: 0 2px 8px rgba($primary-color, 0.35);
        }
      }
    }
  }

  .week-grid {
    flex: 1;
    display: flex;
    overflow: auto;
    background: $surface-color;
    border-radius: 0 0 $border-radius-lg $border-radius-lg;
  }

  .time-column {
    width: 60px;
    flex-shrink: 0;
    border-right: 1px solid $border-color;
    background: $gray-50;

    .time-slot {
      height: 60px;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 4px;
      border-bottom: 1px solid rgba($border-color, 0.5);

      .time-label {
        font-size: $font-size-xs;
        color: $text-secondary;
      }
    }
  }

  .week-columns {
    flex: 1;
    display: flex;
  }

  .week-day-column {
    flex: 1;
    position: relative;
    border-right: 1px solid $border-color;
    cursor: pointer;
    min-width: 120px;

    &:last-child {
      border-right: none;
    }

    &.today {
      background: rgba($primary-color, 0.02);
    }

    .hour-cell {
      height: 60px;
      border-bottom: 1px solid rgba($border-color, 0.5);

      &:hover {
        background: rgba($primary-color, 0.05);
      }
    }

    .week-event-item {
      position: absolute;
      left: 4px;
      right: 4px;
      padding: 6px 8px;
      background: linear-gradient(
        135deg,
        rgba($primary-color, 0.15) 0%,
        rgba($primary-color, 0.08) 100%
      );
      border-left: 3px solid $primary-color;
      border-radius: $border-radius-md;
      cursor: pointer;
      transition: all $transition-fast;
      overflow: hidden;
      z-index: 1;

      &:hover {
        background: linear-gradient(
          135deg,
          rgba($primary-color, 0.25) 0%,
          rgba($primary-color, 0.15) 100%
        );
        transform: translateX(2px);
        box-shadow: 0 2px 8px rgba($primary-color, 0.2);
        z-index: 2;
      }

      .event-time {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        color: $text-secondary;
        margin-bottom: 2px;

        .el-icon {
          font-size: 10px;
        }
      }

      .event-title {
        font-size: $font-size-xs;
        color: $text-primary;
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}

// ========== 日视图 ==========
.day-view {
  .day-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-lg $spacing-xl;
    background: $surface-color;
    border-radius: $border-radius-lg $border-radius-lg 0 0;
    border-bottom: 1px solid $border-color;

    &.today {
      background: linear-gradient(
        135deg,
        rgba($primary-color, 0.08) 0%,
        rgba($primary-color, 0.03) 100%
      );

      .day-date {
        background: $primary-color;
        color: white;
        box-shadow: 0 4px 12px rgba($primary-color, 0.35);
      }
    }

    .day-title {
      display: flex;
      align-items: center;
      gap: $spacing-md;

      .day-date {
        width: 56px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: $font-size-3xl;
        font-weight: 700;
        color: $text-primary;
        background: $gray-100;
        border-radius: $border-radius-xl;
      }

      .day-info {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .day-weekday {
          font-size: $font-size-lg;
          font-weight: 600;
          color: $text-primary;
        }

        .day-full-date {
          font-size: $font-size-sm;
          color: $text-secondary;
        }
      }
    }

    .day-events-count {
      padding: $spacing-xs $spacing-md;
      background: rgba($primary-color, 0.1);
      color: $primary-color;
      font-size: $font-size-sm;
      font-weight: 500;
      border-radius: $border-radius-full;
    }
  }

  .day-grid {
    flex: 1;
    display: flex;
    overflow: auto;
    background: $surface-color;
    border-radius: 0 0 $border-radius-lg $border-radius-lg;
  }

  .time-column {
    width: 70px;
    flex-shrink: 0;
    border-right: 1px solid $border-color;
    background: $gray-50;

    .time-slot {
      height: 60px;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 4px;
      border-bottom: 1px solid rgba($border-color, 0.5);

      .time-label {
        font-size: $font-size-sm;
        color: $text-secondary;
        font-weight: 500;
      }
    }
  }

  .day-content {
    flex: 1;
    position: relative;
    cursor: pointer;

    .hour-cell {
      height: 60px;
      border-bottom: 1px solid rgba($border-color, 0.5);

      &:hover {
        background: rgba($primary-color, 0.03);
      }
    }

    .day-event-item {
      position: absolute;
      left: 12px;
      right: 12px;
      padding: 10px 14px;
      background: linear-gradient(
        135deg,
        rgba($primary-color, 0.15) 0%,
        rgba($primary-color, 0.08) 100%
      );
      border-left: 4px solid $primary-color;
      border-radius: $border-radius-lg;
      cursor: pointer;
      transition: all $transition-fast;
      z-index: 1;

      &:hover {
        background: linear-gradient(
          135deg,
          rgba($primary-color, 0.25) 0%,
          rgba($primary-color, 0.15) 100%
        );
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba($primary-color, 0.2);
        z-index: 2;
      }

      .event-time {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: $font-size-sm;
        color: $text-secondary;
        margin-bottom: 6px;

        .el-icon {
          font-size: 12px;
        }

        .event-end-time {
          color: $text-disabled;
        }
      }

      .event-title {
        font-size: $font-size-base;
        color: $text-primary;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .no-events {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;

      .sub-text {
        font-size: $font-size-sm;
        color: $text-secondary;
        margin-top: 8px;
      }
    }
  }
}

// ========== 响应式设计 ==========
@media (max-width: 1024px) {
  .calendar-toolbar {
    flex-wrap: wrap;
    gap: $spacing-md;

    .toolbar-center {
      order: 3;
      width: 100%;
      justify-content: center;
    }

    .current-title {
      min-width: auto;
    }
  }

  .week-view {
    .week-day-column {
      min-width: 100px;
    }
  }
}

@media (max-width: 768px) {
  .calendar-toolbar {
    padding: $spacing-sm;

    .toolbar-left {
      width: 100%;
      display: flex;
      gap: $spacing-sm;

      .field-select {
        flex: 1;
        margin-right: 0;
      }
    }

    .toolbar-right {
      width: 100%;
      display: flex;
      justify-content: center;
    }

    .toolbar-center {
      .current-title {
        font-size: $font-size-base;
      }
    }
  }

  .month-view {
    .calendar-header {
      padding: $spacing-sm $spacing-xs;
      margin-bottom: $spacing-sm;

      .weekday-cell {
        padding: $spacing-xs;
        font-size: $font-size-sm;
        letter-spacing: 0;

        &:first-child,
        &:last-child {
          border-radius: $border-radius-sm;
        }
      }
    }

    .calendar-cell {
      min-height: 65px;
      padding: 4px;
      border-radius: $border-radius-md;

      .cell-header {
        height: 24px;
        margin-bottom: 2px;
      }

      .day-number {
        width: 24px;
        height: 24px;
        font-size: $font-size-sm;
        font-weight: 500;
      }

      &.today {
        .day-number {
          width: 24px;
          height: 24px;
          font-size: $font-size-sm;
          font-weight: 600;
        }
      }
    }

    .event-item {
      padding: 2px 4px;
      font-size: 10px;
    }

    .more-events {
      font-size: 9px;
      padding: 2px 4px;
    }

    // 在平板端隐藏tooltip，改用点击展开
    .events-tooltip {
      display: none;
    }
  }

  .week-view {
    .week-day-header {
      .weekday-name {
        font-size: 10px;
      }

      .weekday-date {
        font-size: $font-size-base;
        width: 28px;
        height: 28px;
      }
    }

    .time-column {
      width: 45px;

      .time-label {
        font-size: 10px;
      }
    }
  }

  .day-view {
    .day-header {
      padding: $spacing-md;

      .day-date {
        width: 44px;
        height: 44px;
        font-size: $font-size-xl;
      }

      .day-info {
        .day-weekday {
          font-size: $font-size-base;
        }
      }
    }

    .time-column {
      width: 50px;

      .time-label {
        font-size: 11px;
      }
    }
  }
}

@media (max-width: 480px) {
  .view-switcher {
    .view-btn {
      padding: $spacing-xs $spacing-md;
      font-size: 12px;
    }
  }

  .nav-button-group {
    .nav-btn {
      width: 28px;
      height: 28px;

      &.today-btn {
        padding: 0 $spacing-sm;
        font-size: 12px;
      }
    }
  }

  .month-view {
    .calendar-header {
      padding: $spacing-xs 2px;
      margin-bottom: $spacing-xs;
      border-radius: $border-radius-md;

      .weekday-cell {
        padding: 4px 2px;
        font-size: 11px;
        font-weight: 600;

        &:first-child,
        &:last-child {
          color: $primary-color;
        }
      }
    }

    .calendar-grid {
      gap: 2px;
    }

    .calendar-cell {
      min-height: 50px;
      padding: 2px;
      border-radius: $border-radius-sm;

      .cell-header {
        height: 20px;
        margin-bottom: 2px;
      }

      .day-number {
        width: 20px;
        height: 20px;
        font-size: 12px;
        font-weight: 500;
      }

      &.today {
        border-width: 1px;

        .day-number {
          width: 20px;
          height: 20px;
          font-size: 12px;
          font-weight: 600;
          box-shadow: 0 2px 6px rgba($primary-color, 0.35);
        }
      }
    }

    .event-item {
      padding: 1px 3px;
      font-size: 9px;
      border-left-width: 2px;
    }

    .more-events {
      font-size: 8px;
      padding: 1px 3px;
    }
  }
}
</style>
