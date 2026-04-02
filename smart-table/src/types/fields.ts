export const FieldType = {
  TEXT: 'text',
  NUMBER: 'number',
  DATE: 'date',
  SINGLE_SELECT: 'singleSelect',
  MULTI_SELECT: 'multiSelect',
  CHECKBOX: 'checkbox',
  ATTACHMENT: 'attachment',
  MEMBER: 'member',
  RATING: 'rating',
  PROGRESS: 'progress',
  PHONE: 'phone',
  EMAIL: 'email',
  URL: 'url',
  FORMULA: 'formula',
  LINK: 'link',
  LOOKUP: 'lookup',
  CREATED_BY: 'createdBy',
  CREATED_TIME: 'createdTime',
  UPDATED_BY: 'updatedBy',
  UPDATED_TIME: 'updatedTime',
  AUTO_NUMBER: 'autoNumber'
} as const;

export type FieldTypeValue = typeof FieldType[keyof typeof FieldType];

export interface FieldOption {
  id: string;
  name: string;
  color: string;
}

export type RelationshipType = 'oneToOne' | 'oneToMany' | 'manyToMany';

export type AggregationType = 'single' | 'concat' | 'sum' | 'avg' | 'min' | 'max' | 'count';

export interface FieldOptions {
  // 通用选项
  isRichText?: boolean;
  maxLength?: number;
  precision?: number;
  format?: 'number' | 'currency' | 'percent';
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
    text: '文本',
    number: '数字',
    date: '日期',
    singleSelect: '单选',
    multiSelect: '多选',
    checkbox: '复选框',
    attachment: '附件',
    member: '成员',
    rating: '评分',
    progress: '进度',
    phone: '电话',
    email: '邮箱',
    url: '链接',
    formula: '公式',
    link: '关联',
    lookup: '查找',
    createdBy: '创建人',
    createdTime: '创建时间',
    updatedBy: '修改人',
    updatedTime: '修改时间',
    autoNumber: '自动编号'
  }
  return labels[type] || type
}

export function getFieldTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    text: '📝',
    number: '🔢',
    date: '📅',
    singleSelect: '☑️',
    multiSelect: '☑️',
    checkbox: '✅',
    attachment: '📎',
    member: '👤',
    rating: '⭐',
    progress: '📊',
    phone: '📞',
    email: '📧',
    url: '🔗',
    formula: '🔣',
    link: '🔗',
    lookup: '🔍',
    createdBy: '👤',
    createdTime: '🕐',
    updatedBy: '👤',
    updatedTime: '🕐',
    autoNumber: '🔢'
  }
  return icons[type] || '📝'
}

/**
 * 获取关联关系类型的标签
 */
export function getRelationshipTypeLabel(type: RelationshipType): string {
  const labels: Record<RelationshipType, string> = {
    oneToOne: '一对一',
    oneToMany: '一对多',
    manyToMany: '多对多'
  }
  return labels[type] || type
}

/**
 * 获取聚合类型的标签
 */
export function getAggregationTypeLabel(type: AggregationType): string {
  const labels: Record<AggregationType, string> = {
    single: '单个值',
    concat: '连接',
    sum: '求和',
    avg: '平均值',
    min: '最小值',
    max: '最大值',
    count: '计数'
  }
  return labels[type] || type
}
