import type { WorkflowNode, ScheduleConfig } from "@/types/workflow";
import { getConditionBranches } from "@/utils/conditionBranch";
import dayjs from "dayjs";

/**
 * 动作类型反向映射：后端 action + config.action_type -> 前端细粒度 node_type
 */
const ACTION_TYPE_TO_FRONTEND: Record<string, WorkflowNode["node_type"]> = {
  update_record: "update_record",
  create_record: "create_record",
  send_email: "send_email",
  trigger_webhook: "webhook",
  find_records: "find_records",
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

/**
 * 按 order 自动重建节点执行链：
 * - 条件节点的 next_nodes 由其 branches 中的 target_node_id 决定；
 * - 普通节点默认指向下一个节点；
 * - 分支目标节点可链接到下一个非分支目标节点（合并点或后续节点），
 *   但不会自动链接到任何分支目标节点，以保持并行分支独立。
 */
export function rebuildWorkflowNodeChain(nodes: WorkflowNode[]): WorkflowNode[] {
  const sorted = [...nodes].sort((a, b) => a.order - b.order);
  const branchTargetIds = new Set<string>();
  sorted.forEach((node) => {
    if (node.node_type !== "condition") return;
    getConditionBranches(node.config).forEach((branch) => {
      if (branch.target_node_id) branchTargetIds.add(branch.target_node_id);
    });
  });
  const nextMap = new Map<string, string[]>();
  sorted.forEach((node, index) => {
    if (node.node_type === "condition") {
      const nextIds = getConditionBranches(node.config)
        .map((b) => b.target_node_id)
        .filter((id): id is string => !!id);
      nextMap.set(node.id, nextIds);
    } else {
      const nextNode = sorted[index + 1];
      if (!nextNode || branchTargetIds.has(nextNode.id)) {
        nextMap.set(node.id, []);
      } else {
        nextMap.set(node.id, [nextNode.id]);
      }
    }
  });
  return nodes.map((node) => ({
    ...node,
    next_nodes: nextMap.get(node.id) ?? [],
  }));
}

/**
 * 判断触发类型是否为“指定时间”触发器。
 */
export function isSpecifiedTimeTrigger(trigger_type: string): boolean {
  return trigger_type === "specified_time";
}

export function isValidWorkflowVariableName(name: string): boolean {
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

/**
 * 创建一个默认的定时器配置对象。
 * 默认：当前日期、00:00、不重复、自定义间隔 1 天、无截止日期。
 */
export function createDefaultScheduleConfig(): ScheduleConfig {
  return {
    start_date: dayjs().format("YYYY-MM-DD"),
    start_time: "00:00",
    repeat_type: "no_repeat",
    custom_interval: 1,
    custom_unit: "day",
    end_type: "never",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}
