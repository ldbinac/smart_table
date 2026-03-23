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
    const timestamp = Number(date)
    if (isNaN(timestamp)) return '#ERROR'
    return dayjs(timestamp).year()
  },
  
  MONTH: (date: unknown) => {
    const timestamp = Number(date)
    if (isNaN(timestamp)) return '#ERROR'
    return dayjs(timestamp).month() + 1
  },
  
  DAY: (date: unknown) => {
    const timestamp = Number(date)
    if (isNaN(timestamp)) return '#ERROR'
    return dayjs(timestamp).date()
  },
  
  HOUR: (date: unknown) => {
    const timestamp = Number(date)
    if (isNaN(timestamp)) return '#ERROR'
    return dayjs(timestamp).hour()
  },
  
  MINUTE: (date: unknown) => {
    const timestamp = Number(date)
    if (isNaN(timestamp)) return '#ERROR'
    return dayjs(timestamp).minute()
  },
  
  SECOND: (date: unknown) => {
    const timestamp = Number(date)
    if (isNaN(timestamp)) return '#ERROR'
    return dayjs(timestamp).second()
  },
  
  DATEDIF: (startDate: unknown, endDate: unknown, unit: unknown) => {
    const start = dayjs(Number(startDate))
    const end = dayjs(Number(endDate))
    const u = String(unit ?? 'D').toUpperCase()
    
    if (!start.isValid() || !end.isValid()) return '#ERROR'
    
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
  
  DATEADD: (date: unknown, amount: unknown, unit: unknown) => {
    const d = dayjs(Number(date))
    const amt = Number(amount)
    const u = String(unit ?? 'day').toLowerCase()
    
    if (!d.isValid() || isNaN(amt)) return '#ERROR'
    
    const result = d.add(amt, u as dayjs.ManipulateType)
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

export const functionCategories = {
  math: ['SUM', 'AVG', 'MAX', 'MIN', 'ROUND', 'CEILING', 'FLOOR', 'ABS', 'MOD', 'POWER', 'SQRT'],
  text: ['CONCAT', 'LEFT', 'RIGHT', 'LEN', 'UPPER', 'LOWER', 'TRIM', 'SUBSTITUTE', 'REPLACE', 'FIND'],
  date: ['TODAY', 'NOW', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'DATEDIF', 'DATEADD'],
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
  DATEDIF: '计算两个日期之间的差',
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
