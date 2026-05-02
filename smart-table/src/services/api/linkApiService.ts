/**
 * 关联字段 API 服务
 */
import { apiClient } from "@/api/client";
import type { LinkRelation, LinkValue } from "@/types/link";

// 简单的内存缓存
interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

class LinkDataCache {
  private cache = new Map<string, CacheEntry<unknown>>();
  private readonly TTL = 5 * 60 * 1000; // 5分钟缓存

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    // 检查是否过期
    if (Date.now() - entry.timestamp > this.TTL) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  set<T>(key: string, data: T): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  invalidate(key: string): void {
    this.cache.delete(key);
  }

  invalidateByPattern(pattern: string): void {
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }

  clear(): void {
    this.cache.clear();
  }
}

// 全局缓存实例
const linkCache = new LinkDataCache();

export type RelationshipType = "one_to_one" | "one_to_many" | "many_to_one" | "many_to_many";

export const RELATIONSHIP_TYPE_LABELS: Record<RelationshipType, string> = {
  one_to_one: "一对一",
  one_to_many: "一对多",
  many_to_one: "多对一",
  many_to_many: "多对多",
};

export const getInverseRelationshipType = (type: RelationshipType): RelationshipType => {
  const mapping: Record<RelationshipType, RelationshipType> = {
    one_to_one: "one_to_one",
    one_to_many: "many_to_one",
    many_to_one: "one_to_many",
    many_to_many: "many_to_many",
  };
  return mapping[type];
};

export interface CreateLinkFieldData {
  table_id: string;
  name: string;
  target_table_id: string;
  relationship_type: "one_to_one" | "one_to_many" | "many_to_one" | "many_to_many";
  display_field_id?: string;
  bidirectional?: boolean;
  description?: string;
}

export interface UpdateLinkFieldData {
  relationship_type?: "one_to_one" | "one_to_many" | "many_to_one" | "many_to_many";
  display_field_id?: string;
  bidirectional?: boolean;
  name?: string;
  description?: string;
}

export interface UpdateLinkValueData {
  target_record_ids: string[];
}

export interface SearchLinkableRecordsParams {
  keyword?: string;
  exclude_ids?: string[];
  page?: number;
  per_page?: number;
}

/**
 * 创建关联字段
 */
export const createLinkField = async (
  data: CreateLinkFieldData
): Promise<{ field: Record<string, unknown>; link_relation: LinkRelation }> => {
  return apiClient.post<{
    field: Record<string, unknown>;
    link_relation: LinkRelation;
  }>("/fields/link", data);
};

/**
 * 更新关联字段配置
 */
export const updateLinkField = async (
  fieldId: string,
  data: UpdateLinkFieldData
): Promise<Record<string, unknown>> => {
  return apiClient.put<Record<string, unknown>>(
    `/fields/${fieldId}/link`,
    data
  );
};

/**
 * 删除关联字段
 */
export const deleteLinkField = async (fieldId: string): Promise<void> => {
  return apiClient.delete<void>(`/fields/${fieldId}/link`);
};

/**
 * 获取表格的所有关联关系
 */
export const getTableLinkRelations = async (
  tableId: string
): Promise<LinkRelation[]> => {
  return apiClient.get<LinkRelation[]>(`/tables/${tableId}/links`);
};

/**
 * 获取记录的关联数据（带缓存）
 */
export const getRecordLinks = async (
  recordId: string,
  useCache: boolean = true
): Promise<{
  outbound: Array<{
    field_id: string;
    field_name: string;
    target_table_id: string;
    target_table_name: string;
    linked_records: Array<{
      record_id: string;
      display_value: string;
    }>;
  }>;
  inbound: Array<{
    field_id: string;
    field_name: string;
    source_table_id: string;
    source_table_name: string;
    linked_records: Array<{
      record_id: string;
      display_value: string;
    }>;
  }>;
}> => {
  const cacheKey = `record_links:${recordId}`;

  // 尝试从缓存获取
  if (useCache) {
    const cached = linkCache.get<ReturnType<typeof getRecordLinks>>(cacheKey);
    if (cached) {
      console.log(`[linkApiService] 从缓存获取记录 ${recordId} 的关联数据`);
      return cached;
    }
  }

  // 从 API 获取
  const result = await apiClient.get<{
    outbound: Array<{
      field_id: string;
      field_name: string;
      target_table_id: string;
      target_table_name: string;
      linked_records: Array<{
        record_id: string;
        display_value: string;
      }>;
    }>;
    inbound: Array<{
      field_id: string;
      field_name: string;
      source_table_id: string;
      source_table_name: string;
      linked_records: Array<{
        record_id: string;
        display_value: string;
      }>;
    }>;
  }>(`/records/${recordId}/links`);

  // 存入缓存
  if (useCache) {
    linkCache.set(cacheKey, result);
  }

  return result;
};

/**
 * 更新记录的关联值
 */
export const updateRecordLink = async (
  recordId: string,
  fieldId: string,
  data: UpdateLinkValueData
): Promise<{ updated_count: number }> => {
  const result = await apiClient.put<{ updated_count: number }>(
    `/records/${recordId}/links/${fieldId}`,
    data
  );

  // 清除相关缓存
  linkCache.invalidate(`record_links:${recordId}`);

  return result;
};

/**
 * 搜索可关联的记录
 */
export const searchLinkableRecords = async (
  tableId: string,
  params: SearchLinkableRecordsParams
): Promise<{
  items: Array<{
    id: string;
    values: Record<string, unknown>;
    created_at: string;
  }>;
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}> => {
  const queryParams: Record<string, unknown> = {
    page: params.page || 1,
    per_page: params.per_page || 20,
  };

  if (params.keyword) {
    queryParams.keyword = params.keyword;
  }

  if (params.exclude_ids && params.exclude_ids.length > 0) {
    queryParams.exclude_ids = params.exclude_ids.join(",");
  }

  // 后端返回格式为 {success, message, data: items, meta: {pagination: {...}}}
  // apiClient.get 会返回整个响应对象（因为包含 meta 字段）
  const response = await apiClient.get<{
    success: boolean;
    message: string;
    data: Array<{
      id: string;
      values: Record<string, unknown>;
      created_at: string;
    }>;
    meta: {
      pagination: {
        page: number;
        per_page: number;
        total: number;
        total_pages: number;
      };
    };
  }>(`/tables/${tableId}/records/search`, queryParams);

  console.log("[searchLinkableRecords] API 响应:", response);

  // 转换为前端期望的格式
  // response 是 { success, message, data, meta } 结构
  return {
    items: response.data || [],
    total: response.meta?.pagination?.total || 0,
    page: response.meta?.pagination?.page || 1,
    per_page: response.meta?.pagination?.per_page || 20,
    total_pages: response.meta?.pagination?.total_pages || 0,
  };
};

export const linkApiService = {
  createLinkField,
  updateLinkField,
  deleteLinkField,
  getTableLinkRelations,
  getRecordLinks,
  updateRecordLink,
  searchLinkableRecords,
  // 缓存操作
  invalidateCache: (key: string) => linkCache.invalidate(key),
  invalidateCacheByPattern: (pattern: string) => linkCache.invalidateByPattern(pattern),
  clearCache: () => linkCache.clear(),
};

export default linkApiService;
