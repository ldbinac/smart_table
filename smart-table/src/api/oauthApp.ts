/**
 * 第三方应用接入（OAuth2）管理后台 API
 *
 * 对应后端蓝图：
 * - /oauth/apps  -> 应用 CRUD / 密钥重置 / 令牌 / 审计
 * - /oauth/bases -> Base 范围候选列表
 * - /oauth/token -> 令牌签发端点（开发者文档 / 调试用）
 */
import { apiClient } from "@/api/client";

/** 应用摘要 / 详情 */
export interface OAuthApp {
  id: string;
  app_name: string;
  client_id: string;
  client_secret?: string;
  owner_id: string;
  callback_url: string | null;
  allowed_bases: string[];
  allowed_base_names: string[];
  scopes: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** 已签发令牌元数据 */
export interface ApiAppToken {
  id: string;
  jti: string;
  app_id: string;
  scope: string[];
  expires_at: string;
  revoked: boolean;
  created_at: string;
}

/** 审计日志 */
export interface ApiAppAuditLog {
  id: string;
  app_id: string | null;
  action: string;
  detail: string | null;
  ip: string | null;
  created_at: string;
}

/** Base 范围候选 */
export interface BaseOption {
  id: string;
  name: string | null;
  owner_id: string | null;
}

/** 令牌端点响应（OAuth2 标准） */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
  request_id?: string | null;
}

const OAUTH_BASE = "/oauth";

/** 列出全部 Base（供授权范围多选） */
export async function listOAuthBases(): Promise<BaseOption[]> {
  return apiClient.get<BaseOption[]>(`${OAUTH_BASE}/bases`);
}

/** 列出第三方应用 */
export async function listOAuthApps(): Promise<OAuthApp[]> {
  return apiClient.get<OAuthApp[]>(`${OAUTH_BASE}/apps`);
}

/** 获取单个应用详情 */
export async function getOAuthApp(id: string): Promise<OAuthApp> {
  return apiClient.get<OAuthApp>(`${OAUTH_BASE}/apps/${id}`);
}

/** 创建应用（返回含明文 client_secret 的详情，仅此一次） */
export async function createOAuthApp(payload: {
  app_name: string;
  allowed_bases: string[];
  scopes: string[];
  callback_url?: string;
  is_active?: boolean;
}): Promise<OAuthApp> {
  return apiClient.post<OAuthApp>(`${OAUTH_BASE}/apps`, payload);
}

/** 更新应用配置 */
export async function updateOAuthApp(
  id: string,
  payload: {
    app_name?: string;
    callback_url?: string;
    allowed_bases?: string[];
    scopes?: string[];
    is_active?: boolean;
  },
): Promise<OAuthApp> {
  return apiClient.put<OAuthApp>(`${OAUTH_BASE}/apps/${id}`, payload);
}

/** 删除应用 */
export async function deleteOAuthApp(id: string): Promise<void> {
  await apiClient.delete(`${OAUTH_BASE}/apps/${id}`);
}

/** 重置 client_secret（返回含明文新密钥的详情） */
export async function resetOAuthSecret(id: string): Promise<OAuthApp> {
  return apiClient.post<OAuthApp>(`${OAUTH_BASE}/apps/${id}/reset-secret`);
}

/** 查看已签发令牌（含已撤销） */
export async function listOAuthTokens(id: string): Promise<ApiAppToken[]> {
  return apiClient.get<ApiAppToken[]>(`${OAUTH_BASE}/apps/${id}/tokens`);
}

/** 撤销令牌：指定 jti 撤销单个，否则撤销全部 */
export async function revokeOAuthTokens(
  id: string,
  jti?: string,
): Promise<{ revoked: number } | null> {
  return apiClient.post<{ revoked: number } | null>(
    `${OAUTH_BASE}/apps/${id}/tokens/revoke`,
    { jti },
  );
}

/** 查看审计日志 */
export async function listOAuthAudit(id: string): Promise<ApiAppAuditLog[]> {
  return apiClient.get<ApiAppAuditLog[]>(`${OAUTH_BASE}/apps/${id}/audit`);
}
