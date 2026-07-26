import type { WorkflowNode, ScheduleConfig, LoopDataSource } from "@/types/workflow";
import { getConditionBranches } from "@/utils/conditionBranch";
import dayjs from "dayjs";

/**
 * 循环节点数据源可选项。
 */
export interface LoopDataSourceOption {
  label: string;
  value: LoopDataSource;
}

/**
 * 循环数据源支持的字段类型：
 * 人员、群组、附件、单向关联、双向关联。
 */
const LOOP_ALLOWED_FIELD_TYPES = ["member", "collaborator", "attachment", "link"];

/**
 * 获取循环节点可用的前序数据源列表。
 *
 * 规则：
 * - 遍历 order 小于当前节点的前序节点；
 * - find_records 节点 → 提供"所有记录"选项 + "某列值"选项（仅允许人员/群组/附件/关联字段）；
 * - webhook 节点 → 提供"json.array"选项；
 * - 触发器字段（始终可用）→ 提供人员/群组/附件/关联字段选项。
 *
 * 注意：若 currentNodeId 不在 nodes 中（例如循环体子节点配置场景），
 * 将所有 nodes 视为前序节点，便于子循环节点引用顶层前序数据源。
 */
export function getAvailableLoopDataSources(
  nodes: WorkflowNode[],
  currentNodeId: string,
  fields: Array<{ id: string; name: string; type: string }>,
): LoopDataSourceOption[] {
  const currentNode = nodes.find((n) => n.id === currentNodeId);
  // 未找到当前节点时，将所有节点视为前序节点（子循环引用顶层前序数据源场景）
  const currentOrder = currentNode ? currentNode.order : Infinity;

  const predecessorNodes = nodes
    .filter((n) => n.order < currentOrder)
    .sort((a, b) => a.order - b.order);

  const options: LoopDataSourceOption[] = [];
  const allowedFields = fields.filter((f) =>
    LOOP_ALLOWED_FIELD_TYPES.includes(f.type),
  );

  // 前序 find_records 节点
  predecessorNodes
    .filter((n) => n.node_type === "find_records")
    .forEach((n) => {
      const varName = (n.config?.result_variable as string | undefined) ?? "records";
      options.push({
        label: `${n.name} - 所有记录（${varName}）`,
        value: { type: "find_records_all", node_id: n.id },
      });
      allowedFields.forEach((f) => {
        options.push({
          label: `${n.name} - ${f.name}`,
          value: {
            type: "find_records_column",
            node_id: n.id,
            field_id: f.id,
          },
        });
      });
    });

  // 前序 webhook 节点
  predecessorNodes
    .filter((n) => n.node_type === "webhook")
    .forEach((n) => {
      options.push({
        label: `${n.name} - json.array`,
        value: { type: "webhook_array", node_id: n.id },
      });
    });

  // 触发器字段（始终可用，因为工作流必然有触发器）
  allowedFields.forEach((f) => {
    options.push({
      label: `触发器 - ${f.name}`,
      value: {
        type: "trigger_field",
        field_id: f.id,
        trigger_field_id: f.id,
      },
    });
  });

  return options;
}

/**
 * 动作类型反向映射：旧版后端 action + config.action_type -> 前端细粒度 node_type
 * 仅用于向后兼容历史版本快照数据，新数据已直接使用细粒度 node_type。
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
 * - loop 节点的循环体子节点（config.loop_body_nodes）也会递归重建子链。
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
  return nodes.map((node) => {
    // 对 loop 节点递归重建循环体子链
    if (node.node_type === "loop") {
      const config = node.config || {};
      const loopBodyNodes = (config.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
      if (loopBodyNodes.length > 0) {
        const rebuiltBodyNodes = rebuildWorkflowNodeChain(loopBodyNodes);
        return {
          ...node,
          next_nodes: nextMap.get(node.id) ?? [],
          config: { ...config, loop_body_nodes: rebuiltBodyNodes },
        };
      }
    }
    return {
      ...node,
      next_nodes: nextMap.get(node.id) ?? [],
    };
  });
}

/**
 * 判断触发类型是否为“指定时间”触发器。
 */
export function isSpecifiedTimeTrigger(trigger_type: string): boolean {
  return trigger_type === "specified_time";
}

/**
 * 判断触发类型是否为"到达记录中的时间时"触发器。
 */
export function isRecordTimeReachedTrigger(trigger_type: string): boolean {
  return trigger_type === "record_time_reached";
}

export function isValidWorkflowVariableName(name: string): boolean {
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

/**
 * 创建循环节点的默认配置。
 */
export function createDefaultLoopNodeConfig(): Record<string, unknown> {
  return {
    loop_mode: "sequential",
    data_source: { type: "find_records_all" },
    max_iterations: 100,
    error_handling: "skip",
    empty_result_action: "skip",
    loop_body_nodes: [],
  };
}

/**
 * 递归统计节点列表中 loop 节点的总数（含嵌套循环体内的）。
 */
export function countLoopNodes(nodes: WorkflowNode[]): number {
  let count = 0;
  for (const node of nodes) {
    if (node.node_type !== "loop") continue;
    count += 1;
    const loopBodyNodes = (node.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
    count += countLoopNodes(loopBodyNodes);
  }
  return count;
}

/**
 * 计算节点列表中 loop 节点的最大嵌套深度。
 * 顶层 loop 为深度 1，嵌套层累加。
 */
export function getMaxLoopNestingDepth(nodes: WorkflowNode[]): number {
  let maxDepth = 0;
  for (const node of nodes) {
    if (node.node_type !== "loop") continue;
    const loopBodyNodes = (node.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
    const childDepth = getMaxLoopNestingDepth(loopBodyNodes);
    maxDepth = Math.max(maxDepth, 1 + childDepth);
  }
  return maxDepth;
}

/**
 * 判断指定节点是否位于某个 loop 容器内（即作为某 loop 节点的循环体子节点）。
 * 返回父 loop 节点 ID，不在循环体内返回 null。
 */
export function findParentLoopNodeId(
  nodes: WorkflowNode[],
  nodeId: string,
): string | null {
  for (const node of nodes) {
    if (node.node_type !== "loop") continue;
    const loopBodyNodes = (node.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
    if (loopBodyNodes.some((n) => n.id === nodeId)) {
      return node.id;
    }
    // 递归查找嵌套循环
    const nested = findParentLoopNodeId(loopBodyNodes, nodeId);
    if (nested) return nested;
  }
  return null;
}

/**
 * 获取 loop 节点的循环体子节点列表。
 */
export function getLoopBodyNodes(node: WorkflowNode): WorkflowNode[] {
  if (node.node_type !== "loop") return [];
  return (node.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
}

/**
 * 设置 loop 节点的循环体子节点列表，返回更新后的节点。
 */
export function setLoopBodyNodes(
  node: WorkflowNode,
  bodyNodes: WorkflowNode[],
): WorkflowNode {
  if (node.node_type !== "loop") return node;
  return {
    ...node,
    config: { ...node.config, loop_body_nodes: bodyNodes },
  };
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
