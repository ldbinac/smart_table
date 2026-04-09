export const FieldType = {
  TEXT: "text",
  NUMBER: "number",
  DATE: "date",
  SINGLE_SELECT: "single_select",
  MULTI_SELECT: "multi_select",
  CHECKBOX: "checkbox",
  ATTACHMENT: "attachment",
  MEMBER: "member",
  RATING: "rating",
  PROGRESS: "progress",
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

export type RelationshipType = "one_to_one" | "one_to_many" | "many_to_many";

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
  isRichText?: boolean;
  maxLength?: number;
  precision?: number;
  format?: "number" | "currency" | "percent";
  currencySymbol?: string;
  includeTime?: boolean;
  showTime?: boolean;
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

  // 自动编号选项
  startNumber?: number;

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
    text: "文本",
    number: "数字",
    date: "日期",
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

export function getFieldTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    text: "📝",
    number: "🔢",
    date: "📅",
    single_select: "☑️",
    multi_select: "☑️",
    checkbox: "✅",
    attachment: "📎",
    member: "👤",
    rating: "⭐",
    progress: "📊",
    phone: "📞",
    email: "📧",
    url: "🔗",
    formula: "🔣",
    link: "🔗",
    lookup: "🔍",
    created_by: "👤",
    created_time: "🕐",
    updated_by: "👤",
    updated_time: "🕐",
    auto_number: "🔢",
  };
  return icons[type] || "📝";
}

/**
 * 获取关联关系类型的标签
 */
export function getRelationshipTypeLabel(type: RelationshipType): string {
  const labels: Record<RelationshipType, string> = {
    one_to_one: "一对一",
    one_to_many: "一对多",
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
    // 文本类型
    'single_line_text': 'text',
    'long_text': 'text',
    'rich_text': 'text',
    
    // 日期时间类型
    'date_time': 'date',
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
    
    // 前端特有或后端不支持的类型（保持原样）
    'auto_number': 'auto_number',
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
    'text': 'single_line_text',
    'date': 'date',
    'link': 'link_to_record',
    'updated_by': 'last_modified_by',
    'member': 'collaborator',
    'number': 'number',
    'progress': 'percent',  // 前端的 progress 映射为后端的 percent
    'auto_number': 'auto_number',
  };
  
  // 如果映射表中存在则返回映射后的值，否则返回原值
  return typeMap[frontendType] || frontendType;
}
