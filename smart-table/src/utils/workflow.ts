import type { WorkflowNode, ScheduleConfig } from "@/types/workflow";
import dayjs from "dayjs";

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

/**
 * 判断触发类型是否为“指定时间”触发器。
 */
export function isSpecifiedTimeTrigger(trigger_type: string): boolean {
  return trigger_type === "specified_time";
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
  };
}
