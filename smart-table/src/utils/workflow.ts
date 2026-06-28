import type { WorkflowNode } from "@/types/workflow";

/**
 * 动作类型反向映射：后端 action + config.action_type -> 前端细粒度 node_type
 */
const ACTION_TYPE_TO_FRONTEND: Record<string, WorkflowNode["node_type"]> = {
  update_record: "update_record",
  create_record: "create_record",
  send_email: "send_email",
  trigger_webhook: "webhook",
};

/**
 * 将后端返回的节点数据规范化为前端可识别的 node_type。
 * 兼容已存在的历史版本快照（action + action_type）。
 */
export function normalizeWorkflowNode(node: WorkflowNode): WorkflowNode {
  if (node.node_type !== "action") {
    return node;
  }
  const actionType = node.config?.action_type as string | undefined;
  const frontendType = actionType
    ? ACTION_TYPE_TO_FRONTEND[actionType]
    : undefined;
  if (!frontendType) {
    return node;
  }
  return {
    ...node,
    node_type: frontendType,
  };
}

export function normalizeWorkflowNodes(nodes: WorkflowNode[]): WorkflowNode[] {
  return nodes.map(normalizeWorkflowNode);
}
