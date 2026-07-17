import dayjs from 'dayjs'

type FormulaFunction = (...args: unknown[]) => unknown

export const formulaFunctions: Record<string, FormulaFunction> = {
  SUM: (...args: unknown[]) => {
    const numbers = flattenNumbers(args)
    return numbers.reduce((sum, n) => sum + n, 0)
  },
  
  AVG: (...args: unknown[]) => {
    const numbers = flattenNumbers(args)
    if (numbers.length === 0) return 0
    return numbers.reduce((sum, n) => sum + n, 0) / numbers.length
  },
  
  MAX: (...args: unknown[]) => {
    const numbers = flattenNumbers(args)
    if (numbers.length === 0) return 0
    return Math.max(...numbers)
  },
  
  MIN: (...args: unknown[]) => {
    const numbers = flattenNumbers(args)
    if (numbers.length === 0) return 0
    return Math.min(...numbers)
  },
  
  ROUND: (value: unknown, decimals: unknown = 0) => {
    const num = Number(value)
    const dec = Number(decimals)
    if (isNaN(num)) return '#ERROR'
    const factor = Math.pow(10, dec)
    return Math.round(num * factor) / factor
  },
  
  CEILING: (value: unknown) => {
    const num = Number(value)
    if (isNaN(num)) return '#ERROR'
    return Math.ceil(num)
  },
  
  FLOOR: (value: unknown) => {
    const num = Number(value)
    if (isNaN(num)) return '#ERROR'
    return Math.floor(num)
  },
  
  ABS: (value: unknown) => {
    const num = Number(value)
    if (isNaN(num)) return '#ERROR'
    return Math.abs(num)
  },
  
  MOD: (value: unknown, divisor: unknown) => {
    const num = Number(value)
    const div = Number(divisor)
    if (isNaN(num) || isNaN(div) || div === 0) return '#ERROR'
    return num % div
  },
  
  POWER: (base: unknown, exponent: unknown) => {
    const b = Number(base)
    const e = Number(exponent)
    if (isNaN(b) || isNaN(e)) return '#ERROR'
    return Math.pow(b, e)
  },
  
  SQRT: (value: unknown) => {
    const num = Number(value)
    if (isNaN(num) || num < 0) return '#ERROR'
    return Math.sqrt(num)
  },
  
  CONCAT: (...args: unknown[]) => {
    return args.map(a => String(a ?? '')).join('')
  },
  
  LEFT: (text: unknown, length: unknown) => {
    const str = String(text ?? '')
    const len = Number(length)
    if (isNaN(len)) return '#ERROR'
    return str.substring(0, len)
  },
  
  RIGHT: (text: unknown, length: unknown) => {
    const str = String(text ?? '')
    const len = Number(length)
    if (isNaN(len)) return '#ERROR'
    return str.substring(str.length - len)
  },
  
  LEN: (text: unknown) => {
    return String(text ?? '').length
  },
  
  UPPER: (text: unknown) => {
    return String(text ?? '').toUpperCase()
  },
  
  LOWER: (text: unknown) => {
    return String(text ?? '').toLowerCase()
  },
  
  TRIM: (text: unknown) => {
    return String(text ?? '').trim()
  },
  
  SUBSTITUTE: (text: unknown, oldText: unknown, newText: unknown, instance?: unknown) => {
    const str = String(text ?? '')
    const oldStr = String(oldText ?? '')
    const newStr = String(newText ?? '')
    const inst = instance !== undefined ? Number(instance) : undefined
    
    if (inst === undefined || isNaN(inst)) {
      return str.split(oldStr).join(newStr)
    }
    
    let count = 0
    return str.replace(new RegExp(escapeRegex(oldStr), 'g'), (match) => {
      count++
      return count === inst ? newStr : match
    })
  },
  
  REPLACE: (text: unknown, start: unknown, length: unknown, newText: unknown) => {
    const str = String(text ?? '')
    const startPos = Number(start) - 1
    const len = Number(length)
    const newStr = String(newText ?? '')
    
    if (isNaN(startPos) || isNaN(len)) return '#ERROR'
    return str.substring(0, startPos) + newStr + str.substring(startPos + len)
  },
  
  FIND: (findText: unknown, withinText: unknown, start?: unknown) => {
    const find = String(findText ?? '')
    const within = String(withinText ?? '')
    const startPos = start !== undefined ? Number(start) - 1 : 0
    
    if (isNaN(startPos)) return '#ERROR'
    const index = within.indexOf(find, startPos)
    return index === -1 ? 0 : index + 1
  },
  
  TODAY: () => {
    return dayjs().startOf('day').valueOf()
  },
  
  NOW: () => {
    return Date.now()
  },
  
  YEAR: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    return d.year()
  },

  MONTH: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    return d.month() + 1
  },

  DAY: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    return d.date()
  },

  HOUR: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    return d.hour()
  },

  MINUTE: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    return d.minute()
  },

  SECOND: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    return d.second()
  },

  WEEKDAY: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    // 1=周一, 7=周日，与后端保持一致
    const day = d.day()
    return day === 0 ? 7 : day
  },

  DATETIME_FORMAT: (date: unknown, format: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    const fmt = String(format ?? 'YYYY-MM-DD HH:mm:ss')
    return d.format(fmt)
  },

  FROMUNIXTIME: (timestamp: unknown) => {
    const ts = Number(timestamp)
    if (isNaN(ts)) return '#ERROR'
    // 前端日期统一使用毫秒时间戳
    return dayjs(ts).valueOf()
  },

  UNIXTIMESTAMP: (date: unknown) => {
    const d = parseDateValue(date)
    if (!d) return '#ERROR'
    // 前端日期统一使用毫秒时间戳
    return d.valueOf()
  },

  DATEDIF: (startDate: unknown, endDate: unknown, unit: unknown) => {
    const start = parseDateValue(startDate)
    const end = parseDateValue(endDate)
    if (!start || !end) return '#ERROR'

    const u = String(unit ?? 'D').toUpperCase()

    switch (u) {
      case 'Y':
        return end.diff(start, 'year')
      case 'M':
        return end.diff(start, 'month')
      case 'D':
        return end.diff(start, 'day')
      default:
        return '#ERROR'
    }
  },

  // DATEDIFF 是 DATEDIF 的别名，保持与飞书兼容
  DATEDIFF: (startDate: unknown, endDate: unknown, unit: unknown) => {
    const start = parseDateValue(startDate)
    const end = parseDateValue(endDate)
    if (!start || !end) return '#ERROR'

    const u = String(unit ?? 'day').toLowerCase()

    switch (u) {
      case 'y':
      case 'year':
        return end.diff(start, 'year')
      case 'm':
      case 'month':
        return end.diff(start, 'month')
      case 'd':
      case 'day':
        return end.diff(start, 'day')
      default:
        return '#ERROR'
    }
  },

  DATEADD: (date: unknown, amount: unknown, unit: unknown) => {
    const d = parseDateValue(date)
    const amt = Number(amount)
    const rawUnit = String(unit ?? 'day').trim()
    // 区分大小写：M=月，m=分；其余按小写处理
    const unitMap: Record<string, dayjs.ManipulateType> = {
      'M': 'month',
      'm': 'minute',
      'year': 'year',
      'years': 'year',
      'y': 'year',
      'month': 'month',
      'months': 'month',
      'week': 'week',
      'weeks': 'week',
      'w': 'week',
      'day': 'day',
      'days': 'day',
      'd': 'day',
      'hour': 'hour',
      'hours': 'hour',
      'h': 'hour',
      'minute': 'minute',
      'minutes': 'minute',
      'second': 'second',
      'seconds': 'second',
      's': 'second'
    }

    if (!d || isNaN(amt)) return '#ERROR'

    const u = unitMap[rawUnit] ?? unitMap[rawUnit.toLowerCase()] ?? 'day'
    const result = d.add(amt, u)
    return result.valueOf()
  },
  
  IF: (condition: unknown, trueValue: unknown, falseValue: unknown) => {
    const cond = toBoolean(condition)
    return cond ? trueValue : falseValue
  },
  
  AND: (...args: unknown[]) => {
    return args.every(toBoolean)
  },
  
  OR: (...args: unknown[]) => {
    return args.some(toBoolean)
  },
  
  NOT: (value: unknown) => {
    return !toBoolean(value)
  },
  
  IFERROR: (value: unknown, valueIfError: unknown) => {
    if (value === '#ERROR' || value instanceof Error) {
      return valueIfError
    }
    return value
  },
  
  IFS: (...args: unknown[]) => {
    for (let i = 0; i < args.length; i += 2) {
      const condition = args[i]
      const value = args[i + 1]
      if (toBoolean(condition)) {
        return value
      }
    }
    return '#ERROR'
  },
  
  SWITCH: (expression: unknown, ...args: unknown[]) => {
    for (let i = 0; i < args.length - 1; i += 2) {
      if (expression === args[i]) {
        return args[i + 1]
      }
    }
    if (args.length % 2 === 1) {
      return args[args.length - 1]
    }
    return '#ERROR'
  },
  
  COUNT: (...args: unknown[]) => {
    return flattenValues(args).filter(v => v !== null && v !== undefined && v !== '').length
  },
  
  COUNTA: (...args: unknown[]) => {
    return flattenValues(args).length
  },
  
  COUNTIF: (range: unknown, criteria: unknown) => {
    const values = Array.isArray(range) ? range : [range]
    const crit = String(criteria ?? '')
    
    return values.filter(v => {
      if (crit.startsWith('>=')) return Number(v) >= Number(crit.slice(2))
      if (crit.startsWith('<=')) return Number(v) <= Number(crit.slice(2))
      if (crit.startsWith('<>')) return String(v) !== crit.slice(2)
      if (crit.startsWith('>')) return Number(v) > Number(crit.slice(1))
      if (crit.startsWith('<')) return Number(v) < Number(crit.slice(1))
      if (crit.startsWith('=')) return String(v) === crit.slice(1)
      return String(v) === crit
    }).length
  },
  
  SUMIF: (range: unknown, criteria: unknown, sumRange?: unknown) => {
    const values = Array.isArray(range) ? range : [range]
    const sumValues = sumRange ? (Array.isArray(sumRange) ? sumRange : [sumRange]) : values
    const crit = String(criteria ?? '')
    
    let sum = 0
    values.forEach((v, i) => {
      let matches = false
      if (crit.startsWith('>=')) matches = Number(v) >= Number(crit.slice(2))
      else if (crit.startsWith('<=')) matches = Number(v) <= Number(crit.slice(2))
      else if (crit.startsWith('<>')) matches = String(v) !== crit.slice(2)
      else if (crit.startsWith('>')) matches = Number(v) > Number(crit.slice(1))
      else if (crit.startsWith('<')) matches = Number(v) < Number(crit.slice(1))
      else if (crit.startsWith('=')) matches = String(v) === crit.slice(1)
      else matches = String(v) === crit
      
      if (matches) {
        sum += Number(sumValues[i]) || 0
      }
    })
    return sum
  },
  
  AVERAGEIF: (range: unknown, criteria: unknown, avgRange?: unknown) => {
    const values = Array.isArray(range) ? range : [range]
    const avgValues = avgRange ? (Array.isArray(avgRange) ? avgRange : [avgRange]) : values
    const crit = String(criteria ?? '')
    
    let sum = 0
    let count = 0
    values.forEach((v, i) => {
      let matches = false
      if (crit.startsWith('>=')) matches = Number(v) >= Number(crit.slice(2))
      else if (crit.startsWith('<=')) matches = Number(v) <= Number(crit.slice(2))
      else if (crit.startsWith('<>')) matches = String(v) !== crit.slice(2)
      else if (crit.startsWith('>')) matches = Number(v) > Number(crit.slice(1))
      else if (crit.startsWith('<')) matches = Number(v) < Number(crit.slice(1))
      else if (crit.startsWith('=')) matches = String(v) === crit.slice(1)
      else matches = String(v) === crit
      
      if (matches) {
        sum += Number(avgValues[i]) || 0
        count++
      }
    })
    return count > 0 ? sum / count : 0
  }
}

function flattenNumbers(args: unknown[]): number[] {
  const result: number[] = []
  for (const arg of args) {
    if (Array.isArray(arg)) {
      result.push(...flattenNumbers(arg))
    } else if (typeof arg === 'number' && !isNaN(arg)) {
      result.push(arg)
    } else if (arg !== null && arg !== undefined && arg !== '') {
      const num = Number(arg)
      if (!isNaN(num)) {
        result.push(num)
      }
    }
  }
  return result
}

function flattenValues(args: unknown[]): unknown[] {
  const result: unknown[] = []
  for (const arg of args) {
    if (Array.isArray(arg)) {
      result.push(...flattenValues(arg))
    } else {
      result.push(arg)
    }
  }
  return result
}

function toBoolean(value: unknown): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const lower = value.toLowerCase()
    return lower === 'true' || lower === '1' || lower === 'yes'
  }
  return Boolean(value)
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * 解析日期值，支持多种格式：
 * - 数字时间戳（毫秒）
 * - 日期字符串（如 "2026-07-02"）
 * - Date 对象
 * - dayjs 对象
 */
function parseDateValue(value: unknown): dayjs.Dayjs | null {
  if (value === null || value === undefined) return null

  // 数字时间戳
  if (typeof value === 'number') {
    const d = dayjs(value)
    return d.isValid() ? d : null
  }

  // 字符串：尝试用 dayjs 解析
  if (typeof value === 'string') {
    const d = dayjs(value)
    return d.isValid() ? d : null
  }

  // Date 对象或 dayjs 对象
  if (value instanceof Date) {
    const d = dayjs(value)
    return d.isValid() ? d : null
  }

  // 尝试作为 dayjs 对象处理
  if (typeof value === 'object' && 'isValid' in value) {
    try {
      const d = value as dayjs.Dayjs
      return d.isValid() ? d : null
    } catch {
      return null
    }
  }

  return null
}

export const functionCategories = {
  math: ['SUM', 'AVG', 'MAX', 'MIN', 'ROUND', 'CEILING', 'FLOOR', 'ABS', 'MOD', 'POWER', 'SQRT'],
  text: ['CONCAT', 'LEFT', 'RIGHT', 'LEN', 'UPPER', 'LOWER', 'TRIM', 'SUBSTITUTE', 'REPLACE', 'FIND'],
  date: ['TODAY', 'NOW', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'WEEKDAY', 'DATETIME_FORMAT', 'FROMUNIXTIME', 'UNIXTIMESTAMP', 'DATEDIF', 'DATEDIFF', 'DATEADD'],
  logic: ['IF', 'AND', 'OR', 'NOT', 'IFERROR', 'IFS', 'SWITCH'],
  statistics: ['COUNT', 'COUNTA', 'COUNTIF', 'SUMIF', 'AVERAGEIF']
}

export const functionDescriptions: Record<string, string> = {
  SUM: '计算数值的总和',
  AVG: '计算数值的平均值',
  MAX: '返回最大值',
  MIN: '返回最小值',
  ROUND: '四舍五入到指定小数位',
  CEILING: '向上取整',
  FLOOR: '向下取整',
  ABS: '返回绝对值',
  MOD: '返回余数',
  POWER: '返回数的幂',
  SQRT: '返回平方根',
  CONCAT: '连接多个文本',
  LEFT: '返回文本左侧指定字符数',
  RIGHT: '返回文本右侧指定字符数',
  LEN: '返回文本长度',
  UPPER: '转换为大写',
  LOWER: '转换为小写',
  TRIM: '去除首尾空格',
  SUBSTITUTE: '替换文本',
  REPLACE: '替换指定位置的文本',
  FIND: '查找文本位置',
  TODAY: '返回今天的日期',
  NOW: '返回当前日期时间',
  YEAR: '返回年份',
  MONTH: '返回月份',
  DAY: '返回日期',
  HOUR: '返回小时',
  MINUTE: '返回分钟',
  SECOND: '返回秒',
  WEEKDAY: '返回星期几 (1=周一, 7=周日)',
  DATETIME_FORMAT: '按指定格式显示日期时间',
  FROMUNIXTIME: '时间戳转日期时间（毫秒）',
  UNIXTIMESTAMP: '日期时间转时间戳（毫秒）',
  DATEDIF: '计算两个日期之间的差',
  DATEDIFF: '计算两个日期之间的差（DATEDIF的别名）',
  DATEADD: '日期加减',
  IF: '条件判断',
  AND: '逻辑与',
  OR: '逻辑或',
  NOT: '逻辑非',
  IFERROR: '错误处理',
  IFS: '多条件判断',
  SWITCH: '多值匹配',
  COUNT: '计数',
  COUNTA: '计数非空值',
  COUNTIF: '条件计数',
  SUMIF: '条件求和',
  AVERAGEIF: '条件平均值'
}
