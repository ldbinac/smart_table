import type { WorkflowNode } from "@/types/workflow";
import { getConditionBranches } from "@/utils/conditionBranch";

const VERTICAL_SPACING = 120;
const BRANCH_OFFSET_X = 280;
const BRANCH_START_Y_OFFSET = 80;
const BRANCH_STEP_Y = 150;
const CENTER_RETURN_STEP = 50;

export function hasValidLayout(node: WorkflowNode): boolean {
  const layout = node.ui_layout;
  return (
    !!layout &&
    typeof layout.x === "number" &&
    typeof layout.y === "number" &&
    !Number.isNaN(layout.x) &&
    !Number.isNaN(layout.y)
  );
}

/**
 * 为没有 `ui_layout` 的工作流节点计算自动布局坐标。
 *
 * 规则：
 * - 已有有效 `ui_layout` 的节点保持原样。
 * - 节点按 `order` 升序排列。
 * - 普通节点垂直单列排列，x=0。
 * - 条件节点的每个分支目标节点在右侧垂直分布，避免重叠。
 * - 分支结束后，后续节点逐步向中心靠拢，最终回到 x=0 的主列。
 */
export function layoutWorkflowNodes(nodes: WorkflowNode[]): WorkflowNode[] {
  // 收集每个条件节点的分支目标 ID，按顺序分配 Y 偏移
  const branchTargets = new Map<string, { conditionY: number; index: number }>();
  nodes.forEach((node) => {
    if (node.node_type !== "condition") return;
    const conditionY = hasValidLayout(node)
      ? node.ui_layout!.y
      : undefined;
    getConditionBranches(node.config).forEach((branch, index) => {
      if (!branch.target_node_id) return;
      branchTargets.set(branch.target_node_id, {
        conditionY: conditionY ?? 0,
        index,
      });
    });
  });

  const sorted = [...nodes].sort((a, b) => a.order - b.order);
  const result: WorkflowNode[] = [];

  let cursorY = 0;
  let lastConditionY = 0;
  let branchReturnX: number | null = null;

  for (const node of sorted) {
    if (hasValidLayout(node)) {
      result.push(node);
      cursorY = Math.max(cursorY, node.ui_layout!.y + VERTICAL_SPACING);
      if (node.node_type === "condition") {
        lastConditionY = node.ui_layout!.y;
      }
      continue;
    }

    let x: number;
    let y: number;

    if (node.node_type === "condition") {
      x = 0;
      y = cursorY;
      lastConditionY = y;
      cursorY = y + VERTICAL_SPACING;
      branchReturnX = null;
    } else if (branchTargets.has(node.id)) {
      const target = branchTargets.get(node.id)!;
      x = BRANCH_OFFSET_X;
      y = lastConditionY + BRANCH_START_Y_OFFSET + target.index * BRANCH_STEP_Y;
      cursorY = Math.max(cursorY, y + VERTICAL_SPACING);
      branchReturnX = BRANCH_OFFSET_X;
    } else {
      if (branchReturnX !== null && branchReturnX > 0) {
        x = Math.max(0, branchReturnX - CENTER_RETURN_STEP);
        y = cursorY;
        branchReturnX = x;
      } else {
        x = 0;
        y = cursorY;
      }
      cursorY = y + VERTICAL_SPACING;
    }

    result.push({
      ...node,
      ui_layout: { x, y },
    });
  }

  return result;
}
