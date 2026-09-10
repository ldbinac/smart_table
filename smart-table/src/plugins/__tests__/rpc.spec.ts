/**
 * RPC 桥单元测试：聚焦安全属性
 *  - 一次性握手 token 校验（不依赖 event.origin）
 *  - 未通过握手的来源窗口发起的请求一律丢弃
 *  - 权限点过滤（deny by default）
 *  - 速率限制（令牌桶）
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// ---- 准备可控的 window 环境（jsdom 下劫持 addEventListener / 记录 postMessage） ----
const captured: Array<(ev: any) => void> = [];
let posted: Array<{ win: any; msg: any }> = [];

function makeWin(): any {
  return {
    postMessage: (msg: any) => {
      posted.push({ win: undefined, msg }); // 占位，下面覆盖
    },
  };
}

const fakeIframe = makeWin();
const forgedWin = makeWin();

fakeIframe.postMessage = (msg: any) => posted.push({ win: fakeIframe, msg });
forgedWin.postMessage = (msg: any) => posted.push({ win: forgedWin, msg });

beforeEach(() => {
  captured.length = 0;
  posted = [];
  vi.stubGlobal("window", {
    addEventListener: (type: string, cb: (ev: any) => void) => {
      if (type === "message") captured.push(cb);
    },
    removeEventListener: () => {},
  });
  // 每个测试重新加载模块以确保全局监听只注册一次且状态干净
  vi.resetModules();
});

function dispatch(source: any, data: any): void {
  for (const cb of captured) cb({ source, data });
}

async function loadRpc() {
  return await import("../rpc");
}

describe("generateHandshakeToken", () => {
  it("生成唯一且非空的 token", async () => {
    const rpc = await loadRpc();
    const a = rpc.generateHandshakeToken();
    const b = rpc.generateHandshakeToken();
    expect(a).toBeTruthy();
    expect(b).toBeTruthy();
    expect(a).not.toBe(b);
  });
});

describe("RPC 握手安全（不依赖 origin）", () => {
  it("合法握手：注册 token 的窗口发起 init 后收到 initAck 并建立通道", async () => {
    const rpc = await loadRpc();
    const handlers = new Map();
    rpc.createPluginBridge({
      iframeWindow: fakeIframe,
      handshakeToken: "tok-valid",
      handlers,
      permissions: { records: "read" },
      context: { pluginId: "p1", baseId: "b1", tableId: "t1", config: {} },
    });

    dispatch(fakeIframe, { type: "init", token: "tok-valid" });

    const acks = posted.filter((p) => p.win === fakeIframe && p.msg.type === "initAck");
    expect(acks.length).toBe(1);
    expect(acks[0].msg.permissions).toEqual({ records: "read" });
  });

  it("伪造来源窗口发起的 init 被忽略（不返回 initAck）", async () => {
    const rpc = await loadRpc();
    rpc.createPluginBridge({
      iframeWindow: fakeIframe,
      handshakeToken: "tok-valid",
      handlers: new Map(),
      permissions: {},
      context: { pluginId: "p1", baseId: "b1", tableId: "t1", config: {} },
    });

    // 伪造窗口用相同 token 发起握手
    dispatch(forgedWin, { type: "init", token: "tok-valid" });

    const acksToForged = posted.filter(
      (p) => p.win === forgedWin && p.msg.type === "initAck",
    );
    expect(acksToForged.length).toBe(0);
  });

  it("未握手的窗口发起 rpc.request 被静默丢弃（无响应）", async () => {
    const rpc = await loadRpc();
    const handler = vi.fn(async () => ({ ok: true }));
    const handlers = new Map([["table.getRecords", handler]]);
    rpc.createPluginBridge({
      iframeWindow: fakeIframe,
      handshakeToken: "tok-valid",
      handlers,
      permissions: { records: "read" },
      context: { pluginId: "p1", baseId: "b1", tableId: "t1", config: {} },
    });

    // 直接以 forgedWin 发起请求（未握手）
    dispatch(forgedWin, {
      type: "rpc.request",
      id: "r1",
      method: "table.getRecords",
      params: {},
    });

    expect(handler).not.toHaveBeenCalled();
    const responses = posted.filter((p) => p.msg.type === "rpc.response");
    expect(responses.length).toBe(0);
  });

  it("已握手通道的 rpc.request 转发到对应 handler 并返回结果", async () => {
    const rpc = await loadRpc();
    const handler = vi.fn(async () => ({ items: [] }));
    const handlers = new Map([["table.getRecords", handler]]);
    rpc.createPluginBridge({
      iframeWindow: fakeIframe,
      handshakeToken: "tok-valid",
      handlers,
      permissions: { records: "read" },
      context: { pluginId: "p1", baseId: "b1", tableId: "t1", config: {} },
    });

    dispatch(fakeIframe, { type: "init", token: "tok-valid" });
    posted = []; // 清掉 initAck
    dispatch(fakeIframe, {
      type: "rpc.request",
      id: "r2",
      method: "table.getRecords",
      params: { tableId: "t1" },
    });

    // 响应在 handler await 之后异步 post，flush 微任务后断言
    await new Promise((r) => setTimeout(r, 0));

    expect(handler).toHaveBeenCalledTimes(1);
    const resp = posted.find((p) => p.win === fakeIframe && p.msg.type === "rpc.response");
    expect(resp?.msg.id).toBe("r2");
    expect(resp?.msg.result).toEqual({ items: [] });
  });

  it("未声明权限的方法调用返回 PERMISSION_DENIED", async () => {
    const rpc = await loadRpc();
    const handlers = new Map(); // 故意不注册受限方法
    rpc.createPluginBridge({
      iframeWindow: fakeIframe,
      handshakeToken: "tok-valid",
      handlers,
      permissions: { records: "read" }, // 仅 read，无 write
      context: { pluginId: "p1", baseId: "b1", tableId: "t1", config: {} },
    });

    dispatch(fakeIframe, { type: "init", token: "tok-valid" });
    posted = [];
    dispatch(fakeIframe, {
      type: "rpc.request",
      id: "r3",
      method: "record.update", // 需要 records:write，未授权
      params: { recordId: "x", values: {} },
    });

    const resp = posted.find((p) => p.msg.type === "rpc.response");
    expect(resp?.msg.error?.code).toBe("PERMISSION_DENIED");
  });

  it("超出发送速率时被限流（RATE_LIMITED）", async () => {
    const rpc = await loadRpc();
    const handler = vi.fn(async () => null);
    const handlers = new Map([["ui.notify", handler]]);
    rpc.createPluginBridge({
      iframeWindow: fakeIframe,
      handshakeToken: "tok-valid",
      handlers,
      permissions: {},
      context: { pluginId: "p1", baseId: "b1", tableId: "t1", config: {} },
    });

    dispatch(fakeIframe, { type: "init", token: "tok-valid" });
    posted = [];

    // 连续发超过阈值（RATE_LIMIT_PER_SEC=50）的请求，全部在同一时刻（令牌桶未补充）
    const limit = rpc.RATE_LIMIT_PER_SEC;
    for (let i = 0; i < limit + 5; i++) {
      dispatch(fakeIframe, {
        type: "rpc.request",
        id: `s${i}`,
        method: "ui.notify",
        params: { message: "x" },
      });
    }

    const responses = posted.filter((p) => p.msg.type === "rpc.response");
    const limited = responses.filter((p) => p.msg.error?.code === "RATE_LIMITED");
    expect(limited.length).toBeGreaterThan(0);
    expect(handler.mock.calls.length).toBeLessThanOrEqual(limit);
  });
});
