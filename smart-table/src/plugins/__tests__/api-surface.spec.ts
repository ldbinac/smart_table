/**
 * 宿主 API 面单测：buildApiSurface 按权限点声明过滤方法（deny by default）
 */
import { describe, it, expect, vi } from "vitest";

// 避免引入 element-plus UI 与真实网络服务
vi.mock("element-plus", () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));
vi.mock("@/services/api/recordApiService", () => ({
  getRecords: vi.fn(),
  getRecord: vi.fn(),
  createRecord: vi.fn(),
  updateRecord: vi.fn(),
  deleteRecord: vi.fn(),
}));
vi.mock("@/services/api/tableApiService", () => ({
  getTables: vi.fn(),
  getTable: vi.fn(),
}));
vi.mock("@/services/api/fieldApiService", () => ({
  getFields: vi.fn(),
}));

import { buildApiSurface } from "../api-surface";

describe("buildApiSurface 权限过滤", () => {
  it("records:write 时暴露记录读写方法，但不暴露 storage", () => {
    const surface = buildApiSurface({ records: "write" });
    expect(surface.has("table.getRecords")).toBe(true);
    expect(surface.has("record.create")).toBe(true);
    expect(surface.has("record.update")).toBe(true);
    expect(surface.has("record.delete")).toBe(true);
    expect(surface.has("storage.get")).toBe(false);
  });

  it("records:read 时仅暴露读取类方法，写方法不可见", () => {
    const surface = buildApiSurface({ records: "read" });
    expect(surface.has("table.getRecords")).toBe(true);
    expect(surface.has("record.create")).toBe(false);
    expect(surface.has("record.update")).toBe(false);
    expect(surface.has("record.delete")).toBe(false);
  });

  it("storage:true 时暴露插件自有 KV 方法", () => {
    const surface = buildApiSurface({ storage: true });
    expect(surface.has("storage.get")).toBe(true);
    expect(surface.has("storage.set")).toBe(true);
    expect(surface.has("storage.remove")).toBe(true);
  });

  it("无需声明权限的 UI 能力始终可用", () => {
    const surface = buildApiSurface({});
    expect(surface.has("ui.notify")).toBe(true);
    expect(surface.has("ui.getContext")).toBe(true);
    expect(surface.has("config.get")).toBe(true);
  });

  it("tables:read 暴露表结构方法", () => {
    const surface = buildApiSurface({ tables: "read" });
    expect(surface.has("table.listTables")).toBe(true);
    expect(surface.has("table.getSchema")).toBe(true);
  });
});
