/**
 * 记录变更历史 API 服务
 * 提供记录变更历史的查询功能
 */
import { apiClient } from "@/api/client";

/**
 * 变更详情
 */
export interface HistoryChange {
  field_id: string;
  old_value: any;
  new_value: any;
}

/**
 * 变更人信息
 */
export interface HistoryChanger {
  id: string;
  name: string;
  avatar?: string;
}

/**
 * 记录变更历史
 */
export interface RecordHistory {
  id: string;
  record_id: string;
  table_id: string;
  action: "CREATE" | "UPDATE" | "DELETE";
  changed_by: HistoryChanger;
  changed_at: string;
  changes: HistoryChange[];
  snapshot: Record<string, any>;
}

/**
 * 分页响应
 */
export interface PaginatedHistoryResponse {
  items: RecordHistory[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/**
 * 获取记录变更历史
 * @param recordId 记录 ID
 * @param page 页码（从1开始）
 * @param size 每页数量
 * @returns 分页的变更历史列表
 */
export const getRecordHistory = async (
  recordId: string,
  page: number = 1,
  size: number = 20
): Promise<PaginatedHistoryResponse> => {
  const response = await apiClient.get<
    RecordHistory[] | { data: RecordHistory[]; meta?: { pagination?: { total?: number; page?: number; per_page?: number; total_pages?: number } } }
  >(`/records/${recordId}/history`, { page, size });

  // 处理后端返回的分页格式 { data: [...], meta: { pagination: {...} } }
  if (Array.isArray(response)) {
    return {
      items: response,
      total: response.length,
      page: page,
      size: size,
      pages: 1
    };
  }

  // 处理标准分页响应
  const data = response as { data: RecordHistory[]; meta?: { pagination?: { total?: number; page?: number; per_page?: number; total_pages?: number } } };
  const pagination = data.meta?.pagination;

  return {
    items: data.data || [],
    total: pagination?.total || 0,
    page: pagination?.page || page,
    size: pagination?.per_page || size,
    pages: pagination?.total_pages || 1
  };
};

/**
 * 数据表变更历史查询参数
 */
export interface TableHistoryParams {
  page?: number;
  size?: number;
  startTime?: string;
  endTime?: string;
  changedBy?: string;
  action?: "CREATE" | "UPDATE" | "DELETE" | "";
}

/**
 * 获取数据表变更历史（审计日志）
 * 按数据表查询 record_history 表，支持时间段、变更人、变更动作过滤
 * @param tableId 数据表 ID
 * @param params 分页与过滤参数
 * @returns 分页的变更历史列表
 */
export const getTableHistory = async (
  tableId: string,
  params: TableHistoryParams = {}
): Promise<PaginatedHistoryResponse> => {
  const { page = 1, size = 10, startTime, endTime, changedBy, action } = params;

  const query: Record<string, any> = { page, size };
  if (startTime) query.start_time = startTime;
  if (endTime) query.end_time = endTime;
  if (changedBy) query.changed_by = changedBy;
  if (action) query.action = action;

  const response = await apiClient.get<
    RecordHistory[] | { data: RecordHistory[]; meta?: { pagination?: { total?: number; page?: number; per_page?: number; total_pages?: number } } }
  >(`/tables/${tableId}/history`, query);

  // 处理后端返回的分页格式 { data: [...], meta: { pagination: {...} } }
  if (Array.isArray(response)) {
    return {
      items: response,
      total: response.length,
      page: page,
      size: size,
      pages: 1
    };
  }

  const data = response as { data: RecordHistory[]; meta?: { pagination?: { total?: number; page?: number; per_page?: number; total_pages?: number } } };
  const pagination = data.meta?.pagination;

  return {
    items: data.data || [],
    total: pagination?.total || 0,
    page: pagination?.page || page,
    size: pagination?.per_page || size,
    pages: pagination?.total_pages || 1
  };
};

export const recordHistoryApiService = {
  getRecordHistory,
  getTableHistory,
};

export default recordHistoryApiService;
