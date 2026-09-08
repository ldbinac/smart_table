/**
 * 表格勾选 → 插件 的数据通道（宿主侧）
 *
 * 设计要点：
 * 1. **只传记录 ID**：快照仅含 recordId 列表 + 总数/全选/截断标记，插件按需用
 *    `table.getRecord` 取详情，避免大批量数据进入沙箱上下文；
 * 2. **打开时快照**：宿主在打开插件的瞬间生成快照并注入 RPC context，
 *    不推送后续变更（勾选变化需重新打开插件感知）；
 * 3. **宿主可插拔**：表格侧只需实现 `SelectionProvider` 接口并注册，
 *    插件/SDK 不依赖任何具体表格组件，便于适配 VTable、原生表格或其他组件库。
 */
import type { SelectionSnapshot, SelectionSummary } from "./types";

/** 单次快照允许传递的最大记录 ID 数（超出则截断并标记 truncated） */
export const MAX_SELECTION_IDS = 1000;

/** 表格/视图向插件体系提供勾选状态的适配接口 */
export interface SelectionProvider {
  getSelection: () => SelectionSummary | null;
}

let provider: SelectionProvider | null = null;

/** 注册/注销勾选状态提供方（页面切换表格实现时替换） */
export function registerSelectionProvider(p: SelectionProvider | null): void {
  provider = p;
}

/** 读取当前勾选摘要（供工具栏按钮可用性判断） */
export function getSelectionSummary(): SelectionSummary | null {
  if (!provider) return null;
  try {
    return provider.getSelection();
  } catch (error) {
    console.warn("[plugin-selection] 读取勾选状态失败:", error);
    return null;
  }
}

/** 生成传给插件的勾选快照（打开插件时调用一次） */
export function buildSelectionSnapshot(): SelectionSnapshot {
  const summary = getSelectionSummary();
  const recordIds = summary?.recordIds ?? [];
  const total = summary?.total ?? recordIds.length;
  const truncated = recordIds.length > MAX_SELECTION_IDS;
  return {
    recordIds: truncated
      ? recordIds.slice(0, MAX_SELECTION_IDS)
      : [...recordIds],
    total,
    truncated,
    selectAll: Boolean(summary?.selectAll),
    scope: summary?.scope ?? "page",
    at: Date.now(),
  };
}

/** 校验当前勾选是否满足扩展点声明（按钮可用性/点击校验） */
export function checkSelectionRequirement(
  summary: SelectionSummary | null,
  opts: { requiresSelection?: boolean; maxSelection?: number },
): { ok: boolean; count: number; reason?: "empty" | "tooMany" } {
  const count = summary?.total ?? 0;
  if (opts.requiresSelection && count === 0) {
    return { ok: false, count, reason: "empty" };
  }
  if (opts.maxSelection !== undefined && count > opts.maxSelection) {
    return { ok: false, count, reason: "tooMany" };
  }
  return { ok: true, count };
}
