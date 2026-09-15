/**
 * 插件注册表单元测试：有效启用过滤、扩展点归类、错误隔离
 */
import { describe, it, expect } from "vitest";
import pluginRegistry, {
  isEffective,
  reportPluginError,
  clearPluginErrors,
  setPlugins,
} from "../registry";
import type { PluginEntity } from "../types";

function makePlugin(over: Partial<PluginEntity> = {}): PluginEntity {
  return {
    id: "com.example.demo",
    name: "Demo",
    type: "ui",
    status: "enabled",
    current_version: "1.0.0",
    manifest: {
      id: "com.example.demo",
      name: "Demo",
      version: "1.0.0",
      type: "ui",
      apiVersion: "1",
      engines: { smarttable: ">=1.7.0" },
      entry: "main.js",
      permissions: { records: "read" },
      extensionPoints: [{ type: "toolbar-button", title: "Demo" }],
    } as any,
    ...over,
  } as PluginEntity;
}

describe("isEffective（两层权限语义）", () => {
  it("全局 enabled 且 Base 级 enabled → 有效", () => {
    expect(
      isEffective(makePlugin({ status: "enabled", baseEnabled: true })),
    ).toBe(true);
  });

  it("全局 disabled 时，即使 Base 启用也无效", () => {
    expect(
      isEffective(makePlugin({ status: "disabled", baseEnabled: true })),
    ).toBe(false);
  });

  it("全局 enabled 但 Base 未安装/未启用 → 无效", () => {
    expect(
      isEffective(makePlugin({ status: "enabled", baseEnabled: false })),
    ).toBe(false);
  });

  it("状态为 error 时无效", () => {
    expect(
      isEffective(makePlugin({ status: "error", baseEnabled: true })),
    ).toBe(false);
  });
});

describe("扩展点归类", () => {
  it("toolbarButtons 仅收集有效启用的 ui 插件 toolbar-button", () => {
    setPlugins([
      makePlugin({
        id: "p1",
        status: "enabled",
        baseEnabled: true,
        manifest: {
          id: "p1",
          name: "P1",
          version: "1.0.0",
          type: "ui",
          apiVersion: "1",
          engines: { smarttable: ">=1.7.0" },
          entry: "main.js",
          permissions: {},
          extensionPoints: [{ type: "toolbar-button", title: "Btn1" }],
        } as any,
      }),
      makePlugin({
        id: "p2",
        status: "disabled", // 无效
        baseEnabled: true,
        manifest: {
          id: "p2",
          name: "P2",
          version: "1.0.0",
          type: "ui",
          apiVersion: "1",
          engines: { smarttable: ">=1.7.0" },
          entry: "main.js",
          permissions: {},
          extensionPoints: [{ type: "toolbar-button", title: "Btn2" }],
        } as any,
      }),
    ]);

    const buttons = pluginRegistry.toolbarButtons.value;
    expect(buttons.map((b) => b.plugin.id)).toEqual(["p1"]);
    expect(buttons[0].extension.title).toBe("Btn1");
  });
});

describe("首页菜单（home-menu，全局作用域）", () => {
  it("只看全局启用状态，不要求 Base 安装", () => {
    setPlugins([
      makePlugin({
        id: "p1",
        status: "enabled",
        baseEnabled: false, // 未安装到任何 Base
        manifest: {
          id: "p1",
          name: "P1",
          version: "1.0.0",
          type: "ui",
          apiVersion: "1",
          engines: { smarttable: ">=1.7.0" },
          entry: "main.js",
          permissions: {},
          extensionPoints: [{ type: "home-menu", title: "HM1" }],
        } as any,
      }),
      makePlugin({
        id: "p2",
        status: "disabled", // 全局禁用
        baseEnabled: true,
        manifest: {
          id: "p2",
          name: "P2",
          version: "1.0.0",
          type: "ui",
          apiVersion: "1",
          engines: { smarttable: ">=1.7.0" },
          entry: "main.js",
          permissions: {},
          extensionPoints: [{ type: "home-menu", title: "HM2" }],
        } as any,
      }),
    ]);
    const items = pluginRegistry.homeMenuItems.value;
    expect(items.map((i) => i.plugin.id)).toEqual(["p1"]);
  });
});

describe("仪表盘组件（dashboard-widget）", () => {
  it("收集有效启用的 ui 插件 dashboard-widget 扩展点", () => {
    setPlugins([
      makePlugin({
        id: "p1",
        status: "enabled",
        baseEnabled: true,
        manifest: {
          id: "p1",
          name: "P1",
          version: "1.0.0",
          type: "ui",
          apiVersion: "1",
          engines: { smarttable: ">=1.7.0" },
          entry: "main.js",
          permissions: {},
          extensionPoints: [{ type: "dashboard-widget", title: "DW1" }],
        } as any,
      }),
    ]);
    const items = pluginRegistry.dashboardWidgets.value;
    expect(items.map((i) => i.plugin.id)).toEqual(["p1"]);
    expect(items[0].extension.title).toBe("DW1");
  });
});

describe("错误隔离", () => {
  it("reportPluginError 记录且不掩盖其他插件；clearPluginErrors 可清除", () => {
    reportPluginError("p1", "side-panel", "boom");
    expect(pluginRegistry.errors.value.length).toBe(1);
    expect(pluginRegistry.errors.value[0].pluginId).toBe("p1");

    clearPluginErrors("p1");
    expect(pluginRegistry.errors.value.length).toBe(0);
  });
});
