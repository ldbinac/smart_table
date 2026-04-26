export const FieldType = {
  SINGLE_LINE_TEXT: "single_line_text",
  LONG_TEXT: "long_text",
  RICH_TEXT: "rich_text",
  NUMBER: "number",
  DATE: "date",
  DATE_TIME: "date_time",
  SINGLE_SELECT: "single_select",
  MULTI_SELECT: "multi_select",
  CHECKBOX: "checkbox",
  ATTACHMENT: "attachment",
  MEMBER: "member",
  RATING: "rating",
  PROGRESS: "progress",
  PERCENT: "percent",
  PHONE: "phone",
  EMAIL: "email",
  URL: "url",
  FORMULA: "formula",
  LINK: "link",
  LOOKUP: "lookup",
  CREATED_BY: "created_by",
  CREATED_TIME: "created_time",
  UPDATED_BY: "updated_by",
  UPDATED_TIME: "updated_time",
  AUTO_NUMBER: "auto_number",
} as const;

export type FieldTypeValue = (typeof FieldType)[keyof typeof FieldType];

export interface FieldOption {
  id: string;
  name: string;
  color: string;
}

export type RelationshipType = "one_to_one" | "one_to_many" | "many_to_one" | "many_to_many";

export type AggregationType =
  | "single"
  | "concat"
  | "sum"
  | "avg"
  | "min"
  | "max"
  | "count";

export interface FieldOptions {
  // 通用选项
  maxLength?: number;
  precision?: number;
  format?: "number" | "currency" | "percent";
  currencySymbol?: string;
  includeTime?: boolean;
  dateFormat?: string;
  prefix?: string;
  suffix?: string;

  // 单选/多选选项
  options?: FieldOption[];
  allowAddOptions?: boolean;

  // 评分选项
  maxRating?: number;

  // 进度选项
  showPercent?: boolean;

  // 公式选项
  formula?: string;

  // ==================== 自动编号字段 (Auto Number Field) 选项 ====================
  /** 起始编号 */
  startNumber?: number;
  /** 编号前缀 */
  prefix?: string;
  /** 编号后缀 */
  suffix?: string;
  /** 编号位数（不足时前面补0） */
  digitLength?: number;
  /** 是否包含日期前缀 */
  includeDate?: boolean;
  /** 日期格式（用于编号前缀） */
  dateFormat?: string;

  // ==================== 附件字段 (Attachment Field) 选项 ====================
  /** 接受的 MIME 类型 */
  acceptTypes?: string[];
  /** 接受的文件扩展名 */
  acceptExtensions?: string[];
  /** 单个文件最大大小（字节） */
  maxSize?: number;
  /** 总大小限制（字节） */
  maxTotalSize?: number;
  /** 最大文件数量 */
  maxCount?: number;
  /** 最小文件数量 */
  minCount?: number;
  /** 是否生成缩略图 */
  enableThumbnail?: boolean;
  /** 缩略图最大宽度 */
  thumbnailMaxWidth?: number;
  /** 缩略图最大高度 */
  thumbnailMaxHeight?: number;
  /** 缩略图质量 0-1 */
  thumbnailQuality?: number;

  // ==================== 关联字段 (Link Field) 选项 ====================
  /** 关联的目标表 ID */
  linkedTableId?: string;
  /** 关联字段 ID（用于双向关联） */
  linkedFieldId?: string;
  /** 显示字段 ID（用于显示关联记录的哪个字段值） */
  displayFieldId?: string;
  /** 是否允许多选 */
  allowMultiple?: boolean;
  /** 关联关系类型 */
  relationshipType?: RelationshipType;
  /** 是否为双向关联 */
  bidirectional?: boolean;
  /** 反向关联字段 ID */
  inverseFieldId?: string;

  // ==================== 查找字段 (Lookup Field) 选项 ====================
  /** 查找的目标字段 ID */
  lookupFieldId?: string;
  /** 聚合类型 */
  aggregationType?: AggregationType;
  /** 连接分隔符（用于 concat 聚合） */
  separator?: string;
}

export type CellValue =
  | string
  | number
  | boolean
  | null
  | string[]
  | { id: string; name: string }[]
  | { id: string; url: string; name: string }[];

export function getFieldTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    single_line_text: "单行文本",
    long_text: "多行文本",
    rich_text: "富文本",
    number: "数字",
    date: "日期",
    date_time: "日期时间",
    single_select: "单选",
    multi_select: "多选",
    checkbox: "复选框",
    attachment: "附件",
    member: "成员",
    rating: "评分",
    progress: "进度",
    phone: "电话",
    email: "邮箱",
    url: "链接",
    formula: "公式",
    link: "关联",
    lookup: "查找",
    created_by: "创建人",
    created_time: "创建时间",
    updated_by: "修改人",
    updated_time: "修改时间",
    auto_number: "自动编号",
  };
  return labels[type] || type;
}

// export function getFieldTypeIcon(type: string): string {
//   const icons: Record<string, string> = {
//     single_line_text: "📝",
//     long_text: "📄",
//     rich_text: "🎨",
//     number: "🔢",
//     date: "📅",
//     date_time: "🕐",
//     single_select: "🔘",
//     multi_select: "☑️",
//     checkbox: "✅",
//     attachment: "📎",
//     member: "👤",
//     rating: "⭐",
//     progress: "📊",
//     phone: "📞",
//     email: "📧",
//     url: "🔗",
//     formula: "🔣",
//     link: "🔗",
//     lookup: "🔍",
//     created_by: "👤",
//     created_time: "🕐",
//     updated_by: "👤",
//     updated_time: "🕐",
//     auto_number: "🔢",
//   };
//   return icons[type] || "📝";
// }

// ==================== Element Plus 图标组件映射 ====================

import type { Component } from "vue";
import {
  EditPen,
  Document,
  Memo,
  Sort,
  Calendar,
  AlarmClock,
  CircleCheck,
  FolderChecked,
  TurnOff,
  Paperclip,
  User,
  Star,
  TrendCharts,
  Phone,
  Message,
  Link,
  Share,
  Search,
  Timer,
  ScaleToOriginal,
} from "@element-plus/icons-vue";

/**
 * 字段类型到 Element Plus 图标组件的映射
 */
const fieldTypeIconComponentMap: Record<string, Component> = {
  single_line_text: EditPen,
  long_text: Document,
  rich_text: Memo,
  number: ScaleToOriginal,
  percent: Sort,
  date: Calendar,
  date_time: AlarmClock,
  single_select: CircleCheck,
  multi_select: FolderChecked,
  checkbox: TurnOff,
  attachment: Paperclip,
  member: User,
  created_by: User,
  updated_by: User,
  rating: Star,
  progress: TrendCharts,
  phone: Phone,
  email: Message,
  url: Link,
  link: Link,
  formula: Share,
  lookup: Search,
  created_time: Timer,
  updated_time: Timer,
  auto_number: Document,
};

/**
 * 获取字段类型对应的 Element Plus 图标组件
 * @param type 字段类型
 * @returns 图标组件，如果没有匹配则返回 Document 组件
 */
export function getFieldTypeIconComponent(type: string): Component {
  return fieldTypeIconComponentMap[type] || Document;
}

/**
 * 获取关联关系类型的标签
 */
export function getRelationshipTypeLabel(type: RelationshipType): string {
  const labels: Record<RelationshipType, string> = {
    one_to_one: "一对一",
    one_to_many: "一对多",
    many_to_one: "多对一",
    many_to_many: "多对多",
  };
  return labels[type] || type;
}

/**
 * 获取聚合类型的标签
 */
export function getAggregationTypeLabel(type: AggregationType): string {
  const labels: Record<AggregationType, string> = {
    single: "单个值",
    concat: "连接",
    sum: "求和",
    avg: "平均值",
    min: "最小值",
    max: "最大值",
    count: "计数",
  };
  return labels[type] || type;
}

/**
 * 将后端返回的字段类型转换为前端使用的类型
 * 后端类型 -> 前端类型 映射
 */
export function normalizeFieldType(backendType: string): string {
  const typeMap: Record<string, string> = {
    // 日期时间类型 - date_time 保持为 date_time，date 保持为 date
    'duration': 'number',
    
    // 关联类型
    'link_to_record': 'link',
    'rollup': 'lookup',
    
    // 人员类型
    'last_modified_by': 'updated_by',
    'collaborator': 'member',
    
    // 其他类型映射
    'currency': 'number',
    'percent': 'progress',  // 后端的 percent 映射为前端的 progress
  };
  
  // 如果映射表中存在则返回映射后的值，否则返回原值
  return typeMap[backendType] || backendType;
}

/**
 * 将前端字段类型转换为后端使用的类型（用于发送到后端 API）
 * 前端类型 -> 后端类型 映射
 */
export function denormalizeFieldType(frontendType: string): string {
  const typeMap: Record<string, string> = {
    'date': 'date',
    'link': 'link_to_record',
    'updated_by': 'last_modified_by',
    'member': 'collaborator',
    'number': 'number',
    'progress': 'percent',  // 前端的 progress 映射为后端的 percent
  };
  
  // 如果映射表中存在则返回映射后的值，否则返回原值
  return typeMap[frontendType] || frontendType;
}

/**
 * 生成自动编号字符串
 * @param sequence 序列号
 * @param options 自动编号配置选项
 * @returns 格式化后的编号字符串
 */
export function generateAutoNumber(
  sequence: number,
  options?: FieldOptions
): string {
  if (!options) {
    return String(sequence);
  }

  const {
    prefix = '',
    suffix = '',
    digitLength = 0,
    includeDate = false,
    dateFormat = 'YYYYMMDD',
  } = options;

  let numberPart = String(sequence);

  // 补零
  if (digitLength > 0 && numberPart.length < digitLength) {
    numberPart = numberPart.padStart(digitLength, '0');
  }

  // 日期前缀
  let datePart = '';
  if (includeDate) {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');

    switch (dateFormat) {
      case 'YYYYMMDD':
        datePart = `${year}${month}${day}`;
        break;
      case 'YYYYMM':
        datePart = `${year}${month}`;
        break;
      case 'YYYY':
        datePart = `${year}`;
        break;
      case 'YYMMDD':
        datePart = `${String(year).slice(-2)}${month}${day}`;
        break;
      default:
        datePart = `${year}${month}${day}`;
    }

    // 日期和数字之间用连字符分隔
    if (datePart) {
      datePart = `${datePart}-`;
    }
  }

  return `${prefix}${datePart}${numberPart}${suffix}`;
}
