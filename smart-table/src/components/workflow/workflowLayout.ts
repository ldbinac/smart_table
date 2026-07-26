import type { WorkflowNode } from "@/types/workflow";
import { getConditionBranches } from "@/utils/conditionBranch";

const VERTICAL_SPACING = 120;
const BRANCH_OFFSET_X = 280;
const BRANCH_START_Y_OFFSET = 80;
const BRANCH_STEP_Y = 150;
const CENTER_RETURN_STEP = 50;

/** 循环容器基础高度（头部 + 内边距 + 底部添加按钮） */
const LOOP_BASE_HEIGHT = 200;
/** 循环体内每个子节点占用的高度（含间距） */
const LOOP_CHILD_HEIGHT = 80;

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
 * 计算 loop 节点占用的高度（含循环体子节点）。
 */
function getLoopNodeHeight(node: WorkflowNode): number {
  if (node.node_type !== "loop") return VERTICAL_SPACING;
  const bodyNodes = (node.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
  return LOOP_BASE_HEIGHT + LOOP_CHILD_HEIGHT * bodyNodes.length;
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
 * - loop 节点根据循环体子节点数量动态计算高度，并预留垂直空间。
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
      const nodeHeight =
        node.node_type === "loop" ? getLoopNodeHeight(node) : VERTICAL_SPACING;
      cursorY = Math.max(cursorY, node.ui_layout!.y + nodeHeight);
      if (node.node_type === "condition") {
        lastConditionY = node.ui_layout!.y;
      }
      continue;
    }

    let x: number;
    let y: number;
    let nodeHeight: number;

    if (node.node_type === "condition") {
      x = 0;
      y = cursorY;
      lastConditionY = y;
      nodeHeight = VERTICAL_SPACING;
      cursorY = y + nodeHeight;
      branchReturnX = null;
    } else if (node.node_type === "loop") {
      x = 0;
      y = cursorY;
      nodeHeight = getLoopNodeHeight(node);
      cursorY = y + nodeHeight;
      branchReturnX = null;
    } else if (branchTargets.has(node.id)) {
      const target = branchTargets.get(node.id)!;
      x = BRANCH_OFFSET_X;
      y = lastConditionY + BRANCH_START_Y_OFFSET + target.index * BRANCH_STEP_Y;
      nodeHeight = VERTICAL_SPACING;
      cursorY = Math.max(cursorY, y + nodeHeight);
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
      nodeHeight = VERTICAL_SPACING;
      cursorY = y + nodeHeight;
    }

    result.push({
      ...node,
      ui_layout: { x, y },
    });
  }

  return result;
}
