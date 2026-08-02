/**
 * 主从表数据服务
 * 封装主从表子表数据的获取、创建关联、列配置构建逻辑
 */
import { apiClient } from "@/api/client";
import { FieldType } from "@/types/fields";
import { fieldService } from "@/db/services/fieldService";
import { formatDate, formatDateTime } from "@/utils/timezone";

// ==================== 类型定义 ====================

export interface LinkedRecordDetail {
  id: string;
  values: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LinkedRecordsDetailResponse {
  records: LinkedRecordDetail[];
  fields: any[]; // 目标表字段定义数组
  total: number;
  page: number;
  per_page: number;
  link_relation: {
    id: string;
    source_table_id: string;
    target_table_id: string;
    source_field_id: string;
    target_field_id: string | null;
    relationship_type:
      | "one_to_one"
      | "one_to_many"
      | "many_to_one"
      | "many_to_many";
    bidirectional: boolean;
  };
}

export interface GetLinkedRecordsDetailParams {
  page?: number;
  per_page?: number;
  keyword?: string;
}

export interface CreateAndLinkRecordResponse {
  record: LinkedRecordDetail;
  link_value: {
    id: string;
    link_relation_id: string;
    source_record_id: string;
    target_record_id: string;
  };
}

// ==================== 字段定义缓存 ====================

/**
 * 字段定义缓存
 * 缓存目标表的字段定义，减少重复请求
 */
class FieldDefinitionCache {
  private cache = new Map<string, { data: any[]; timestamp: number }>();
  private readonly TTL = 5 * 60 * 1000; // 5分钟

  get(tableId: string): any[] | null {
    const entry = this.cache.get(tableId);
    if (!entry) return null;

    // 检查是否过期
    if (Date.now() - entry.timestamp > this.TTL) {
      this.cache.delete(tableId);
      return null;
    }

    return entry.data;
  }

  set(tableId: string, fields: any[]): void {
    this.cache.set(tableId, {
      data: fields,
      timestamp: Date.now(),
    });
  }

  invalidate(tableId: string): void {
    this.cache.delete(tableId);
  }

  clear(): void {
    this.cache.clear();
  }
}

// 全局缓存实例
export const fieldDefinitionCache = new FieldDefinitionCache();

// ==================== API 方法 ====================

/**
 * 获取主记录关联的子表记录详情（含目标表字段定义）
 * GET /records/{recordId}/links/{fieldId}/details?page=&per_page=&keyword=
 *
 * 后端返回格式为 { success, message, data: {...} }，
 * apiClient.get 会返回 data 部分。
 */
export async function getLinkedRecordsDetail(
  recordId: string,
  fieldId: string,
  params?: GetLinkedRecordsDetailParams
): Promise<LinkedRecordsDetailResponse> {
  const queryParams: Record<string, unknown> = {};

  if (params?.page !== undefined) {
    queryParams.page = params.page;
  }
  if (params?.per_page !== undefined) {
    queryParams.per_page = params.per_page;
  }
  if (params?.keyword) {
    queryParams.keyword = params.keyword;
  }

  return apiClient.get<LinkedRecordsDetailResponse>(
    `/records/${recordId}/links/${fieldId}/details`,
    queryParams
  );
}

/**
 * 创建新记录并自动建立与主记录的关联
 * POST /records/{recordId}/links/{fieldId}/records，请求体 { values }
 */
export async function createAndLinkRecord(
  recordId: string,
  fieldId: string,
  values: Record<string, unknown>
): Promise<CreateAndLinkRecordResponse> {
  return apiClient.post<CreateAndLinkRecordResponse>(
    `/records/${recordId}/links/${fieldId}/records`,
    { values }
  );
}

// ==================== 列配置构建 ====================

/**
 * 根据目标表字段定义构建 VTable 子表列配置
 * 字段类型映射参考 VTableView.vue 的 getCellTypeConfig 方法（简化版）
 *
 * 子表列统一使用 cellType: 'text'，对特定类型添加 fieldFormat 进行格式化。
 * 子表列不需要编辑器配置（编辑通过事件处理），不需要 customRender。
 */
export function buildSubTableColumns(
  targetFields: any[]
): any[] {
  const columns: any[] = [];

  for (const field of targetFields) {
    const column: Record<string, any> = {
      field: field.id,
      title: field.name,
      width: 150,
      cellType: "text",
    };

    const fieldType = field.type;

    // 数字类型字段：number, percent, currency, duration - 添加数字格式化
    if (
      fieldType === FieldType.NUMBER ||
      fieldType === FieldType.PERCENT ||
      fieldType === FieldType.CURRENCY ||
      fieldType === FieldType.DURATION
    ) {
      column.fieldFormat = (record: any) => {
        const value = record?.[field.id];
        if (value === null || value === undefined || value === "") return "";
        const num = Number(value);
        if (Number.isNaN(num)) return String(value);

        const options = field.options || {};
        const precision = options.precision ?? 0;
        const prefix = options.prefix || "";
        const suffix = options.suffix || "";
        const currencySymbol = options.currencySymbol || "";

        let formatted = num.toFixed(precision);
        if (fieldType === FieldType.PERCENT) {
          formatted = `${formatted}%`;
        } else if (fieldType === FieldType.CURRENCY && currencySymbol) {
          formatted = `${currencySymbol}${formatted}`;
        }

        return `${prefix}${formatted}${suffix}`;
      };
    }
    // 日期类型字段：date, date_time - 添加日期格式化
    else if (fieldType === FieldType.DATE || fieldType === FieldType.DATE_TIME) {
      const isDateTime = fieldType === FieldType.DATE_TIME;
      column.fieldFormat = (record: any) => {
        const cellValue = record?.[field.id];
        if (cellValue === null || cellValue === undefined || cellValue === "")
          return "";

        if (cellValue instanceof Date) {
          return isDateTime
            ? formatDateTime(cellValue.getTime())
            : formatDate(cellValue.getTime());
        }
        if (typeof cellValue === "number") {
          return isDateTime ? formatDateTime(cellValue) : formatDate(cellValue);
        }
        if (typeof cellValue === "string") {
          return isDateTime ? formatDateTime(cellValue) : formatDate(cellValue);
        }
        return String(cellValue);
      };
    }
    // 复选框字段：显示是/否
    else if (fieldType === FieldType.CHECKBOX) {
      column.fieldFormat = (record: any) => {
        const value = record?.[field.id];
        if (value === true) return "是";
        if (value === false) return "否";
        if (value === null || value === undefined || value === "") return "";
        return String(value);
      };
    }
    // 关联字段：显示"关联 N 条"
    else if (fieldType === FieldType.LINK) {
      column.fieldFormat = (record: any) => {
        const rawIds = record?.[field.id];
        if (Array.isArray(rawIds) && rawIds.length > 0) {
          return `关联 ${rawIds.length} 条`;
        }
        return "";
      };
    }

    columns.push(column);
  }

  return columns;
}

// ==================== 目标表字段定义获取（带缓存） ====================

/**
 * 获取目标表字段定义，优先从缓存获取
 * 缓存未命中时调用 fieldService.getFieldsByTable 获取并缓存
 */
export async function getTargetTableFields(tableId: string): Promise<any[]> {
  // 尝试从缓存获取
  const cached = fieldDefinitionCache.get(tableId);
  if (cached) {
    console.log(
      `[masterDetailService] 从缓存获取表 ${tableId} 的字段定义`
    );
    return cached;
  }

  // 缓存未命中，调用 fieldService 获取并缓存
  const fields = await fieldService.getFieldsByTable(tableId);
  fieldDefinitionCache.set(tableId, fields);
  console.log(
    `[masterDetailService] 获取并缓存表 ${tableId} 的字段定义 (${fields.length} 个字段)`
  );

  return fields;
}

// ==================== 服务对象导出 ====================

export const masterDetailService = {
  getLinkedRecordsDetail,
  createAndLinkRecord,
  buildSubTableColumns,
  getTargetTableFields,
  fieldDefinitionCache,
};

export default masterDetailService;
