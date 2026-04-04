import * as XLSX from "xlsx";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import { FieldType, type CellValue } from "@/types";

export interface ExportOptions {
  filename?: string;
  sheetName?: string;
  includeHeaders?: boolean;
}

export interface ImportResult {
  headers: string[];
  data: CellValue[][];
  totalRows: number;
}

// 公共格式化函数 - 用于 Excel 导出
function formatValueForExcel(value: CellValue, field: FieldEntity): unknown {
  if (value === null || value === undefined) return "";

  switch (field.type) {
    case FieldType.SINGLE_SELECT:
      // 将选项 ID 转换为选项名称
      if (typeof value === "string") {
        const options = field.options?.choices as
          | Array<{ id: string; name: string; color: string }>
          | undefined;
        const option = options?.find((opt) => opt.id === value);
        return option?.name || value;
      }
      return value;

    case FieldType.MULTI_SELECT:
      // 将选项 ID 数组转换为选项名称数组
      if (Array.isArray(value)) {
        const options = field.options?.choices as
          | Array<{ id: string; name: string; color: string }>
          | undefined;
        const names = value.map((id) => {
          const option = options?.find((opt) => opt.id === id);
          return option?.name || id;
        });
        return names.join(", ");
      }
      return value;

    case FieldType.CHECKBOX:
      return value ? "是" : "否";

    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      if (typeof value === "number") {
        return new Date(value).toLocaleDateString("zh-CN");
      }
      return value;

    case FieldType.MEMBER:
      if (Array.isArray(value)) {
        return value
          .map((m) =>
            typeof m === "object" && m !== null && "name" in m
              ? m.name
              : String(m),
          )
          .join(", ");
      }
      return value;

    case FieldType.ATTACHMENT:
      if (Array.isArray(value)) {
        return value
          .map((f) =>
            typeof f === "object" && f !== null && "name" in f
              ? f.name
              : String(f),
          )
          .join(", ");
      }
      return value;

    default:
      return value;
  }
}

// 公共 CSV 转义函数
function escapeCSV(value: unknown): string {
  const str = String(value ?? "");
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

// 公共格式化函数 - 用于 CSV 导出
function formatValueForCSV(value: CellValue, field: FieldEntity): string {
  if (value === null || value === undefined) return "";

  switch (field.type) {
    case FieldType.SINGLE_SELECT:
      // 将选项 ID 转换为选项名称
      if (typeof value === "string") {
        const options = field.options?.choices as
          | Array<{ id: string; name: string; color: string }>
          | undefined;
        const option = options?.find((opt) => opt.id === value);
        return option?.name || value;
      }
      return String(value);

    case FieldType.MULTI_SELECT:
      // 将选项 ID 数组转换为选项名称数组
      if (Array.isArray(value)) {
        const options = field.options?.choices as
          | Array<{ id: string; name: string; color: string }>
          | undefined;
        const names = value.map((id) => {
          const option = options?.find((opt) => opt.id === id);
          return option?.name || id;
        });
        return names.join("; ");
      }
      return String(value);

    case FieldType.CHECKBOX:
      return value ? "是" : "否";

    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      if (typeof value === "number") {
        return new Date(value).toLocaleDateString("zh-CN");
      }
      return String(value);

    default:
      return String(value);
  }
}

export class ExcelExporter {
  static exportTable(
    tableName: string,
    fields: FieldEntity[],
    records: RecordEntity[],
    options: ExportOptions = {},
  ): void {
    const {
      filename = tableName,
      sheetName = tableName,
      includeHeaders = true,
    } = options;

    const headers = fields.map((f) => f.name);

    const data = records.map((record) => {
      return fields.map((field) => {
        const value = record.values[field.id];
        return formatValueForExcel(value, field);
      });
    });

    const wsData = includeHeaders ? [headers, ...data] : data;
    const ws = XLSX.utils.aoa_to_sheet(wsData);

    const colWidths = fields.map((field, index) => {
      const maxLen = Math.max(
        field.name.length,
        ...data.slice(0, 100).map((row) => String(row[index] || "").length),
      );
      return { wch: Math.min(Math.max(maxLen + 2, 10), 50) };
    });
    ws["!cols"] = colWidths;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, sheetName);

    XLSX.writeFile(wb, `${filename}.xlsx`);
  }

  static async importTable(file: File): Promise<ImportResult> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const arrayData = new Uint8Array(e.target?.result as ArrayBuffer);
          const workbook = XLSX.read(arrayData, { type: "array" });
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
          const jsonData = XLSX.utils.sheet_to_json(firstSheet, {
            header: 1,
            raw: false,
            defval: "",
          }) as CellValue[][];

          if (jsonData.length === 0) {
            resolve({ headers: [], data: [], totalRows: 0 });
            return;
          }

          const headers = jsonData[0] as string[];
          const rows = jsonData.slice(1);

          resolve({
            headers,
            data: rows,
            totalRows: rows.length,
          });
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error("文件读取失败"));
      reader.readAsArrayBuffer(file);
    });
  }
}

export class CSVExporter {
  static exportTable(
    tableName: string,
    fields: FieldEntity[],
    records: RecordEntity[],
    options: ExportOptions = {},
  ): void {
    const { filename = tableName, includeHeaders = true } = options;

    const headers = fields.map((f) => escapeCSV(f.name));
    const data = records.map((record) => {
      return fields.map((field) => {
        const value = record.values[field.id];
        return escapeCSV(formatValueForCSV(value, field));
      });
    });

    const csvContent = (includeHeaders ? [headers.join(","), "\n"] : [])
      .concat(data.map((row) => row.join(",")))
      .join("\n");

    const BOM = "\uFEFF";
    const blob = new Blob([BOM + csvContent], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}.csv`;
    link.click();

    URL.revokeObjectURL(url);
  }

  static async importTable(file: File): Promise<ImportResult> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          const lines = text.split(/\r?\n/);

          if (lines.length === 0) {
            resolve({ headers: [], data: [], totalRows: 0 });
            return;
          }

          const headers = this.parseCSVLine(lines[0]);
          const data = lines
            .slice(1)
            .filter((line) => line.trim())
            .map((line) => this.parseCSVLine(line));

          resolve({
            headers,
            data,
            totalRows: data.length,
          });
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error("文件读取失败"));
      reader.readAsText(file, "UTF-8");
    });
  }

  private static parseCSVLine(line: string): string[] {
    const result: string[] = [];
    let current = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];

      if (inQuotes) {
        if (char === '"') {
          if (line[i + 1] === '"') {
            current += '"';
            i++;
          } else {
            inQuotes = false;
          }
        } else {
          current += char;
        }
      } else {
        if (char === '"') {
          inQuotes = true;
        } else if (char === ",") {
          result.push(current);
          current = "";
        } else {
          current += char;
        }
      }
    }

    result.push(current);
    return result;
  }
}

export class JSONExporter {
  static exportTable(
    tableName: string,
    fields: FieldEntity[],
    records: RecordEntity[],
    options: ExportOptions = {},
  ): void {
    const { filename = tableName } = options;

    const fieldMap = new Map(fields.map((f) => [f.id, f]));

    const exportData = records.map((record) => {
      const obj: Record<string, CellValue> = {};

      for (const [fieldId, value] of Object.entries(record.values)) {
        const field = fieldMap.get(fieldId);
        if (field) {
          obj[field.name] = value;
        }
      }

      return obj;
    });

    const jsonContent = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonContent], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}.json`;
    link.click();

    URL.revokeObjectURL(url);
  }

  static async importTable(file: File): Promise<ImportResult> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          const jsonData = JSON.parse(text);

          if (!Array.isArray(jsonData)) {
            reject(new Error("JSON 格式错误：应为数组"));
            return;
          }

          if (jsonData.length === 0) {
            resolve({ headers: [], data: [], totalRows: 0 });
            return;
          }

          const headers = Object.keys(jsonData[0]);
          const data = jsonData.map((item) =>
            headers.map((h) => item[h] ?? ""),
          );

          resolve({
            headers,
            data,
            totalRows: data.length,
          });
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error("文件读取失败"));
      reader.readAsText(file, "UTF-8");
    });
  }
}

export const exportUtils = {
  excel: ExcelExporter,
  csv: CSVExporter,
  json: JSONExporter,
};

// 独立导出函数
export async function exportToExcel(
  records: RecordEntity[],
  fields: FieldEntity[],
  options: ExportOptions = {},
): Promise<Uint8Array> {
  const { sheetName = "Sheet1", includeHeaders = true } = options;

  const headers = fields.map((f) => f.name);

  const data = records.map((record) => {
    return fields.map((field) => {
      const value = record.values[field.id];
      return formatValueForExcel(value, field);
    });
  });

  const wsData = includeHeaders ? [headers, ...data] : data;
  const ws = XLSX.utils.aoa_to_sheet(wsData);

  const colWidths = fields.map((field, index) => {
    const maxLen = Math.max(
      field.name.length,
      ...data.slice(0, 100).map((row) => String(row[index] || "").length),
    );
    return { wch: Math.min(Math.max(maxLen + 2, 10), 50) };
  });
  ws["!cols"] = colWidths;

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);

  return XLSX.write(wb, { bookType: "xlsx", type: "array" });
}

export function exportToCSV(
  records: RecordEntity[],
  fields: FieldEntity[],
  options: ExportOptions = {},
): string {
  const { includeHeaders = true } = options;

  const headers = fields.map((f) => escapeCSV(f.name));
  const data = records.map((record) => {
    return fields.map((field) => {
      const value = record.values[field.id];
      return escapeCSV(formatValueForCSV(value, field));
    });
  });

  const csvContent = (includeHeaders ? [headers.join(","), "\n"] : [])
    .concat(data.map((row) => row.join(",")))
    .join("\n");

  return "\uFEFF" + csvContent;
}

export function exportToJSON(
  records: RecordEntity[],
  fields: FieldEntity[],
  _options: ExportOptions = {},
): string {
  const fieldMap = new Map(fields.map((f) => [f.id, f]));

  const exportData = records.map((record) => {
    const obj: Record<string, CellValue> = {};

    for (const [fieldId, value] of Object.entries(record.values)) {
      const field = fieldMap.get(fieldId);
      if (field) {
        obj[field.name] = value;
      }
    }

    return obj;
  });

  return JSON.stringify(exportData, null, 2);
}
