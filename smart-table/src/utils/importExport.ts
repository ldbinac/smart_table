import * as XLSX from 'xlsx';
import type { FieldEntity } from '@/db/schema';
import { FieldType, type CellValue, type FieldTypeValue } from '@/types';

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
export function autoMatchFields(
  sourceColumns: string[],
  targetFields: FieldEntity[]
): FieldMapping[] {
  return sourceColumns.map((column) => {
    // 尝试找到匹配的字段（名称相同或相似）
    const matchedField = targetFields.find(
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
 * 转换值为目标字段类型
 */
export function convertValue(value: any, targetType: FieldTypeValue): CellValue {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  
  switch (targetType) {
    case FieldType.TEXT:
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
      
    case FieldType.SINGLE_SELECT:
      return String(value);
      
    case FieldType.MULTI_SELECT:
      if (Array.isArray(value)) return value.map(String);
      if (typeof value === 'string') {
        // 尝试解析为数组（逗号分隔）
        return value.split(/[,，]/).map(s => s.trim()).filter(Boolean);
      }
      return [String(value)];
      
    default:
      return String(value);
  }
}

/**
 * 将导入数据行转换为记录值
 */
export function convertImportData(
  rowData: Record<string, any>,
  fieldMappings: FieldMapping[]
): Record<string, CellValue> {
  const result: Record<string, CellValue> = {};
  
  fieldMappings.forEach((mapping) => {
    if (mapping.targetFieldId && mapping.targetFieldType) {
      const value = rowData[mapping.sourceColumn];
      result[mapping.targetFieldId] = convertValue(value, mapping.targetFieldType);
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
    if (field.options?.required) {
      const value = rowData[field.id];
      if (value === null || value === undefined || value === '' || 
          (Array.isArray(value) && value.length === 0)) {
        errors.push(`${field.name} 为必填项`);
      }
    }
    
    // 验证邮箱格式
    if (field.type === FieldType.EMAIL && rowData[field.id]) {
      const email = String(rowData[field.id]);
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        errors.push(`${field.name} 格式不正确`);
      }
    }
    
    // 验证手机格式
    if (field.type === FieldType.PHONE && rowData[field.id]) {
      const phone = String(rowData[field.id]);
      if (!/^1[3-9]\d{9}$/.test(phone)) {
        errors.push(`${field.name} 格式不正确`);
      }
    }
    
    // 验证 URL 格式
    if (field.type === FieldType.URL && rowData[field.id]) {
      const url = String(rowData[field.id]);
      try {
        new URL(url);
      } catch {
        errors.push(`${field.name} 格式不正确`);
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
