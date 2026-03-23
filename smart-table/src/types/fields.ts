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

export interface FieldOptions {
  isRichText?: boolean;
  maxLength?: number;
  precision?: number;
  format?: 'number' | 'currency' | 'percent';
  currencySymbol?: string;
  includeTime?: boolean;
  dateFormat?: string;
  options?: FieldOption[];
  allowAddOptions?: boolean;
  maxRating?: number;
  showPercent?: boolean;
  formula?: string;
  linkedTableId?: string;
  linkedFieldId?: string;
  lookupFieldId?: string;
  prefix?: string;
  suffix?: string;
  startNumber?: number;
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
