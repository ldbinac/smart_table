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
  CURRENCY: "currency",
  BARCODE: "barcode",
  COLLABORATOR: "collaborator",
  LAST_MODIFIED_BY: "last_modified_by",
  DURATION: "duration",
  BUTTON: "button",
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
  defaultValue?: string | number | boolean | string[];

  // 单选/多选选项
  options?: FieldOption[];
  choices?: FieldOption[];
  allowAddOptions?: boolean;

  // 评分选项
  maxRating?: number;

  // 进度选项
  showPercent?: boolean;
  min?: number;
  max?: number;

  // 富文本选项
  isRichText?: boolean;

  // 成员选项
  multiple?: boolean;

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

  // ==================== 成员字段 (Member Field) 选项 ====================
  /** 默认值类型：当前用户或指定用户 */
  memberDefaultType?: "current_user" | "specific_user";
  /** 默认用户（当 memberDefaultType 为 specific_user 时使用） */
  memberDefaultUser?: {
    id: string;
    name: string;
    email: string;
    avatar?: string;
  };
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
    currency: "货币",
    percent: "百分比",
    rating: "评分",
    date: "日期",
    date_time: "日期时间",
    duration: "时长",
    single_select: "单选",
    multi_select: "多选",
    checkbox: "复选框",
    attachment: "附件",
    member: "成员",
    collaborator: "协作者",
    phone: "电话",
    email: "邮箱",
    url: "链接",
    link_to_record: "关联记录",
    link: "关联",
    lookup: "查找",
    rollup: "汇总",
    formula: "公式",
    auto_number: "自动编号",
    barcode: "条形码",
    button: "按钮",
    progress: "进度",
    created_by: "创建人",
    created_time: "创建时间",
    updated_by: "修改人",
    updated_time: "修改时间",
    last_modified_by: "最后修改人",
  };
  return labels[type] || type;
}

/**
 * 获取可用于导入/创建的字段类型选项列表
 * 排除系统生成的字段类型（如创建人、创建时间、修改人、修改时间、自动编号等）
 */
export function getImportableFieldTypeOptions(): { value: string; label: string }[] {
  const importableTypes = [
    FieldType.SINGLE_LINE_TEXT,
    FieldType.LONG_TEXT,
    FieldType.RICH_TEXT,
    FieldType.NUMBER,
    FieldType.CURRENCY,
    FieldType.PERCENT,
    FieldType.RATING,
    FieldType.DATE,
    FieldType.DATE_TIME,
    FieldType.DURATION,
    FieldType.SINGLE_SELECT,
    FieldType.MULTI_SELECT,
    FieldType.CHECKBOX,
    FieldType.ATTACHMENT,
    FieldType.MEMBER,
    FieldType.COLLABORATOR,
    FieldType.PHONE,
    FieldType.EMAIL,
    FieldType.URL,
    FieldType.BARCODE,
    FieldType.BUTTON,
    FieldType.PROGRESS,
  ];

  return importableTypes.map((type) => ({
    value: type,
    label: getFieldTypeLabel(type),
  }));
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
  ScaleToOriginal,
  PieChart,
  List,
  Calendar,
  AlarmClock,
  CircleCheck,
  FolderChecked,
  TurnOff,
  Paperclip,
  User,
  Star,
  Phone,
  Message,
  Link,
  Share,
  Search,
  Timer,
} from "@element-plus/icons-vue";

/**
 * 字段类型到 Element Plus 图标组件的映射
 */
const fieldTypeIconComponentMap: Record<string, Component> = {
  single_line_text: EditPen,
  long_text: Document,
  rich_text: Memo,
  number: ScaleToOriginal,
  percent: PieChart,
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
  progress: PieChart,
  phone: Phone,
  email: Message,
  url: Link,
  link: Link,
  formula: Share,
  lookup: Search,
  created_time: Timer,
  updated_time: Timer,
  auto_number: List,
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
 * 字段类型到 SVG 图标路径内容的映射
 * 路径数据与 @element-plus/icons-vue 保持一致（viewBox="0 0 1024 1024"，fill="currentColor"）
 * 存储的是 <svg> 标签内的子元素（<path> 等），由具体消费方自行包裹 <svg> 标签
 */
export const fieldTypeSvgContentMap: Record<string, string> = {
  single_line_text:
    '<path fill="currentColor" d="m199.04 672.64 193.984 112 224-387.968-193.92-112-224 388.032zm-23.872 60.16 32.896 148.288 144.896-45.696zM455.04 229.248l193.92 112 56.704-98.112-193.984-112zM104.32 708.8l384-665.024 304.768 175.936L409.152 884.8h.064l-248.448 78.336zm384 254.272v-64h448v64z"/>',
  long_text:
    '<path fill="currentColor" d="M832 384H576V128H192v768h640zm-26.496-64L640 154.496V320zM160 64h480l256 256v608a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V96a32 32 0 0 1 32-32m160 448h384v64H320zm0-192h160v64H320zm0 384h384v64H320z"/>',
  rich_text:
    '<path fill="currentColor" d="M480 320h192c21.33 0 32-10.67 32-32s-10.67-32-32-32H480c-21.33 0-32 10.67-32 32s10.67 32 32 32"/><path fill="currentColor" d="M887.01 72.99C881.01 67 873.34 64 864 64H160c-9.35 0-17.02 3-23.01 8.99C131 78.99 128 86.66 128 96v832c0 9.35 2.99 17.02 8.99 23.01S150.66 960 160 960h704c9.35 0 17.02-2.99 23.01-8.99S896 937.34 896 928V96c0-9.35-3-17.02-8.99-23.01M192 896V128h96v768zm640 0H352V128h480z"/><path fill="currentColor" d="M480 512h192c21.33 0 32-10.67 32-32s-10.67-32-32-32H480c-21.33 0-32 10.67-32 32s10.67 32 32 32m0 192h192c21.33 0 32-10.67 32-32s-10.67-32-32-32H480c-21.33 0-32 10.67-32 32s10.67 32 32 32"/>',
  number:
    '<path fill="currentColor" d="M813.176 180.706a60.235 60.235 0 0 1 60.236 60.235v481.883a60.235 60.235 0 0 1-60.236 60.235H210.824a60.235 60.235 0 0 1-60.236-60.235V240.94a60.235 60.235 0 0 1 60.236-60.235h602.352zm0-60.235H210.824A120.47 120.47 0 0 0 90.353 240.94v481.883a120.47 120.47 0 0 0 120.47 120.47h602.353a120.47 120.47 0 0 0 120.471-120.47V240.94a120.47 120.47 0 0 0-120.47-120.47zm-120.47 180.705a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 0 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118m-361.412 0a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 1 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118M512 361.412a30.12 30.12 0 0 0-30.118 30.117v30.118a30.118 30.118 0 0 0 60.236 0V391.53A30.12 30.12 0 0 0 512 361.412M512 512a30.12 30.12 0 0 0-30.118 30.118v30.117a30.118 30.118 0 0 0 60.236 0v-30.117A30.12 30.12 0 0 0 512 512"/>',
  percent:
    '<path fill="currentColor" d="M448 68.48v64.832A384.128 384.128 0 0 0 512 896a384.13 384.13 0 0 0 378.688-320h64.768A448.128 448.128 0 0 1 64 512 448.13 448.13 0 0 1 448 68.48"/><path fill="currentColor" d="M576 97.28V448h350.72A384.064 384.064 0 0 0 576 97.28M512 64V33.152A448 448 0 0 1 990.848 512H512z"/>',
  date:
    '<path fill="currentColor" d="M128 384v512h768V192H768v32a32 32 0 1 1-64 0v-32H320v32a32 32 0 0 1-64 0v-32H128v128h768v64zm192-256h384V96a32 32 0 1 1 64 0v32h160a32 32 0 0 1 32 32v768a32 32 0 0 1-32 32H96a32 32 0 0 1-32-32V160a32 32 0 0 1 32-32h160V96a32 32 0 0 1 64 0zm-32 384h64a32 32 0 0 1 0 64h-64a32 32 0 0 1 0-64m0 192h64a32 32 0 1 1 0 64h-64a32 32 0 1 1 0-64m192-192h64a32 32 0 0 1 0 64h-64a32 32 0 0 1 0-64m0 192h64a32 32 0 1 1 0 64h-64a32 32 0 1 1 0-64m192-192h64a32 32 0 1 1 0 64h-64a32 32 0 1 1 0-64m0 192h64a32 32 0 1 1 0 64h-64a32 32 0 1 1 0-64"/>',
  date_time:
    '<path fill="currentColor" d="M512 832a320 320 0 1 0 0-640 320 320 0 0 0 0 640m0 64a384 384 0 1 1 0-768 384 384 0 0 1 0 768"/><path fill="currentColor" d="m292.288 824.576 55.424 32-48 83.136a32 32 0 1 1-55.424-32zm439.424 0-55.424 32 48 83.136a32 32 0 1 0 55.424-32zM512 512h160a32 32 0 1 1 0 64H480a32 32 0 0 1-32-32V320a32 32 0 0 1 64 0zM90.496 312.256A160 160 0 0 1 312.32 90.496l-46.848 46.848a96 96 0 0 0-128 128L90.56 312.256zm835.264 0A160 160 0 0 0 704 90.496l46.848 46.848a96 96 0 0 1 128 128z"/>',
  single_select:
    '<path fill="currentColor" d="M512 896a384 384 0 1 0 0-768 384 384 0 0 0 0 768m0 64a448 448 0 1 1 0-896 448 448 0 0 1 0 896"/><path fill="currentColor" d="M745.344 361.344a32 32 0 0 1 45.312 45.312l-288 288a32 32 0 0 1-45.312 0l-160-160a32 32 0 1 1 45.312-45.312L480 626.752z"/>',
  multi_select:
    '<path fill="currentColor" d="M128 192v640h768V320H485.76L357.504 192zm-32-64h287.872l128.384 128H928a32 32 0 0 1 32 32v576a32 32 0 0 1-32 32H96a32 32 0 0 1-32-32V160a32 32 0 0 1 32-32m414.08 502.144 180.992-180.992L736.32 494.4 510.08 720.64l-158.4-158.336 45.248-45.312z"/>',
  checkbox:
    '<path fill="currentColor" d="M329.956 257.138a254.862 254.862 0 0 0 0 509.724h364.088a254.862 254.862 0 0 0 0-509.724zm0-72.818h364.088a327.68 327.68 0 1 1 0 655.36H329.956a327.68 327.68 0 1 1 0-655.36"/><path fill="currentColor" d="M329.956 621.227a109.227 109.227 0 1 0 0-218.454 109.227 109.227 0 0 0 0 218.454m0 72.817a182.044 182.044 0 1 1 0-364.088 182.044 182.044 0 0 1 0 364.088"/>',
  attachment:
    '<path fill="currentColor" d="M602.496 240.448A192 192 0 1 1 874.048 512l-316.8 316.8A256 256 0 0 1 195.2 466.752L602.496 59.456l45.248 45.248L240.448 512A192 192 0 0 0 512 783.552l316.8-316.8a128 128 0 1 0-181.056-181.056L353.6 579.904a32 32 0 1 0 45.248 45.248l294.144-294.144 45.312 45.248L444.096 670.4a96 96 0 1 1-135.744-135.744z"/>',
  member:
    '<path fill="currentColor" d="M512 512a192 192 0 1 0 0-384 192 192 0 0 0 0 384m0 64a256 256 0 1 1 0-512 256 256 0 0 1 0 512m320 320v-96a96 96 0 0 0-96-96H288a96 96 0 0 0-96 96v96a32 32 0 1 1-64 0v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 1 1-64 0"/>',
  created_by:
    '<path fill="currentColor" d="M512 512a192 192 0 1 0 0-384 192 192 0 0 0 0 384m0 64a256 256 0 1 1 0-512 256 256 0 0 1 0 512m320 320v-96a96 96 0 0 0-96-96H288a96 96 0 0 0-96 96v96a32 32 0 1 1-64 0v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 1 1-64 0"/>',
  updated_by:
    '<path fill="currentColor" d="M512 512a192 192 0 1 0 0-384 192 192 0 0 0 0 384m0 64a256 256 0 1 1 0-512 256 256 0 0 1 0 512m320 320v-96a96 96 0 0 0-96-96H288a96 96 0 0 0-96 96v96a32 32 0 1 1-64 0v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 1 1-64 0"/>',
  rating:
    '<path fill="currentColor" d="m512 747.84 228.16 119.936a6.4 6.4 0 0 0 9.28-6.72l-43.52-254.08 184.512-179.904a6.4 6.4 0 0 0-3.52-10.88l-255.104-37.12L517.76 147.904a6.4 6.4 0 0 0-11.52 0L392.192 379.072l-255.104 37.12a6.4 6.4 0 0 0-3.52 10.88L318.08 606.976l-43.584 254.08a6.4 6.4 0 0 0 9.28 6.72zM313.6 924.48a70.4 70.4 0 0 1-102.144-74.24l37.888-220.928L88.96 472.96A70.4 70.4 0 0 1 128 352.896l221.76-32.256 99.2-200.96a70.4 70.4 0 0 1 126.208 0l99.2 200.96 221.824 32.256a70.4 70.4 0 0 1 39.04 120.064L774.72 629.376l37.888 220.928a70.4 70.4 0 0 1-102.144 74.24L512 820.096l-198.4 104.32z"/>',
  progress:
    '<path fill="currentColor" d="M448 68.48v64.832A384.128 384.128 0 0 0 512 896a384.13 384.13 0 0 0 378.688-320h64.768A448.128 448.128 0 0 1 64 512 448.13 448.13 0 0 1 448 68.48"/><path fill="currentColor" d="M576 97.28V448h350.72A384.064 384.064 0 0 0 576 97.28M512 64V33.152A448 448 0 0 1 990.848 512H512z"/>',
  phone:
    '<path fill="currentColor" d="M79.36 432.256 591.744 944.64a32 32 0 0 0 35.2 6.784l253.44-108.544a32 32 0 0 0 9.984-52.032l-153.856-153.92a32 32 0 0 0-36.928-6.016l-69.888 34.944L358.08 394.24l35.008-69.888a32 32 0 0 0-5.952-36.928L233.152 133.568a32 32 0 0 0-52.032 10.048L72.512 397.056a32 32 0 0 0 6.784 35.2zm60.48-29.952 81.536-190.08L325.568 316.48l-24.64 49.216-20.608 41.216 32.576 32.64 271.552 271.552 32.64 32.64 41.216-20.672 49.28-24.576 104.192 104.128-190.08 81.472zM512 320v-64a256 256 0 0 1 256 256h-64a192 192 0 0 0-192-192m0-192V64a448 448 0 0 1 448 448h-64a384 384 0 0 0-384-384"/>',
  email:
    '<path fill="currentColor" d="M128 224v512a64 64 0 0 0 64 64h640a64 64 0 0 0 64-64V224zm0-64h768a64 64 0 0 1 64 64v512a128 128 0 0 1-128 128H192A128 128 0 0 1 64 736V224a64 64 0 0 1 64-64"/><path fill="currentColor" d="M904 224 656.512 506.88a192 192 0 0 1-289.024 0L120 224zm-698.944 0 210.56 240.704a128 128 0 0 0 192.704 0L818.944 224z"/>',
  url:
    '<path fill="currentColor" d="M715.648 625.152 670.4 579.904l90.496-90.56c75.008-74.944 85.12-186.368 22.656-248.896-62.528-62.464-173.952-52.352-248.96 22.656L444.16 353.6l-45.248-45.248 90.496-90.496c100.032-99.968 251.968-110.08 339.456-22.656 87.488 87.488 77.312 239.424-22.656 339.456l-90.496 90.496zm-90.496 90.496-90.496 90.496C434.624 906.112 282.688 916.224 195.2 828.8c-87.488-87.488-77.312-239.424 22.656-339.456l90.496-90.496 45.248 45.248-90.496 90.56c-75.008 74.944-85.12 186.368-22.656 248.896 62.528 62.464 173.952 52.352 248.96-22.656l90.496-90.496zm0-362.048 45.248 45.248L398.848 670.4 353.6 625.152z"/>',
  link:
    '<path fill="currentColor" d="M715.648 625.152 670.4 579.904l90.496-90.56c75.008-74.944 85.12-186.368 22.656-248.896-62.528-62.464-173.952-52.352-248.96 22.656L444.16 353.6l-45.248-45.248 90.496-90.496c100.032-99.968 251.968-110.08 339.456-22.656 87.488 87.488 77.312 239.424-22.656 339.456l-90.496 90.496zm-90.496 90.496-90.496 90.496C434.624 906.112 282.688 916.224 195.2 828.8c-87.488-87.488-77.312-239.424 22.656-339.456l90.496-90.496 45.248 45.248-90.496 90.56c-75.008 74.944-85.12 186.368-22.656 248.896 62.528 62.464 173.952 52.352 248.96-22.656l90.496-90.496zm0-362.048 45.248 45.248L398.848 670.4 353.6 625.152z"/>',
  formula:
    '<path fill="currentColor" d="m679.872 348.8-301.76 188.608a127.8 127.8 0 0 1 5.12 52.16l279.936 104.96a128 128 0 1 1-22.464 59.904l-279.872-104.96a128 128 0 1 1-16.64-166.272l301.696-188.608a128 128 0 1 1 33.92 54.272z"/>',
  lookup:
    '<path fill="currentColor" d="m795.904 750.72 124.992 124.928a32 32 0 0 1-45.248 45.248L750.656 795.904a416 416 0 1 1 45.248-45.248zM480 832a352 352 0 1 0 0-704 352 352 0 0 0 0 704"/>',
  created_time:
    '<path fill="currentColor" d="M512 896a320 320 0 1 0 0-640 320 320 0 0 0 0 640m0 64a384 384 0 1 1 0-768 384 384 0 0 1 0 768"/><path fill="currentColor" d="M512 320a32 32 0 0 1 32 32l-.512 224a32 32 0 1 1-64 0L480 352a32 32 0 0 1 32-32"/><path fill="currentColor" d="M448 576a64 64 0 1 0 128 0 64 64 0 1 0-128 0m96-448v128h-64V128h-96a32 32 0 0 1 0-64h256a32 32 0 1 1 0 64z"/>',
  updated_time:
    '<path fill="currentColor" d="M512 896a320 320 0 1 0 0-640 320 320 0 0 0 0 640m0 64a384 384 0 1 1 0-768 384 384 0 0 1 0 768"/><path fill="currentColor" d="M512 320a32 32 0 0 1 32 32l-.512 224a32 32 0 1 1-64 0L480 352a32 32 0 0 1 32-32"/><path fill="currentColor" d="M448 576a64 64 0 1 0 128 0 64 64 0 1 0-128 0m96-448v128h-64V128h-96a32 32 0 0 1 0-64h256a32 32 0 1 1 0 64z"/>',
  auto_number:
    '<path fill="currentColor" d="M704 192h160v736H160V192h160v64h384zM288 512h448v-64H288zm0 256h448v-64H288zm96-576V96h256v96z"/>',
  currency:
    '<path fill="currentColor" d="M813.176 180.706a60.235 60.235 0 0 1 60.236 60.235v481.883a60.235 60.235 0 0 1-60.236 60.235H210.824a60.235 60.235 0 0 1-60.236-60.235V240.94a60.235 60.235 0 0 1 60.236-60.235h602.352zm0-60.235H210.824A120.47 120.47 0 0 0 90.353 240.94v481.883a120.47 120.47 0 0 0 120.47 120.47h602.353a120.47 120.47 0 0 0 120.471-120.47V240.94a120.47 120.47 0 0 0-120.47-120.47zm-120.47 180.705a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 0 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118m-361.412 0a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 1 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118M512 361.412a30.12 30.12 0 0 0-30.118 30.117v30.118a30.118 30.118 0 0 0 60.236 0V391.53A30.12 30.12 0 0 0 512 361.412M512 512a30.12 30.12 0 0 0-30.118 30.118v30.117a30.118 30.118 0 0 0 60.236 0v-30.117A30.12 30.12 0 0 0 512 512"/>',
  barcode:
    '<path fill="currentColor" d="M813.176 180.706a60.235 60.235 0 0 1 60.236 60.235v481.883a60.235 60.235 0 0 1-60.236 60.235H210.824a60.235 60.235 0 0 1-60.236-60.235V240.94a60.235 60.235 0 0 1 60.236-60.235h602.352zm0-60.235H210.824A120.47 120.47 0 0 0 90.353 240.94v481.883a120.47 120.47 0 0 0 120.47 120.47h602.353a120.47 120.47 0 0 0 120.471-120.47V240.94a120.47 120.47 0 0 0-120.47-120.47zm-120.47 180.705a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 0 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118m-361.412 0a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 1 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118M512 361.412a30.12 30.12 0 0 0-30.118 30.117v30.118a30.118 30.118 0 0 0 60.236 0V391.53A30.12 30.12 0 0 0 512 361.412M512 512a30.12 30.12 0 0 0-30.118 30.118v30.117a30.118 30.118 0 0 0 60.236 0v-30.117A30.12 30.12 0 0 0 512 512"/>',
  collaborator:
    '<path fill="currentColor" d="M512 512a192 192 0 1 0 0-384 192 192 0 0 0 0 384m0 64a256 256 0 1 1 0-512 256 256 0 0 1 0 512m320 320v-96a96 96 0 0 0-96-96H288a96 96 0 0 0-96 96v96a32 32 0 1 1-64 0v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 1 1-64 0"/>',
  last_modified_by:
    '<path fill="currentColor" d="M512 512a192 192 0 1 0 0-384 192 192 0 0 0 0 384m0 64a256 256 0 1 1 0-512 256 256 0 0 1 0 512m320 320v-96a96 96 0 0 0-96-96H288a96 96 0 0 0-96 96v96a32 32 0 1 1-64 0v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 1 1-64 0"/>',
  duration:
    '<path fill="currentColor" d="M512 832a320 320 0 1 0 0-640 320 320 0 0 0 0 640m0 64a384 384 0 1 1 0-768 384 384 0 0 1 0 768"/><path fill="currentColor" d="m292.288 824.576 55.424 32-48 83.136a32 32 0 1 1-55.424-32zm439.424 0-55.424 32 48 83.136a32 32 0 1 0 55.424-32zM512 512h160a32 32 0 1 1 0 64H480a32 32 0 0 1-32-32V320a32 32 0 0 1 64 0zM90.496 312.256A160 160 0 0 1 312.32 90.496l-46.848 46.848a96 96 0 0 0-128 128L90.56 312.256zm835.264 0A160 160 0 0 0 704 90.496l46.848 46.848a96 96 0 0 1 128 128z"/>',
  button:
    '<path fill="currentColor" d="M813.176 180.706a60.235 60.235 0 0 1 60.236 60.235v481.883a60.235 60.235 0 0 1-60.236 60.235H210.824a60.235 60.235 0 0 1-60.236-60.235V240.94a60.235 60.235 0 0 1 60.236-60.235h602.352zm0-60.235H210.824A120.47 120.47 0 0 0 90.353 240.94v481.883a120.47 120.47 0 0 0 120.47 120.47h602.353a120.47 120.47 0 0 0 120.471-120.47V240.94a120.47 120.47 0 0 0-120.47-120.47zm-120.47 180.705a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 0 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118m-361.412 0a30.12 30.12 0 0 0-30.118 30.118v301.177a30.118 30.118 0 1 0 60.236 0V331.294a30.12 30.12 0 0 0-30.118-30.118M512 361.412a30.12 30.12 0 0 0-30.118 30.117v30.118a30.118 30.118 0 0 0 60.236 0V391.53A30.12 30.12 0 0 0 512 361.412M512 512a30.12 30.12 0 0 0-30.118 30.118v30.117a30.118 30.118 0 0 0 60.236 0v-30.117A30.12 30.12 0 0 0 512 512"/>',
};

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
