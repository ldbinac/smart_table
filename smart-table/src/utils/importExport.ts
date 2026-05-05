import * as XLSX from 'xlsx';
import type { FieldEntity } from '@/db/schema';
import { FieldType, type CellValue, type FieldTypeValue, type FieldOption } from '@/types';

export interface ParsedFileData {
  data: Record<string, any>[];
  columns: string[];
  format: string;
}

export interface FieldMapping {
  sourceColumn: string;
  targetFieldId: string | null;
  targetFieldName: string | null;
  targetFieldType: FieldTypeValue | null;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * 解析 Excel 文件
 */
export function parseExcel(file: File): Promise<ParsedFileData> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = XLSX.read(data, { type: 'binary' });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 }) as any[][];
        
        if (jsonData.length === 0) {
          reject(new Error('文件为空'));
          return;
        }
        
        const headers = jsonData[0] as string[];
        const rows = jsonData.slice(1).map((row) => {
          const obj: Record<string, any> = {};
          headers.forEach((header, index) => {
            obj[header] = row[index] ?? null;
          });
          return obj;
        });
        
        resolve({
          data: rows,
          columns: headers,
          format: 'excel'
        });
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = () => reject(new Error('读取文件失败'));
    reader.readAsBinaryString(file);
  });
}

/**
 * 解析 CSV 文件
 */
export function parseCSV(file: File): Promise<ParsedFileData> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const lines = content.split('\n').filter(line => line.trim());
        
        if (lines.length === 0) {
          reject(new Error('文件为空'));
          return;
        }
        
        // 解析 CSV（简单实现，处理引号包裹的情况）
        const parseCSVLine = (line: string): string[] => {
          const result: string[] = [];
          let current = '';
          let inQuotes = false;
          
          for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
              if (inQuotes && line[i + 1] === '"') {
                current += '"';
                i++;
              } else {
                inQuotes = !inQuotes;
              }
            } else if (char === ',' && !inQuotes) {
              result.push(current.trim());
              current = '';
            } else {
              current += char;
            }
          }
          result.push(current.trim());
          return result;
        };
        
        const headers = parseCSVLine(lines[0]);
        const rows = lines.slice(1).map((line) => {
          const values = parseCSVLine(line);
          const obj: Record<string, any> = {};
          headers.forEach((header, index) => {
            obj[header] = values[index] ?? null;
          });
          return obj;
        });
        
        resolve({
          data: rows,
          columns: headers,
          format: 'csv'
        });
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = () => reject(new Error('读取文件失败'));
    reader.readAsText(file);
  });
}

/**
 * 解析 JSON 文件
 */
export function parseJSON(file: File): Promise<ParsedFileData> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const data = JSON.parse(content);
        
        if (!Array.isArray(data)) {
          reject(new Error('JSON 文件必须是数组格式'));
          return;
        }
        
        if (data.length === 0) {
          reject(new Error('文件为空'));
          return;
        }
        
        const columns = Object.keys(data[0]);
        
        resolve({
          data,
          columns,
          format: 'json'
        });
      } catch (error) {
        reject(new Error('JSON 格式错误'));
      }
    };
    reader.onerror = () => reject(new Error('读取文件失败'));
    reader.readAsText(file);
  });
}

/**
 * 自动检测文件类型并解析
 */
export async function parseFile(file: File): Promise<ParsedFileData> {
  const extension = file.name.split('.').pop()?.toLowerCase();
  
  switch (extension) {
    case 'xlsx':
    case 'xls':
      return parseExcel(file);
    case 'csv':
      return parseCSV(file);
    case 'json':
      return parseJSON(file);
    default:
      throw new Error(`不支持的文件格式: ${extension}`);
  }
}

/**
 * 自动匹配字段
 */
/**
 * 不可导入的字段类型（系统自动生成或只读）
 */
const NON_IMPORTABLE_FIELD_TYPES: FieldTypeValue[] = [
  FieldType.AUTO_NUMBER,
  FieldType.CREATED_BY,
  FieldType.CREATED_TIME,
  FieldType.UPDATED_BY,
  FieldType.UPDATED_TIME,
];

export function autoMatchFields(
  sourceColumns: string[],
  targetFields: FieldEntity[]
): FieldMapping[] {
  // 过滤掉不可导入的字段类型
  const importableFields = targetFields.filter(
    (field) => !NON_IMPORTABLE_FIELD_TYPES.includes(field.type as FieldTypeValue)
  );

  return sourceColumns.map((column) => {
    // 尝试找到匹配的字段（名称相同或相似）
    const matchedField = importableFields.find(
      (field) => field.name.toLowerCase() === column.toLowerCase() ||
                field.name.toLowerCase().includes(column.toLowerCase()) ||
                column.toLowerCase().includes(field.name.toLowerCase())
    );
    
    return {
      sourceColumn: column,
      targetFieldId: matchedField?.id ?? null,
      targetFieldName: matchedField?.name ?? null,
      targetFieldType: matchedField?.type as FieldTypeValue ?? null
    };
  });
}

/**
 * 获取字段的选项列表
 */
export function getFieldOptions(field?: FieldEntity): FieldOption[] {
  if (!field || !field.options) return [];
  return (field.options.choices || field.options.options || []) as FieldOption[];
}

/**
 * 将选项名称转换为选项ID
 */
function findOptionIdByName(options: FieldOption[], name: string): string | null {
  const trimmedName = name.trim();
  if (!trimmedName) return null;

  // 首先尝试精确匹配（不区分大小写）
  const exactMatch = options.find(
    (opt) => opt.name.toLowerCase() === trimmedName.toLowerCase()
  );
  if (exactMatch) return exactMatch.id;

  // 然后尝试包含匹配
  const partialMatch = options.find(
    (opt) =>
      opt.name.toLowerCase().includes(trimmedName.toLowerCase()) ||
      trimmedName.toLowerCase().includes(opt.name.toLowerCase())
  );
  if (partialMatch) return partialMatch.id;

  return null;
}

/**
 * 将选项ID转换为选项名称
 */
export function findOptionNameById(options: FieldOption[], id: string): string | null {
  const option = options.find((opt) => opt.id === id);
  return option?.name ?? null;
}

/**
 * 转换值为目标字段类型
 * @param value 原始值
 * @param targetType 目标字段类型
 * @param field 字段定义（用于单选/多选字段的选项映射）
 */
export function convertValue(
  value: any,
  targetType: FieldTypeValue,
  field?: FieldEntity
): CellValue {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  switch (targetType) {
    case FieldType.SINGLE_LINE_TEXT:
    case FieldType.LONG_TEXT:
    case FieldType.RICH_TEXT:
    case FieldType.URL:
    case FieldType.EMAIL:
    case FieldType.PHONE:
      return String(value);

    case FieldType.NUMBER:
    case FieldType.RATING:
    case FieldType.PROGRESS:
      const num = Number(value);
      return isNaN(num) ? null : num;

    case FieldType.DATE:
    case FieldType.DATE_TIME:
      // 处理多种日期格式
      if (typeof value === 'number') {
        // Excel 日期序列号
        if (value > 30000 && value < 50000) {
          // Excel 日期序列号转时间戳
          const excelEpoch = new Date(1899, 11, 30);
          return excelEpoch.getTime() + value * 24 * 60 * 60 * 1000;
        }
        return value;
      }
      if (typeof value === 'string') {
        const date = new Date(value);
        return isNaN(date.getTime()) ? null : date.getTime();
      }
      return null;

    case FieldType.CHECKBOX:
      if (typeof value === 'boolean') return value;
      if (typeof value === 'string') {
        return value.toLowerCase() === 'true' || value === '1' || value === '是' || value === 'yes';
      }
      if (typeof value === 'number') return value !== 0;
      return false;

    case FieldType.SINGLE_SELECT: {
      const strValue = String(value).trim();
      if (!strValue) return null;

      const options = getFieldOptions(field);
      if (options.length === 0) {
        // 没有选项定义时，如果值看起来像ID则直接使用
        return strValue;
      }

      // 首先检查值是否已经是有效的选项ID
      const existingOption = options.find((opt) => opt.id === strValue);
      if (existingOption) return strValue;

      // 尝试按名称查找选项ID
      const optionId = findOptionIdByName(options, strValue);
      return optionId || strValue;
    }

    case FieldType.MULTI_SELECT: {
      const options = getFieldOptions(field);

      // 将输入值标准化为字符串数组
      let valueNames: string[];
      if (Array.isArray(value)) {
        valueNames = value.map((v) => String(v).trim()).filter(Boolean);
      } else if (typeof value === 'string') {
        // 尝试解析为数组（逗号分隔）
        valueNames = value.split(/[,，]/).map((s) => s.trim()).filter(Boolean);
      } else {
        valueNames = [String(value).trim()].filter(Boolean);
      }

      if (valueNames.length === 0) return null;

      if (options.length === 0) {
        // 没有选项定义时，如果值看起来像ID则直接使用
        return valueNames;
      }

      // 将每个值转换为选项ID
      return valueNames.map((name) => {
        // 首先检查是否已经是有效的选项ID
        const existingOption = options.find((opt) => opt.id === name);
        if (existingOption) return name;

        // 尝试按名称查找选项ID
        const optionId = findOptionIdByName(options, name);
        return optionId || name;
      });
    }

    default:
      return String(value);
  }
}

/**
 * 将导入数据行转换为记录值
 * @param rowData 行数据
 * @param fieldMappings 字段映射
 * @param fields 字段定义列表（用于单选/多选字段的选项映射）
 */
export function convertImportData(
  rowData: Record<string, any>,
  fieldMappings: FieldMapping[],
  fields?: FieldEntity[]
): Record<string, CellValue> {
  const result: Record<string, CellValue> = {};

  fieldMappings.forEach((mapping) => {
    // 跳过不可导入的字段类型
    if (mapping.targetFieldType && NON_IMPORTABLE_FIELD_TYPES.includes(mapping.targetFieldType)) {
      return;
    }
    if (mapping.targetFieldId && mapping.targetFieldType) {
      const value = rowData[mapping.sourceColumn];
      // 查找字段定义以支持单选/多选选项映射
      const field = fields?.find((f) => f.id === mapping.targetFieldId);
      result[mapping.targetFieldId] = convertValue(value, mapping.targetFieldType, field);
    }
  });

  return result;
}

/**
 * 验证单行数据
 */
export function validateRow(
  rowData: Record<string, CellValue>,
  fields: FieldEntity[]
): ValidationResult {
  const errors: string[] = [];

  fields.forEach((field) => {
    const value = rowData[field.id];

    if (field.options?.required) {
      if (value === null || value === undefined || value === '' ||
          (Array.isArray(value) && value.length === 0)) {
        errors.push(`${field.name} 为必填项`);
      }
    }

    // 验证邮箱格式
    if (field.type === FieldType.EMAIL && value) {
      const email = String(value);
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        errors.push(`${field.name} 格式不正确`);
      }
    }

    // 验证手机格式
    if (field.type === FieldType.PHONE && value) {
      const phone = String(value);
      if (!/^1[3-9]\d{9}$/.test(phone)) {
        errors.push(`${field.name} 格式不正确`);
      }
    }

    // 验证 URL 格式
    if (field.type === FieldType.URL && value) {
      const url = String(value);
      try {
        new URL(url);
      } catch {
        errors.push(`${field.name} 格式不正确`);
      }
    }

    // 验证单选字段值是否为有效选项ID
    if (field.type === FieldType.SINGLE_SELECT && value) {
      const options = getFieldOptions(field);
      if (options.length > 0) {
        const strValue = String(value);
        const validOption = options.find((opt) => opt.id === strValue);
        if (!validOption) {
          errors.push(`${field.name} 的值不是有效的选项`);
        }
      }
    }

    // 验证多选字段值是否均为有效选项ID
    if (field.type === FieldType.MULTI_SELECT && value) {
      const options = getFieldOptions(field);
      if (options.length > 0 && Array.isArray(value)) {
        const invalidValues = value.filter((v) => {
          const strV = String(v);
          return !options.find((opt) => opt.id === strV);
        });
        if (invalidValues.length > 0) {
          errors.push(`${field.name} 包含无效选项: ${invalidValues.join(', ')}`);
        }
      }
    }
  });
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * 导出数据为 Excel
 */
export function exportToExcel(
  data: Record<string, any>[],
  columns: { key: string; title: string }[],
  filename: string
): void {
  const exportData = data.map((row) => {
    const obj: Record<string, any> = {};
    columns.forEach((col) => {
      obj[col.title] = row[col.key];
    });
    return obj;
  });
  
  const worksheet = XLSX.utils.json_to_sheet(exportData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Sheet1');
  XLSX.writeFile(workbook, `${filename}.xlsx`);
}

/**
 * 导出数据为 CSV
 */
export function exportToCSV(
  data: Record<string, any>[],
  columns: { key: string; title: string }[],
  filename: string
): void {
  const headers = columns.map((col) => col.title).join(',');
  const rows = data.map((row) => {
    return columns
      .map((col) => {
        const value = row[col.key];
        if (value === null || value === undefined) return '';
        const str = String(value);
        // 如果包含逗号或引号，需要包裹引号
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      })
      .join(',');
  });
  
  const csvContent = [headers, ...rows].join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

/**
 * 导出数据为 JSON
 */
export function exportToJSON(
  data: Record<string, any>[],
  filename: string
): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}
