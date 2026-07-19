/**
 * 查找字段 API 服务
 */
import { apiClient } from "@/api/client";
import type { LookupFieldConfig } from "@/types/fields";

/** 创建查找字段的请求体 */
export interface CreateLookupFieldPayload {
  name: string;
  description?: string;
  config: LookupFieldConfig;
}

/** 更新查找字段的请求体 */
export interface UpdateLookupFieldPayload {
  name?: string;
  description?: string;
  config: LookupFieldConfig;
}

/** 预览查找结果的请求体 */
export interface PreviewLookupValuePayload {
  record_id: string;
  config?: LookupFieldConfig;
}

/** 字段对象（与后端 to_dict 一致） */
export interface LookupFieldResponse {
  id: string;
  table_id: string;
  name: string;
  type: string;
  description?: string;
  config?: LookupFieldConfig;
  [key: string]: unknown;
}

/** 预览结果响应 */
export interface PreviewLookupValueResponse {
  value: unknown;
}

/**
 * 创建查找字段
 */
export const createLookupField = async (
  tableId: string,
  payload: CreateLookupFieldPayload
): Promise<LookupFieldResponse> => {
  return apiClient.post<LookupFieldResponse>(
    `/tables/${tableId}/fields/lookup`,
    payload
  );
};

/**
 * 更新查找字段配置
 */
export const updateLookupField = async (
  fieldId: string,
  payload: UpdateLookupFieldPayload
): Promise<LookupFieldResponse> => {
  return apiClient.put<LookupFieldResponse>(
    `/fields/${fieldId}/lookup`,
    payload
  );
};

/**
 * 预览查找结果
 */
export const previewLookupValue = async (
  fieldId: string,
  payload: PreviewLookupValuePayload
): Promise<PreviewLookupValueResponse> => {
  return apiClient.post<PreviewLookupValueResponse>(
    `/fields/${fieldId}/lookup/preview`,
    payload
  );
};

export const lookupApiService = {
  createLookupField,
  updateLookupField,
  previewLookupValue,
};

export default lookupApiService;
