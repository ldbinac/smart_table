import type { FieldEntity, RecordEntity } from '@/db/schema'
import { FieldType } from '@/types'
import dayjs from 'dayjs'

export interface ProcessedData {
  labels: string[]
  values: number[]
  rawData: Array<{
    label: string
    value: number
    records: RecordEntity[]
  }>
}

/**
 * 获取选项的显示名称
 */
export function getOptionDisplayName(
  field: FieldEntity,
  optionId: string
): string {
  if (!optionId || optionId === 'null' || optionId === 'undefined') {
    return '未设置'
  }

  const options = (field.options?.options || []) as Array<{
    id: string
    name: string
    color?: string
  }>

  const option = options.find(opt => opt.id === optionId)
  return option?.name || optionId
}

/**
 * 获取选项的完整信息
 */
export function getOptionInfo(
  field: FieldEntity,
  optionId: string
): { id: string; name: string; color: string } | null {
  if (!optionId || optionId === 'null' || optionId === 'undefined') {
    return null
  }

  const options = (field.options?.options || []) as Array<{
    id: string
    name: string
    color?: string
  }>

  const option = options.find(opt => opt.id === optionId)
  if (option) {
    return {
      id: option.id,
      name: option.name,
      color: option.color || '#3370FF'
    }
  }

  // 如果找不到选项，可能是直接存储了名称
  return {
    id: optionId,
    name: optionId,
    color: '#3370FF'
  }
}

/**
 * 获取多选字段的显示值
 */
export function getMultiSelectDisplayNames(
  field: FieldEntity,
  value: unknown
): string[] {
  if (!Array.isArray(value) || value.length === 0) {
    return []
  }

  return value.map(v => getOptionDisplayName(field, String(v)))
}

/**
 * 格式化日期值
 */
export function formatDateValue(
  field: FieldEntity,
  value: unknown
): string {
  if (value === null || value === undefined) {
    return '未设置'
  }

  const showTime = (field.options?.showTime as boolean) ?? false
  const format = showTime ? 'YYYY-MM-DD HH:mm' : 'YYYY-MM-DD'

  if (typeof value === 'number') {
    return dayjs(value).format(format)
  }

  if (typeof value === 'string') {
    const num = parseInt(value)
    if (!isNaN(num) && String(num).length >= 10) {
      return dayjs(num).format(format)
    }
    return value
  }

  return String(value)
}

/**
 * 格式化数值
 */
export function formatNumberValue(
  field: FieldEntity,
  value: unknown
): string {
  if (value === null || value === undefined || value === '') {
    return '未设置'
  }

  const num = Number(value)
  if (isNaN(num)) {
    return String(value)
  }

  const precision = (field.options?.precision as number) ?? 0
  const prefix = (field.options?.prefix as string) || ''
  const suffix = (field.options?.suffix as string) || ''

  return `${prefix}${num.toFixed(precision)}${suffix}`
}

/**
 * 获取字段值的显示文本（用于分组标签）
 */
export function getFieldValueDisplay(
  field: FieldEntity | undefined,
  value: unknown
): string {
  if (!field) {
    return String(value ?? '未设置')
  }

  if (value === null || value === undefined) {
    return '未设置'
  }

  switch (field.type) {
    case FieldType.SINGLE_SELECT:
      return getOptionDisplayName(field, String(value))

    case FieldType.MULTI_SELECT:
      return getMultiSelectDisplayNames(field, value).join(', ')

    case FieldType.DATE:
      return formatDateValue(field, value)

    case FieldType.NUMBER:
      return formatNumberValue(field, value)

    case FieldType.CHECKBOX:
      return value ? '是' : '否'

    case FieldType.RATING:
      return '★'.repeat(Number(value) || 0)

    case FieldType.PROGRESS:
      return `${value}%`

    default:
      return String(value)
  }
}

/**
 * 处理仪表盘图表数据
 */
export function processChartData(
  records: RecordEntity[],
  fields: FieldEntity[],
  groupByFieldId: string | undefined,
  valueFieldId: string,
  aggregation: 'count' | 'sum' | 'avg' | 'max' | 'min' | 'countDistinct'
): ProcessedData {
  const valueField = fields.find(f => f.id === valueFieldId)
  const groupByField = groupByFieldId
    ? fields.find(f => f.id === groupByFieldId)
    : undefined

  const grouped: Record<string, { values: number[]; records: RecordEntity[] }> = {}

  records.forEach(record => {
    // 确定分组键
    let groupKey: string
    if (groupByField) {
      const rawValue = record.values[groupByFieldId!]
      groupKey = getFieldValueDisplay(groupByField, rawValue)
    } else {
      groupKey = '全部'
    }

    if (!grouped[groupKey]) {
      grouped[groupKey] = { values: [], records: [] }
    }

    grouped[groupKey].records.push(record)

    // 计算值
    if (aggregation === 'count') {
      grouped[groupKey].values.push(1)
    } else if (aggregation === 'countDistinct') {
      // 去重计数在后续处理
      grouped[groupKey].values.push(1)
    } else {
      // 数值聚合
      const rawValue = record.values[valueFieldId]
      let numValue: number

      if (valueField?.type === FieldType.NUMBER) {
        numValue = Number(rawValue) || 0
      } else if (valueField?.type === FieldType.SINGLE_SELECT) {
        // 单选字段的数值聚合使用选项索引或1
        numValue = 1
      } else {
        numValue = Number(rawValue) || 0
      }

      if (!isNaN(numValue)) {
        grouped[groupKey].values.push(numValue)
      }
    }
  })

  // 计算聚合结果
  const labels = Object.keys(grouped)
  const values = labels.map(label => {
    const data = grouped[label]
    const nums = data.values

    switch (aggregation) {
      case 'sum':
        return nums.reduce((a, b) => a + b, 0)
      case 'avg':
        return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : 0
      case 'max':
        return nums.length ? Math.max(...nums) : 0
      case 'min':
        return nums.length ? Math.min(...nums) : 0
      case 'countDistinct':
        return new Set(data.records.map(r => r.values[valueFieldId])).size
      case 'count':
      default:
        return nums.length
    }
  })

  const rawData = labels.map((label, i) => ({
    label,
    value: values[i],
    records: grouped[label].records
  }))

  return { labels, values, rawData }
}

/**
 * 获取图表颜色方案
 */
export function getChartColors(count: number): string[] {
  const baseColors = [
    '#3370FF', // 主蓝色
    '#34D399', // 绿色
    '#F59E0B', // 橙色
    '#EF4444', // 红色
    '#8B5CF6', // 紫色
    '#EC4899', // 粉色
    '#06B6D4', // 青色
    '#84CC16', // 黄绿色
    '#F97316', // 深橙色
    '#6366F1', // 靛蓝色
    '#14B8A6', // 蓝绿色
    '#F43F5E', // 玫瑰红
  ]

  if (count <= baseColors.length) {
    return baseColors.slice(0, count)
  }

  // 如果需要更多颜色，循环使用并调整透明度
  const colors: string[] = []
  for (let i = 0; i < count; i++) {
    colors.push(baseColors[i % baseColors.length])
  }
  return colors
}

/**
 * 格式化大数字
 */
export function formatLargeNumber(num: number): string {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + '亿'
  }
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return String(num)
}

/**
 * 验证聚合配置是否有效
 */
export function validateAggregation(
  field: FieldEntity | undefined,
  aggregation: string
): { valid: boolean; message?: string } {
  if (!field) {
    return { valid: false, message: '请选择字段' }
  }

  if (aggregation === 'count' || aggregation === 'countDistinct') {
    return { valid: true }
  }

  // 数值聚合需要数值字段
  const numericTypes = [FieldType.NUMBER, FieldType.RATING, FieldType.PROGRESS, FieldType.AUTO_NUMBER]
  if (!numericTypes.includes(field.type)) {
    return {
      valid: false,
      message: `${field.name} 不是数值字段，无法使用 ${aggregation} 聚合`
    }
  }

  return { valid: true }
}
