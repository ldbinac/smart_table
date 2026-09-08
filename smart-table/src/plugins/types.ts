/**
 * 插件体系类型定义
 *
 * 与后端 app/services/plugin_manifest_schema.py 的 MANIFEST_SCHEMA 保持契约一致。
 */

/** 插件形态 */
export type PluginType = "ui" | "script";

/** 插件全局状态 */
export type PluginStatus = "installed" | "enabled" | "disabled" | "error";

/** 配置作用域 */
export type PluginConfigScope = "global" | "base" | "kv";

/** 权限等级 */
export type PermissionLevel = "read" | "write";

/**
 * 对象式分级权限声明
 * 采用对象式而非扁平字符串数组，为未来细粒度权限（限定表/字段）演进留余地
 */
export interface PluginPermissions {
  records?: PermissionLevel;
  tables?: PermissionLevel;
  storage?: boolean;
  network?: string[];
}

/** UI 扩展点类型（首期） */
export type ExtensionPointType =
  | "toolbar-button"
  | "side-panel"
  | "base-menu"
  | "record-detail-block";

/** UI 扩展点声明 */
export interface ExtensionPoint {
  type: ExtensionPointType;
  title: string;
  icon?: string;
  /** 是否要求表格中已勾选记录（未勾选时宿主禁用入口并提示） */
  requiresSelection?: boolean;
  /** 允许处理的最大勾选条数（超出时宿主禁用入口并提示） */
  maxSelection?: number;
}

/** 勾选范围：page=当前页行、view=当前视图筛选结果 */
export type SelectionScope = "page" | "view";

/** 表格上报的勾选摘要（宿主内部使用，不含记录内容） */
export interface SelectionSummary {
  recordIds: string[];
  total: number;
  /** 是否命中"全选"（如表头复选框全选） */
  selectAll: boolean;
  scope: SelectionScope;
}

/** 传给插件的勾选快照（打开插件时生成，仅含记录 ID） */
export interface SelectionSnapshot {
  recordIds: string[];
  total: number;
  /** 是否因超过上限被截断（此时 total > recordIds.length） */
  truncated: boolean;
  selectAll: boolean;
  scope: SelectionScope;
  /** 快照生成时间戳（ms） */
  at: number;
}

/** 脚本插件配置 */
export interface ScriptConfig {
  timeout?: number;
}

/** 插件清单 */
export interface PluginManifest {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  author?: { name?: string; url?: string; email?: string };
  version: string;
  type: PluginType;
  apiVersion: string;
  engines: { smarttable: string };
  entry: string;
  permissions: PluginPermissions;
  extensionPoints?: ExtensionPoint[];
  configSchema?: Record<string, unknown>;
  script?: ScriptConfig;
}

/** 插件（后端返回结构） */
export interface PluginEntity {
  id: string;
  name: string;
  description?: string | null;
  icon?: string | null;
  type: PluginType;
  status: PluginStatus;
  current_version: string;
  manifest: PluginManifest;
  created_at?: string | null;
  updated_at?: string | null;
  /** 列表接口带 base_id 查询时返回 */
  baseInstalled?: boolean;
  /** Base 级安装记录的原始启用位（不含全局状态） */
  baseInstallEnabled?: boolean;
  /** Base 级生效状态（安装启用 且 全局启用） */
  baseEnabled?: boolean;
}

/** 插件版本 */
export interface PluginVersion {
  id: string;
  plugin_id: string;
  version: string;
  checksum: string;
  installed_at?: string | null;
}

/** Base 级安装关系 */
export interface PluginInstallation {
  id: string;
  plugin_id: string;
  base_id: string;
  enabled: boolean;
  installed_by?: string | null;
  installed_at?: string | null;
}

/** 脚本运行日志 */
export interface PluginRunLog {
  id: string;
  plugin_id: string;
  base_id: string;
  status: "running" | "success" | "failed" | "timeout";
  duration_ms?: number | null;
  triggered_by?: string | null;
  output?: string | null;
  result?: unknown;
  error_summary?: string | null;
  traceback_text?: string | null;
  created_at?: string | null;
}

// ==================== RPC 协议 ====================

/** RPC 错误码（与后端/loader SDK 一致） */
export type RpcErrorCode =
  | "PERMISSION_DENIED"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "RATE_LIMITED"
  | "MESSAGE_TOO_LARGE"
  | "INTERNAL_ERROR"
  | "API_VERSION_MISMATCH";

export interface RpcError {
  code: RpcErrorCode | string;
  message: string;
}

/** iframe → 宿主：握手 */
export interface RpcInitMessage {
  type: "init";
  token: string;
}

/** iframe → 宿主：RPC 请求 */
export interface RpcRequestMessage {
  type: "rpc.request";
  id: string;
  method: string;
  params?: Record<string, unknown>;
}

/** 宿主 → iframe：握手确认 */
export interface RpcInitAckMessage {
  type: "initAck";
  sdk: { apiVersion: string };
  permissions: PluginPermissions;
}

/** 宿主 → iframe：RPC 响应 */
export interface RpcResponseMessage {
  type: "rpc.response";
  id: string;
  result?: unknown;
  error?: RpcError;
}

export type RpcMessage =
  | RpcInitMessage
  | RpcRequestMessage
  | RpcInitAckMessage
  | RpcResponseMessage;

/** 宿主 API 方法处理器 */
export interface ApiHandlerContext {
  pluginId: string;
  permissions: PluginPermissions;
  baseId: string;
  tableId: string;
  config: Record<string, unknown>;
  /** 打开插件瞬间的表格勾选快照（未接入表格时为 null） */
  selection: SelectionSnapshot | null;
}

export type ApiHandler = (
  params: Record<string, unknown>,
  ctx: ApiHandlerContext,
) => Promise<unknown> | unknown;
