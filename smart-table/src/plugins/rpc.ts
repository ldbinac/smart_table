/**
 * 插件 RPC 通道（宿主侧 postMessage 桥）
 *
 * 安全设计：
 * 1. iframe 使用 sandbox="allow-scripts"（不带 allow-same-origin），内容为 opaque origin
 *    （event.origin 恒为 "null"），因此**不能依赖 origin 白名单**做来源校验；
 * 2. 改用握手协议：宿主创建 iframe 前生成一次性 token，经 URL fragment 传入
 *    （fragment 不进服务器日志/Referer），插件首条 init 消息携带 token，
 *    宿主校验后按 (source window, token) 绑定通道；
 * 3. 通道建立后按 event.source 匹配，未通过握手的消息一律丢弃（防伪造）；
 * 4. 逐方法权限过滤（deny by default）+ 速率限制 + 单消息大小限制。
 */
import type {
  PluginPermissions,
  ApiHandler,
  ApiHandlerContext,
  RpcMessage,
  RpcError,
} from "./types";

/** 单消息大小上限（256KB） */
export const MAX_MESSAGE_SIZE = 256 * 1024;
/** 速率限制：每通道每秒请求数 */
export const RATE_LIMIT_PER_SEC = 50;
/** 单通道待处理请求上限 */
const MAX_PENDING_CALLS = 100;

/** 握手超时（ms）：超时未握手的通道视为异常，宿主侧不响应任何请求 */
const HANDSHAKE_TIMEOUT = 10000;

interface BoundChannel {
  token: string;
  handlers: Map<string, ApiHandler>;
  permissions: PluginPermissions;
  context: Omit<ApiHandlerContext, "permissions">;
  /** 令牌桶 */
  tokens: number;
  lastRefill: number;
  timers: Set<ReturnType<typeof setTimeout>>;
}

/** 已绑定通道：以 iframe 的 contentWindow 为键（对象身份，不依赖 origin） */
const channels = new Map<Window, BoundChannel>();
/** 待握手通道：token → 宿主侧占位，握手成功后转入 channels */
const pendingTokens = new Map<string, Window>();

let initialized = false;

/**
 * 注册一次性握手 token
 * @param token 一次性 token（宿主生成）
 * @param win 目标 iframe 的 contentWindow
 */
export function registerHandshakeToken(token: string, win: Window): void {
  pendingTokens.set(token, win);
}

/** 绑定通道：握手成功后调用 */
function bindChannel(
  win: Window,
  token: string,
  handlers: Map<string, ApiHandler>,
  permissions: PluginPermissions,
  context: Omit<ApiHandlerContext, "permissions">,
): void {
  channels.set(win, {
    token,
    handlers,
    permissions,
    context,
    tokens: RATE_LIMIT_PER_SEC,
    lastRefill: Date.now(),
    timers: new Set(),
  });
}

/**
 * 创建插件 RPC 宿主桥
 * @param options.iframeWindow iframe 的 contentWindow
 * @param options.handshakeToken 一次性握手 token
 * @param options.handlers 允许的 API 方法处理器
 * @param options.permissions 插件声明的权限（deny by default）
 * @param options.context 上下文（pluginId/baseId/tableId/config）
 */
export function createPluginBridge(options: {
  iframeWindow: Window;
  handshakeToken: string;
  handlers: Map<string, ApiHandler>;
  permissions: PluginPermissions;
  context: Omit<ApiHandlerContext, "permissions">;
}): { destroy: () => void } {
  const {
    iframeWindow,
    handshakeToken,
    handlers,
    permissions,
    context,
  } = options;

  registerHandshakeToken(handshakeToken, iframeWindow);
  registerHandoffContext(handshakeToken, {
    handlers,
    permissions,
    context,
  });
  ensureGlobalListener();

  const handshakeTimer = setTimeout(() => {
    // 握手超时：撤销待握手 token，避免悬挂的通道占用
    if (pendingTokens.get(handshakeToken) === iframeWindow) {
      pendingTokens.delete(handshakeToken);
      console.warn(
        `[plugin-rpc] 插件握手超时（plugin=${context.pluginId}），已撤销 token`,
      );
    }
  }, HANDSHAKE_TIMEOUT);

  return {
    destroy() {
      clearTimeout(handshakeTimer);
      const channel = channels.get(iframeWindow);
      channel?.timers.forEach((t) => clearTimeout(t));
      channels.delete(iframeWindow);
      pendingTokens.delete(handshakeToken);
    },
  };
}

/** 全局消息监听（单例） */
function ensureGlobalListener(): void {
  if (initialized) return;
  initialized = true;
  window.addEventListener("message", handleMessage);
}

function post(win: Window, msg: RpcMessage): void {
  // 目标为 opaque origin，targetOrigin 只能用 '*'；
  // 安全性由 (source window + 握手 token) 绑定保证，而非 origin
  win.postMessage(msg, "*");
}

function makeError(code: string, message: string): RpcError {
  return { code, message };
}

/** 令牌桶限流 */
function takeToken(channel: BoundChannel): boolean {
  const now = Date.now();
  const elapsed = (now - channel.lastRefill) / 1000;
  channel.tokens = Math.min(
    RATE_LIMIT_PER_SEC,
    channel.tokens + elapsed * RATE_LIMIT_PER_SEC,
  );
  channel.lastRefill = now;
  if (channel.tokens < 1) return false;
  channel.tokens -= 1;
  return true;
}

async function handleMessage(event: MessageEvent): Promise<void> {
  const source = event.source as Window | null;
  if (!source) return;

  const data = event.data as RpcMessage | undefined;
  if (!data || typeof data !== "object" || typeof data.type !== "string") return;

  // 消息大小限制（序列化回估）
  try {
    const size = JSON.stringify(data).length;
    if (size > MAX_MESSAGE_SIZE) {
      if (data.type === "rpc.request") {
        post(source, {
          type: "rpc.response",
          id: data.id,
          error: makeError("MESSAGE_TOO_LARGE", `message exceeds ${MAX_MESSAGE_SIZE} bytes`),
        });
      }
      return;
    }
  } catch {
    return;
  }

  // ---- 握手 ----
  if (data.type === "init") {
    const token = data.token;
    const pending = pendingTokens.get(token);
    // 来源窗口必须与注册该 token 的窗口一致（防重放/伪造）
    if (!pending || pending !== source) {
      console.warn("[plugin-rpc] 丢弃非法握手消息：token 不匹配或来源窗口不一致");
      return;
    }
    pendingTokens.delete(token);

    // 从待绑定上下文取回 handlers/permissions/context
    const ctx = handoffContext.get(token);
    if (!ctx) {
      console.warn("[plugin-rpc] 握手上下文缺失，丢弃");
      return;
    }
    handoffContext.delete(token);
    bindChannel(source, token, ctx.handlers, ctx.permissions, ctx.context);

    post(source, {
      type: "initAck",
      sdk: { apiVersion: "1" },
      permissions: ctx.permissions,
    });
    return;
  }

  // ---- RPC 调用 ----
  if (data.type === "rpc.request") {
    const channel = channels.get(source);
    // 未握手的窗口发起的请求一律丢弃
    if (!channel) return;

    if (!takeToken(channel)) {
      post(source, {
        type: "rpc.response",
        id: data.id,
        error: makeError("RATE_LIMITED", `rate limit ${RATE_LIMIT_PER_SEC}/s exceeded`),
      });
      return;
    }

    const handler = channel.handlers.get(data.method);
    if (!handler) {
      post(source, {
        type: "rpc.response",
        id: data.id,
        error: makeError(
          "PERMISSION_DENIED",
          `unknown or undeclared method: ${data.method}`,
        ),
      });
      return;
    }

    try {
      const result = await handler(data.params || {}, {
        ...channel.context,
        permissions: channel.permissions,
      });
      post(source, { type: "rpc.response", id: data.id, result: result ?? null });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      post(source, {
        type: "rpc.response",
        id: data.id,
        error: makeError("INTERNAL_ERROR", message),
      });
    }
  }
}

/**
 * 待绑定上下文：token → 宿主侧准备好的通道参数
 * （createPluginBridge 时写入，握手成功后移交 channels）
 */
const handoffContext = new Map<
  string,
  {
    handlers: Map<string, ApiHandler>;
    permissions: PluginPermissions;
    context: Omit<ApiHandlerContext, "permissions">;
  }
>();

export function registerHandoffContext(
  token: string,
  ctx: {
    handlers: Map<string, ApiHandler>;
    permissions: PluginPermissions;
    context: Omit<ApiHandlerContext, "permissions">;
  },
): void {
  handoffContext.set(token, ctx);
}

/**
 * 生成一次性握手 token（UUID v4）
 */
export function generateHandshakeToken(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `tk-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export const rpcInternals = {
  channels,
  pendingTokens,
  handoffContext,
  MAX_PENDING_CALLS,
};
