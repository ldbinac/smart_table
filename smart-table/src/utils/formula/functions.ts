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

  LN: (value: unknown) => {
    const num = Number(value)
    if (isNaN(num) || num <= 0) return '#ERROR'
    return Math.log(num)
  },

  LOG: (value: unknown, base: unknown = 10) => {
    const num = Number(value)
    const b = Number(base)
    if (isNaN(num) || isNaN(b) || num <= 0 || b <= 0 || b === 1) return '#ERROR'
    return Math.log(num) / Math.log(b)
  },

  EXP: (value: unknown) => {
    const num = Number(value)
    if (isNaN(num)) return '#ERROR'
    return Math.exp(num)
  },

  PI: () => Math.PI,

  E: () => Math.E,

  RAND: () => Math.random(),

  RANDBETWEEN: (min: unknown, max: unknown) => {
    const lo = Math.ceil(Number(min))
    const hi = Math.floor(Number(max))
    if (isNaN(lo) || isNaN(hi)) return '#ERROR'
    return Math.floor(Math.random() * (hi - lo + 1)) + lo
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

  MID: (text: unknown, start: unknown, length: unknown) => {
    const str = String(text ?? '')
    const startPos = Number(start) - 1
    const len = Number(length)
    if (isNaN(startPos) || isNaN(len)) return '#ERROR'
    return str.substring(startPos, startPos + len)
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

  REPT: (text: unknown, count: unknown) => {
    const str = String(text ?? '')
    const n = Math.floor(Number(count))
    if (isNaN(n)) return '#ERROR'
    return str.repeat(n)
  },

  TEXT: (value: unknown, format: unknown) => {
    const val = Number(value)
    const fmt = String(format ?? '#')
    if (isNaN(val)) return ''

    const lowerFmt = fmt.toLowerCase()
    if (lowerFmt === '0%') return `${Math.round(val * 100)}%`
    if (lowerFmt === '0.00%') return `${(val * 100).toFixed(2)}%`

    if (fmt.includes(',') && fmt.includes('.')) {
      const decimals = fmt.split('.')[1].replace('%', '').length
      return val.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    }
    if (fmt.includes('.')) {
      const decimals = fmt.split('.')[1].replace('%', '').length
      return val.toFixed(decimals)
    }
    if (fmt.includes(',')) {
      return val.toLocaleString('en-US', { maximumFractionDigits: 0 })
    }

    return String(val)
  },

  VALUE: (text: unknown) => {
    if (text === null || text === undefined) return null
    const cleaned = String(text).replace(/,/g, '').replace(/\s/g, '')
    const num = Number(cleaned)
    return isNaN(num) ? '#ERROR' : num
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

  XOR: (...args: unknown[]) => {
    if (args.length < 2) return !toBoolean(args[0])
    return args.reduce((acc, val) => acc !== toBoolean(val), false)
  },

  ISBLANK: (value: unknown) => {
    return value === null || value === undefined || value === '' || (Array.isArray(value) && value.length === 0)
  },

  ISERROR: (value: unknown) => {
    return value === '#ERROR' || value instanceof Error
  },

  ISNUMBER: (value: unknown) => {
    return typeof value === 'number' && !isNaN(value) && !isNaN(Number(value))
  },

  ISTEXT: (value: unknown) => {
    return typeof value === 'string'
  },

  ISDATE: (value: unknown) => {
    if (value instanceof Date) return true
    if (typeof value === 'number') return !isNaN(value)
    if (typeof value !== 'string') return false
    return parseDateValue(value) !== null
  },

  BLANK: () => null,

  NA: () => '#N/A',

  ERROR: (message?: unknown) => {
    return `#ERROR: ${message ?? ''}`
  },

  COUNT: (...args: unknown[]) => {
    return flattenValues(args).filter(v => v !== null && v !== undefined && v !== '').length
  },

  COUNTA: (...args: unknown[]) => {
    return flattenValues(args).length
  },

  COUNTIF: (range: unknown, criteria: unknown) => {
    const values = Array.isArray(range) ? range : [range]
    return values.filter(v => matchesCriteria(v, criteria)).length
  },

  SUMIF: (range: unknown, criteria: unknown, sumRange?: unknown) => {
    const values = Array.isArray(range) ? range : [range]
    const sumValues = sumRange ? (Array.isArray(sumRange) ? sumRange : [sumRange]) : values

    let sum = 0
    values.forEach((v, i) => {
      if (matchesCriteria(v, criteria)) {
        sum += Number(sumValues[i]) || 0
      }
    })
    return sum
  },

  AVERAGEIF: (range: unknown, criteria: unknown, avgRange?: unknown) => {
    const values = Array.isArray(range) ? range : [range]
    const avgValues = avgRange ? (Array.isArray(avgRange) ? avgRange : [avgRange]) : values

    let sum = 0
    let count = 0
    values.forEach((v, i) => {
      if (matchesCriteria(v, criteria)) {
        sum += Number(avgValues[i]) || 0
        count++
      }
    })
    return count > 0 ? sum / count : 0
  },

  COUNTBLANK: (...args: unknown[]) => {
    return flattenValues(args).filter(v => v === null || v === undefined || v === '').length
  },

  STDEV: (...args: unknown[]) => {
    const numbers = flattenNumbers(args)
    if (numbers.length < 2) return null
    const mean = numbers.reduce((a, b) => a + b, 0) / numbers.length
    const variance = numbers.reduce((sum, n) => sum + Math.pow(n - mean, 2), 0) / (numbers.length - 1)
    return Math.sqrt(variance)
  },

  VAR: (...args: unknown[]) => {
    const numbers = flattenNumbers(args)
    if (numbers.length < 2) return null
    const mean = numbers.reduce((a, b) => a + b, 0) / numbers.length
    return numbers.reduce((sum, n) => sum + Math.pow(n - mean, 2), 0) / (numbers.length - 1)
  },

  MEDIAN: (...args: unknown[]) => {
    const numbers = flattenNumbers(args).sort((a, b) => a - b)
    if (numbers.length === 0) return null
    const mid = Math.floor(numbers.length / 2)
    return numbers.length % 2 === 1 ? numbers[mid] : (numbers[mid - 1] + numbers[mid]) / 2
  },

  MODE: (...args: unknown[]) => {
    const numbers = flattenNumbers(args)
    if (numbers.length === 0) return null
    const counts = new Map<number, number>()
    numbers.forEach(n => counts.set(n, (counts.get(n) || 0) + 1))
    let maxCount = 0
    let modes: number[] = []
    counts.forEach((count, n) => {
      if (count > maxCount) {
        maxCount = count
        modes = [n]
      } else if (count === maxCount) {
        modes.push(n)
      }
    })
    return modes.length === 1 ? modes[0] : null
  },

  RANK: (value: unknown, ...others: unknown[]) => {
    const num = Number(value)
    if (isNaN(num)) return null
    const all = flattenNumbers(others)
    return all.filter(v => v < num).length + 1
  },

  UNIQUE: (...args: unknown[]) => {
    const values = flattenValues(args)
    const seen = new Set<string>()
    return values.filter(v => {
      const key = typeof v === 'object' ? JSON.stringify(v) : String(v)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
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

function isNumericValue(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value) && !isNaN(Number(value))
}

function matchesCriteria(value: unknown, criteria: unknown): boolean {
  const crit = String(criteria ?? '')
  if (crit.startsWith('>=')) return isNumericValue(value as number) && (value as number) >= Number(crit.slice(2))
  if (crit.startsWith('<=')) return isNumericValue(value as number) && (value as number) <= Number(crit.slice(2))
  if (crit.startsWith('<>')) return String(value) !== crit.slice(2)
  if (crit.startsWith('>')) return isNumericValue(value as number) && (value as number) > Number(crit.slice(1))
  if (crit.startsWith('<')) return isNumericValue(value as number) && (value as number) < Number(crit.slice(1))
  if (crit.startsWith('=')) return String(value) === crit.slice(1)
  return String(value) === crit
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
  math: ['SUM', 'AVG', 'MAX', 'MIN', 'ROUND', 'CEILING', 'FLOOR', 'ABS', 'MOD', 'POWER', 'SQRT', 'LN', 'LOG', 'EXP', 'PI', 'E', 'RAND', 'RANDBETWEEN'],
  text: ['CONCAT', 'LEFT', 'RIGHT', 'MID', 'LEN', 'UPPER', 'LOWER', 'TRIM', 'SUBSTITUTE', 'REPLACE', 'FIND', 'REPT', 'TEXT', 'VALUE'],
  date: ['TODAY', 'NOW', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'WEEKDAY', 'DATETIME_FORMAT', 'FROMUNIXTIME', 'UNIXTIMESTAMP', 'DATEDIF', 'DATEDIFF', 'DATEADD'],
  logic: ['IF', 'AND', 'OR', 'NOT', 'IFERROR', 'IFS', 'SWITCH', 'XOR', 'ISBLANK', 'ISERROR', 'ISNUMBER', 'ISTEXT', 'ISDATE', 'BLANK', 'NA', 'ERROR'],
  statistics: ['COUNT', 'COUNTA', 'COUNTBLANK', 'COUNTIF', 'SUMIF', 'AVERAGEIF', 'STDEV', 'VAR', 'MEDIAN', 'MODE', 'RANK', 'UNIQUE']
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
  LN: '返回自然对数',
  LOG: '返回指定底数的对数',
  EXP: '返回 e 的指定次幂',
  PI: '返回圆周率 π',
  E: '返回自然常数 e',
  RAND: '返回 [0,1) 之间的随机数',
  RANDBETWEEN: '返回指定范围内的随机整数',
  CONCAT: '连接多个文本',
  LEFT: '返回文本左侧指定字符数',
  RIGHT: '返回文本右侧指定字符数',
  MID: '从文本指定位置返回指定长度字符',
  LEN: '返回文本长度',
  UPPER: '转换为大写',
  LOWER: '转换为小写',
  TRIM: '去除首尾空格',
  SUBSTITUTE: '替换文本',
  REPLACE: '替换指定位置的文本',
  FIND: '查找文本位置',
  REPT: '重复文本指定次数',
  TEXT: '将数字按格式转换为文本',
  VALUE: '将文本转换为数字',
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
  XOR: '逻辑异或',
  ISBLANK: '判断是否为空',
  ISERROR: '判断是否为错误值',
  ISNUMBER: '判断是否为数字',
  ISTEXT: '判断是否为文本',
  ISDATE: '判断是否为日期',
  BLANK: '返回空值',
  NA: '返回 N/A 错误',
  ERROR: '返回自定义错误',
  COUNT: '计数',
  COUNTA: '计数非空值',
  COUNTBLANK: '计数空值',
  COUNTIF: '条件计数',
  SUMIF: '条件求和',
  AVERAGEIF: '条件平均值',
  STDEV: '返回标准差',
  VAR: '返回方差',
  MEDIAN: '返回中位数',
  MODE: '返回众数',
  RANK: '返回排名',
  UNIQUE: '返回去重后的数组'
}
