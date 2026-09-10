/**
 * 插件宿主 API 实现（api-surface）
 *
 * 所有数据操作由宿主以当前用户 JWT 身份转发（复用现有 services/client.ts），
 * 插件自身永不持有凭证 —— 权限为「插件声明权限点 + 用户 RBAC」双重校验。
 *
 * 每个方法声明所需权限点，未声明权限时直接拒绝（deny by default）。
 */
import { ElMessage } from "element-plus";
import {
  getRecords,
  getRecord,
  createRecord,
  updateRecord,
  deleteRecord,
} from "@/services/api/recordApiService";
import {
  getTables,
  getTable,
} from "@/services/api/tableApiService";
import { getFields } from "@/services/api/fieldApiService";
import type { ApiHandler, PluginPermissions } from "./types";

/** 方法 → 所需权限点映射 */
interface MethodMeta {
  permission: "records" | "tables";
  level: "read" | "write";
}

const METHOD_PERMISSIONS: Record<string, MethodMeta> = {
  "table.getRecords": { permission: "records", level: "read" },
  "table.searchRecords": { permission: "records", level: "read" },
  "table.getRecord": { permission: "records", level: "read" },
  "record.create": { permission: "records", level: "write" },
  "record.update": { permission: "records", level: "write" },
  "record.delete": { permission: "records", level: "write" },
  "table.listTables": { permission: "tables", level: "read" },
  "table.getSchema": { permission: "tables", level: "read" },
};

/** 权限校验：插件声明的权限是否满足方法要求 */
function hasPermission(
  permissions: PluginPermissions,
  meta: MethodMeta,
): boolean {
  const declared = permissions[meta.permission];
  if (declared === undefined || declared === null) return false;
  if (typeof declared === "string") {
    if (meta.level === "read") return declared === "read" || declared === "write";
    return declared === "write";
  }
  return false;
}

/** 构造受限的 API 处理器表（仅包含该插件被授权的方法） */
export function buildApiSurface(
  permissions: PluginPermissions,
): Map<string, ApiHandler> {
  const handlers = new Map<string, ApiHandler>();

  // ---------- 无需权限的 UI 能力（始终可用） ----------
  handlers.set("ui.notify", (params) => {
    const { message, type } = params as {
      message?: string;
      type?: "success" | "warning" | "error" | "info";
    };
    ElMessage({ message: String(message ?? ""), type: type || "info" });
    return { ok: true };
  });

  handlers.set("ui.getContext", (_params, ctx) => ({
    pluginId: ctx.pluginId,
    baseId: ctx.baseId,
    tableId: ctx.tableId,
    selection: ctx.selection,
  }));

  // 勾选数据读取（与 ui.getContext 同源，便于插件单独获取）
  handlers.set("selection.get", (_params, ctx) => ctx.selection);

  // 配置读取：隐含授予（与后端一致）
  handlers.set("config.get", (_params, ctx) => ctx.config);

  // ---------- 需权限声明的数据能力 ----------
  const require = (
    method: string,
    fn: ApiHandler,
  ): void => {
    const meta = METHOD_PERMISSIONS[method];
    if (!meta) return;
    if (!hasPermission(permissions, meta)) return; // 未授权则方法不可见
    handlers.set(method, async (params, ctx) => {
      if (!hasPermission(ctx.permissions, meta)) {
        throw new Error(
          `PERMISSION_DENIED: plugin lacks ${meta.permission}:${meta.level}`,
        );
      }
      return fn(params, ctx);
    });
  };

  require("table.getRecords", async (params) => {
    const { tableId, page, per_page, view_id, search } = params as {
      tableId?: string;
      page?: number;
      per_page?: number;
      view_id?: string;
      search?: string;
    };
    const target = tableId || "";
    if (!target) throw new Error("VALIDATION_ERROR: tableId is required");
    return getRecords(target, {
      page: Number(page) || 1,
      per_page: Math.min(500, Number(per_page) || 100),
      view_id,
      search,
    } as never);
  });

  require("table.searchRecords", async (params, ctx) => {
    const { tableId, search, page, per_page } = params as {
      tableId?: string;
      search?: string;
      page?: number;
      per_page?: number;
    };
    const target = tableId || ctx.tableId;
    if (!target) throw new Error("VALIDATION_ERROR: tableId is required");
    return getRecords(target, {
      search: String(search || ""),
      page: Number(page) || 1,
      per_page: Math.min(500, Number(per_page) || 100),
    } as never);
  });

  require("table.getRecord", async (params) => {
    const { recordId } = params as { recordId?: string };
    if (!recordId) throw new Error("VALIDATION_ERROR: recordId is required");
    return getRecord(recordId);
  });

  require("record.create", async (params, ctx) => {
    const { tableId, values } = params as {
      tableId?: string;
      values?: Record<string, unknown>;
    };
    const target = tableId || ctx.tableId;
    if (!target) throw new Error("VALIDATION_ERROR: tableId is required");
    return createRecord(target, values || {});
  });

  require("record.update", async (params) => {
    const { recordId, values } = params as {
      recordId?: string;
      values?: Record<string, unknown>;
    };
    if (!recordId) throw new Error("VALIDATION_ERROR: recordId is required");
    return updateRecord(recordId, values || {});
  });

  require("record.delete", async (params) => {
    const { recordId } = params as { recordId?: string };
    if (!recordId) throw new Error("VALIDATION_ERROR: recordId is required");
    await deleteRecord(recordId);
    return { deleted: true };
  });

  require("table.listTables", async (_params, ctx) => {
    return getTables(ctx.baseId);
  });

  require("table.getSchema", async (params, ctx) => {
    const { tableId } = params as { tableId?: string };
    const target = tableId || ctx.tableId;
    if (!target) throw new Error("VALIDATION_ERROR: tableId is required");
    const [table, fields] = await Promise.all([
      getTable(target),
      getFields(target),
    ]);
    return { table, fields };
  });

  // ---------- storage 权限（插件自有 KV，首期本地实现） ----------
  if (permissions.storage) {
    const storagePrefix = `smarttable.plugin.`;
    handlers.set("storage.get", (params, ctx) => {
      const key = String((params as { key?: string }).key || "");
      const raw = localStorage.getItem(`${storagePrefix}${ctx.pluginId}:${key}`);
      return raw ? (JSON.parse(raw) as unknown) : null;
    });
    handlers.set("storage.set", (params, ctx) => {
      const { key, value } = params as { key?: string; value?: unknown };
      localStorage.setItem(
        `${storagePrefix}${ctx.pluginId}:${String(key || "")}`,
        JSON.stringify(value ?? null),
      );
      return { ok: true };
    });
    handlers.set("storage.remove", (params, ctx) => {
      const key = String((params as { key?: string }).key || "");
      localStorage.removeItem(`${storagePrefix}${ctx.pluginId}:${key}`);
      return { ok: true };
    });
  }

  return handlers;
}

export const apiSurfaceInternals = { METHOD_PERMISSIONS, hasPermission };
