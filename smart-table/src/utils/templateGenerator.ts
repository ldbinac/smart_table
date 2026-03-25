import * as XLSX from 'xlsx';
import type { FieldEntity } from '@/db/schema';
import { FieldType } from '@/types';

/**
 * 生成导入模板数据
 */
export function generateTemplateData(fields: FieldEntity[]): {
  headers: string[];
  sampleData: Record<string, any>;
  fieldDescriptions: Record<string, string>;
} {
  const headers: string[] = [];
  const sampleData: Record<string, any> = {};
  const fieldDescriptions: Record<string, string> = {};

  fields.forEach((field) => {
    if (field.isSystem) return; // 跳过系统字段

    headers.push(field.name);
    sampleData[field.name] = getSampleValue(field);
    fieldDescriptions[field.name] = getFieldDescription(field);
  });

  return { headers, sampleData, fieldDescriptions };
}

/**
 * 获取字段的示例值
 */
function getSampleValue(field: FieldEntity): any {
  switch (field.type) {
    case FieldType.TEXT:
      return '示例文本';

    case FieldType.NUMBER:
      return 100;

    case FieldType.DATE:
      return new Date().toISOString().slice(0, 16).replace('T', ' ');

    case FieldType.SINGLE_SELECT:
      const options = (field.options?.options as Array<{ name: string }>) || [];
      return options[0]?.name || '选项1';

    case FieldType.MULTI_SELECT:
      const multiOptions = (field.options?.options as Array<{ name: string }>) || [];
      return multiOptions.slice(0, 2).map((o) => o.name).join(', ') || '选项1, 选项2';

    case FieldType.CHECKBOX:
      return '是';

    case FieldType.EMAIL:
      return 'example@email.com';

    case FieldType.PHONE:
      return '13800138000';

    case FieldType.URL:
      return 'https://example.com';

    case FieldType.RATING:
      return 5;

    case FieldType.PROGRESS:
      return 80;

    default:
      return '';
  }
}

/**
 * 获取字段描述
 */
function getFieldDescription(field: FieldEntity): string {
  let description = '';

  switch (field.type) {
    case FieldType.TEXT:
      description = '文本类型';
      break;
    case FieldType.NUMBER:
      description = '数字类型';
      break;
    case FieldType.DATE:
      description = '日期时间格式，如: 2024-01-15 14:30';
      break;
    case FieldType.SINGLE_SELECT:
      const singleOptions = (field.options?.options as Array<{ name: string }>) || [];
      description = `单选，可选值: ${singleOptions.map((o) => o.name).join(', ')}`;
      break;
    case FieldType.MULTI_SELECT:
      const multiOptions = (field.options?.options as Array<{ name: string }>) || [];
      description = `多选，多个值用逗号分隔，可选值: ${multiOptions.map((o) => o.name).join(', ')}`;
      break;
    case FieldType.CHECKBOX:
      description = '复选框，可填: 是/否、true/false、1/0';
      break;
    case FieldType.EMAIL:
      description = '邮箱格式，如: example@email.com';
      break;
    case FieldType.PHONE:
      description = '手机号码格式，如: 13800138000';
      break;
    case FieldType.URL:
      description = 'URL链接格式，如: https://example.com';
      break;
    case FieldType.RATING:
      description = '评分，1-5之间的数字';
      break;
    case FieldType.PROGRESS:
      description = '进度，0-100之间的数字';
      break;
    default:
      description = field.type;
  }

  if (field.options?.required) {
    description += ' (必填)';
  }

  return description;
}

/**
 * 导出 Excel 模板
 */
export function exportExcelTemplate(fields: FieldEntity[], filename: string): void {
  const { headers, sampleData, fieldDescriptions } = generateTemplateData(fields);

  // 创建工作表数据
  const worksheetData: any[][] = [];

  // 第一行：字段说明
  worksheetData.push(headers.map((h) => fieldDescriptions[h]));

  // 第二行：列标题
  worksheetData.push(headers);

  // 第三行：示例数据
  worksheetData.push(headers.map((h) => sampleData[h]));

  // 创建工作表
  const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);

  // 设置列宽
  const colWidths = headers.map(() => ({ wch: 20 }));
  worksheet['!cols'] = colWidths;

  // 创建工作簿
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, '导入模板');

  // 下载文件
  XLSX.writeFile(workbook, `${filename}_导入模板.xlsx`);
}

/**
 * 导出 CSV 模板
 */
export function exportCSVTemplate(fields: FieldEntity[], filename: string): void {
  const { headers, sampleData } = generateTemplateData(fields);

  // CSV 内容
  const rows: string[] = [];

  // 列标题
  rows.push(headers.join(','));

  // 示例数据
  const sampleRow = headers
    .map((h) => {
      const value = String(sampleData[h] || '');
      // 如果包含逗号或引号，需要包裹引号
      if (value.includes(',') || value.includes('"') || value.includes('\n')) {
        return `"${value.replace(/"/g, '""')}"`;
      }
      return value;
    })
    .join(',');
  rows.push(sampleRow);

  // 创建并下载文件
  const csvContent = rows.join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}_导入模板.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

/**
 * 导出 JSON 模板
 */
export function exportJSONTemplate(fields: FieldEntity[], filename: string): void {
  const { sampleData } = generateTemplateData(fields);

  // 创建示例数据数组
  const templateData = [sampleData];

  // 添加字段说明
  const templateWithDescription = {
    说明: '这是一个导入模板示例，请按照此格式准备数据',
    字段说明: fields
      .filter((f) => !f.isSystem)
      .reduce((acc, field) => {
        acc[field.name] = getFieldDescription(field);
        return acc;
      }, {} as Record<string, string>),
    数据: templateData,
  };

  // 创建并下载文件
  const blob = new Blob([JSON.stringify(templateWithDescription, null, 2)], {
    type: 'application/json',
  });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}_导入模板.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

/**
 * 根据文件格式导出模板
 */
export function exportTemplate(
  fields: FieldEntity[],
  filename: string,
  format: 'excel' | 'csv' | 'json' = 'excel'
): void {
  switch (format) {
    case 'excel':
      exportExcelTemplate(fields, filename);
      break;
    case 'csv':
      exportCSVTemplate(fields, filename);
      break;
    case 'json':
      exportJSONTemplate(fields, filename);
      break;
    default:
      exportExcelTemplate(fields, filename);
  }
}
