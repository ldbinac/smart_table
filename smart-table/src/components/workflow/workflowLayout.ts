import type { WorkflowNode } from "@/types/workflow";

const VERTICAL_SPACING = 120;
const BRANCH_OFFSET_X = 200;
const BRANCH_START_Y_OFFSET = 80;
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
 * - 普通节点垂直单列排列，x=0，y=order*VERTICAL_SPACING。
 * - 条件节点的“满足条件”分支节点（即其 `next_nodes` 指向的节点）向右偏移展示。
 * - 分支结束后，后续节点逐步向中心靠拢，最终回到 x=0 的主列。
 */
export function layoutWorkflowNodes(nodes: WorkflowNode[]): WorkflowNode[] {
  // 收集所有条件节点的分支目标 ID（MVP 阶段仅处理“满足条件”分支）
  const branchTargetIds = new Set<string>();
  nodes.forEach((node) => {
    if (node.node_type === "condition" && Array.isArray(node.next_nodes)) {
      node.next_nodes.forEach((id) => branchTargetIds.add(id));
    }
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
    } else if (branchTargetIds.has(node.id)) {
      x = BRANCH_OFFSET_X;
      y = lastConditionY + BRANCH_START_Y_OFFSET;
      cursorY = y + VERTICAL_SPACING;
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
