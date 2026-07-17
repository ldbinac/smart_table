<script setup lang="ts">
import { ref, computed, watch } from "vue";
import dayjs from "dayjs";
import { fieldService } from "@/db/services/fieldService";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import type { CellValue, LookupFieldConfig } from "@/types/fields";

interface Props {
  /** 后端实时计算的查找值（null / 数组 / 数字 / 字符串） */
  modelValue: CellValue;
  /** 字段对象（包含 config） */
  field: FieldEntity;
  /** 是否只读（查找字段强制为 true） */
  readonly?: boolean;
  /** 当前记录（已透传） */
  record?: RecordEntity;
  /** 所有字段（已透传） */
  allFields?: FieldEntity[];
}

const props = withDefaults(defineProps<Props>(), {
  readonly: true,
});

// 保留 emit 声明以保持接口一致性（FieldComponentFactory 会绑定 v-model）
// 查找字段强制只读，实际不会触发 emit
defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

// ==================== 配置读取 ====================

const config = computed<LookupFieldConfig | null>(() => {
  return (props.field.config as LookupFieldConfig | undefined) || null;
});

// 源字段定义：用于按源字段类型渲染 original/distinct 模式的值
const sourceField = ref<FieldEntity | null>(null);

async function loadSourceField() {
  if (!config.value?.sourceTableId || !config.value?.targetFieldId) {
    sourceField.value = null;
    return;
  }
  try {
    const fields = await fieldService.getFieldsByTable(
      config.value.sourceTableId,
    );
    sourceField.value =
      fields.find((f) => f.id === config.value!.targetFieldId) || null;
  } catch (e) {
    console.error("[LookupField] 加载源字段失败:", e);
    sourceField.value = null;
  }
}

watch(
  () => config.value?.targetFieldId,
  loadSourceField,
  { immediate: true },
);

// ==================== 渲染状态 ====================

// 是否为聚合模式（非 original/distinct）
const isAggregationMode = computed(() => {
  const t = config.value?.aggregationType;
  return !!t && !["original", "distinct"].includes(t);
});

// 源字段类型
const sourceFieldType = computed<string>(() => sourceField.value?.type ?? "");

// 字段类型分组
const NUMBER_TYPES = new Set(["number", "currency", "percent", "rating"]);
const DATE_TYPES = new Set(["date", "date_time"]);
const CHECKBOX_TYPES = new Set(["checkbox"]);
// 单选/多选类型：渲染为彩色标签
const SELECT_TYPES = new Set(["single_select", "multi_select"]);
// 成员类类型：渲染为头像 + 名称
const MEMBER_TYPES = new Set([
  "collaborator",
  "member",
  "created_by",
  "last_modified_by",
  "updated_by",
]);
// 附件类型：渲染为缩略图 + 名称
const ATTACHMENT_TYPES = new Set(["attachment"]);

// 结构化渲染项：用于 original/distinct 模式按源字段类型渲染
interface RenderItem {
  text: string;
  type: "text" | "tag" | "avatar" | "image";
  color?: string;
  avatar?: string;
  imageUrl?: string;
}

// 空值判断
const isEmpty = computed(() => {
  const v = props.modelValue;
  if (v === null || v === undefined) return true;
  if (Array.isArray(v)) return v.length === 0;
  if (typeof v === "string") return v === "";
  return false;
});

// ==================== 格式化工具 ====================

function formatNumber(value: number, precision: number): string {
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  });
}

// 按源字段类型格式化单个值（用于 original/distinct 模式）
function formatSingleItem(item: unknown): string {
  if (item === null || item === undefined) return "";

  // 对象类型：成员 {id, name} / 附件 {id, url, name}
  if (typeof item === "object") {
    const obj = item as Record<string, unknown>;
    if (typeof obj["name"] === "string") return obj["name"];
    return String(item);
  }

  const type = sourceFieldType.value;

  // 复选框：显示为 是/否
  if (CHECKBOX_TYPES.has(type)) {
    if (typeof item === "boolean") return item ? "是" : "否";
    const s = String(item).toLowerCase();
    if (s === "true" || s === "1") return "是";
    if (s === "false" || s === "0" || s === "") return "否";
    return String(item);
  }

  // 数字类：按源字段 precision 显示
  if (NUMBER_TYPES.has(type)) {
    const num = typeof item === "number" ? item : Number(item);
    if (!isNaN(num)) {
      const opts = sourceField.value?.options as
        | { precision?: number }
        | undefined;
      const precision = opts?.precision ?? 0;
      return formatNumber(num, precision);
    }
    return String(item);
  }

  // 日期类：按源字段 dateFormat 显示
  if (DATE_TYPES.has(type)) {
    const opts = sourceField.value?.options as
      | { dateFormat?: string; includeTime?: boolean }
      | undefined;
    const defaultFmt =
      type === "date_time" ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";
    const fmt = opts?.dateFormat ?? defaultFmt;
    const num = typeof item === "number" ? item : Number(item);
    if (!isNaN(num) && num > 0) {
      return dayjs(num).format(fmt);
    }
    return String(item);
  }

  // 文本类（single_line_text、long_text、rich_text、email、phone、url）及其他
  return String(item);
}

// 按源字段类型将单个值格式化为结构化渲染项（用于 original/distinct 模式）
function formatRenderItem(item: unknown): RenderItem {
  if (item === null || item === undefined) {
    return { text: "", type: "text" };
  }

  const type = sourceFieldType.value;

  // 单选/多选：item 是选项 ID 或名称，从 choices 中查找对应选项
  if (SELECT_TYPES.has(type)) {
    const opts = sourceField.value?.options as
      | { choices?: Array<{ id: string; name: string; color: string }> }
      | undefined;
    const choices = opts?.choices || [];
    const choice = choices.find(
      (c) =>
        c.id === item ||
        c.name === item ||
        String(c.id) === String(item) ||
        String(c.name) === String(item),
    );
    if (choice) {
      return {
        text: choice.name,
        type: "tag",
        color: choice.color,
      };
    }
    // 未匹配到选项：回退为纯文本
    return { text: String(item), type: "text" };
  }

  // 成员：item 是 { id, name, avatar? }
  if (MEMBER_TYPES.has(type)) {
    if (typeof item === "object" && item !== null) {
      const obj = item as {
        id?: string;
        name?: string;
        avatar?: string;
      };
      return {
        text: obj.name || String(item),
        type: "avatar",
        avatar: obj.avatar,
      };
    }
    return { text: String(item), type: "text" };
  }

  // 附件：item 是 { id, url, name, thumbnailUrl? }
  if (ATTACHMENT_TYPES.has(type)) {
    if (typeof item === "object" && item !== null) {
      const obj = item as {
        id?: string;
        url?: string;
        name?: string;
        thumbnailUrl?: string;
      };
      return {
        text: obj.name || String(item),
        type: "image",
        imageUrl: obj.thumbnailUrl || obj.url,
      };
    }
    return { text: String(item), type: "text" };
  }

  // 复选框
  if (CHECKBOX_TYPES.has(type)) {
    let text: string;
    if (typeof item === "boolean") {
      text = item ? "是" : "否";
    } else {
      const s = String(item).toLowerCase();
      if (s === "true" || s === "1") text = "是";
      else if (s === "false" || s === "0" || s === "") text = "否";
      else text = String(item);
    }
    return { text, type: "text" };
  }

  // 数字类
  if (NUMBER_TYPES.has(type)) {
    const num = typeof item === "number" ? item : Number(item);
    let text: string;
    if (!isNaN(num)) {
      const opts = sourceField.value?.options as
        | { precision?: number }
        | undefined;
      const precision = opts?.precision ?? 0;
      text = formatNumber(num, precision);
    } else {
      text = String(item);
    }
    return { text, type: "text" };
  }

  // 日期类
  if (DATE_TYPES.has(type)) {
    const opts = sourceField.value?.options as
      | { dateFormat?: string; includeTime?: boolean }
      | undefined;
    const defaultFmt =
      type === "date_time" ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";
    const fmt = opts?.dateFormat ?? defaultFmt;
    const num = typeof item === "number" ? item : Number(item);
    let text: string;
    if (!isNaN(num) && num > 0) {
      text = dayjs(num).format(fmt);
    } else {
      text = String(item);
    }
    return { text, type: "text" };
  }

  // 对象（含 name）
  if (typeof item === "object" && item !== null && "name" in item) {
    return {
      text: String((item as { name: unknown }).name),
      type: "text",
    };
  }

  // 默认文本
  return { text: String(item), type: "text" };
}

// 聚合模式兜底格式化（后端通常已格式化为字符串，此处仅对未格式化的数字做兜底）
function formatAggregationValue(v: NonNullable<CellValue>): string {
  if (typeof v === "number") {
    const fmt = config.value?.fieldFormat;
    const type = fmt?.type;
    const precision = fmt?.precision;
    if (type === "currency") {
      const symbol = fmt?.currencySymbol ?? "¥";
      return `${symbol}${formatNumber(v, precision ?? 2)}`;
    }
    if (type === "number") {
      return formatNumber(v, precision ?? 0);
    }
    // date 类型的聚合值通常已是字符串，数字直接显示
    return String(v);
  }
  return String(v);
}

// ==================== 最终显示值 ====================

const displayValue = computed(() => {
  const v = props.modelValue;
  if (v === null || v === undefined) return "-";
  if (Array.isArray(v)) {
    if (v.length === 0) return "-";
    return v.map((item) => formatSingleItem(item)).join(", ");
  }
  if (typeof v === "string" && v === "") return "-";
  if (isAggregationMode.value) {
    return formatAggregationValue(v as NonNullable<CellValue>);
  }
  // original/distinct 单值兜底
  return formatSingleItem(v);
});

// original/distinct 模式结构化值列表（用于按源字段类型渲染）
const valueItems = computed<RenderItem[]>(() => {
  const v = props.modelValue;
  if (v === null || v === undefined) return [];
  if (isAggregationMode.value) return []; // 聚合模式不使用结构化渲染

  const items = Array.isArray(v) ? v : [v];
  return items
    .filter((item) => item !== null && item !== undefined && item !== "")
    .map((item) => formatRenderItem(item))
    .filter((item) => item.text !== "");
});
</script>

<template>
  <div class="lookup-field" :class="{ 'is-empty': isEmpty }">
    <span v-if="isEmpty" class="lookup-empty">-</span>
    <!-- 聚合模式：直接显示字符串 -->
    <span v-else-if="isAggregationMode" class="lookup-value">{{
      displayValue
    }}</span>
    <!-- 原值/去重模式：按源字段类型结构化渲染 -->
    <template v-else>
      <span
        v-for="(item, idx) in valueItems"
        :key="idx"
        class="lookup-item">
        <!-- 单选/多选：彩色标签 -->
        <span
          v-if="item.type === 'tag' && item.color"
          class="lookup-tag"
          :style="{
            backgroundColor: item.color + '20',
            color: item.color,
          }">
          {{ item.text }}
        </span>
        <!-- 成员：头像 + 名称 -->
        <span v-else-if="item.type === 'avatar'" class="lookup-avatar">
          <img
            v-if="item.avatar"
            :src="item.avatar"
            class="lookup-avatar-img"
            :alt="item.text" />
          <span class="lookup-avatar-name">{{ item.text }}</span>
        </span>
        <!-- 附件：缩略图 + 名称 -->
        <span v-else-if="item.type === 'image'" class="lookup-image">
          <img
            v-if="item.imageUrl"
            :src="item.imageUrl"
            class="lookup-thumb"
            :alt="item.text" />
          <span class="lookup-image-name">{{ item.text }}</span>
        </span>
        <!-- 纯文本 -->
        <span v-else class="lookup-text">{{ item.text }}</span>
        <!-- 分隔符（非最后一项） -->
        <span
          v-if="idx < valueItems.length - 1"
          class="lookup-separator"
          >, </span
        >
      </span>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.lookup-field {
  width: 100%;
  min-height: 32px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.lookup-empty {
  color: $text-disabled;
  font-size: $font-size-base;
}

.lookup-value {
  font-size: $font-size-base;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// 结构化渲染（original/distinct 模式）
.lookup-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-base;
  color: $text-primary;
}

.lookup-text {
  font-size: $font-size-base;
  color: $text-primary;
}

// 单选/多选：彩色标签
.lookup-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: $font-size-sm;
  font-weight: 500;
  line-height: 1.4;
}

// 成员：头像 + 名称
.lookup-avatar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.lookup-avatar-img {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.lookup-avatar-name {
  font-size: $font-size-base;
  color: $text-primary;
}

// 附件：缩略图 + 名称
.lookup-image {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.lookup-thumb {
  width: 24px;
  height: 24px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}

.lookup-image-name {
  font-size: $font-size-base;
  color: $text-primary;
}

.lookup-separator {
  color: $text-secondary;
  margin: 0 2px;
}
</style>
