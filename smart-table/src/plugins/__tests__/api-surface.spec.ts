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
vi.mock("@/api/plugins", () => ({
  callPluginEndpoint: vi.fn(),
  proxyPluginRequest: vi.fn(),
}));

import { buildApiSurface } from "../api-surface";
import { callPluginEndpoint, proxyPluginRequest } from "@/api/plugins";

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

describe("插件自定义后端接口（backend.call）", () => {
  it("未声明也无妨，backend.call 始终可用", () => {
    const surface = buildApiSurface({});
    expect(surface.has("backend.call")).toBe(true);
  });

  it("endpoint 名称非法时拒绝", async () => {
    const surface = buildApiSurface({});
    const handler = surface.get("backend.call")!;
    await expect(
      handler({ name: "Bad Name", payload: {} }, { pluginId: "p1", baseId: "b1" } as any),
    ).rejects.toThrow(/VALIDATION_ERROR/);
  });

  it("合法调用转发到 callPluginEndpoint", async () => {
    (callPluginEndpoint as any).mockResolvedValue({ ok: true });
    const surface = buildApiSurface({});
    const handler = surface.get("backend.call")!;
    const res = await handler(
      { name: "translate", payload: { a: 1 } },
      { pluginId: "p1", baseId: "b1" } as any,
    );
    expect(callPluginEndpoint).toHaveBeenCalledWith("p1", "translate", { a: 1 }, "b1");
    expect(res).toEqual({ ok: true });
  });
});

describe("第三方网络代理（network.fetch）", () => {
  it("未声明 network 权限时方法不可见（deny by default）", () => {
    const surface = buildApiSurface({});
    expect(surface.has("network.fetch")).toBe(false);
  });

  it("声明 network 权限后可见，并转发到 proxyPluginRequest", async () => {
    (proxyPluginRequest as any).mockResolvedValue({ status: 200, body: "{}" });
    const surface = buildApiSurface({ network: ["api.example.com"] });
    expect(surface.has("network.fetch")).toBe(true);
    const handler = surface.get("network.fetch")!;
    await handler(
      { url: "https://api.example.com/x", method: "GET" },
      { pluginId: "p1", baseId: "b1" } as any,
    );
    expect(proxyPluginRequest).toHaveBeenCalledWith(
      "p1",
      "b1",
      "https://api.example.com/x",
      "GET",
      undefined,
      undefined,
    );
  });

  it("缺少 url 时拒绝", async () => {
    const surface = buildApiSurface({ network: ["api.example.com"] });
    const handler = surface.get("network.fetch")!;
    await expect(
      handler({}, { pluginId: "p1", baseId: "b1" } as any),
    ).rejects.toThrow(/VALIDATION_ERROR/);
  });
});
