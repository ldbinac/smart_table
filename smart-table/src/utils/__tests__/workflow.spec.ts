import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { WorkflowNode, TriggerType, ScheduleConfig } from "@/types/workflow";
import {
  normalizeWorkflowNode,
  normalizeWorkflowNodes,
  rebuildWorkflowNodeChain,
  isSpecifiedTimeTrigger,
  createDefaultScheduleConfig,
} from "@/utils/workflow";

function makeNode(
  nodeType: WorkflowNode["node_type"],
  config: Record<string, unknown> = {}
): WorkflowNode {
  return {
    id: "node-1",
    workflow_id: "wf-1",
    node_type: nodeType,
    name: "测试节点",
    config,
    order: 0,
    next_nodes: [],
  };
}

function makeConditionNode(
  id: string,
  order: number,
  targetNodeIds: (string | undefined)[]
): WorkflowNode {
  return {
    id,
    workflow_id: "wf-1",
    node_type: "condition",
    name: "条件节点",
    config: {
      branches: targetNodeIds.map((targetId, index) => ({
        id: `b${index + 1}`,
        name: `分支 ${index + 1}`,
        conditions: [{ field_id: "f1", operator: "equals", value: `v${index + 1}` }],
        conjunction: "and",
        target_node_id: targetId,
      })),
    },
    order,
    next_nodes: targetNodeIds.filter((id): id is string => !!id),
  };
}

describe("workflow utils", () => {
  describe("normalizeWorkflowNode", () => {
    it("将 action + create_record 转换为 create_record", () => {
      const node = makeNode("action", { action_type: "create_record" });
      const result = normalizeWorkflowNode(node);
      expect(result.node_type).toBe("create_record");
      expect(result.config.action_type).toBe("create_record");
    });

    it("将 action + update_record 转换为 update_record", () => {
      const node = makeNode("action", { action_type: "update_record" });
      expect(normalizeWorkflowNode(node).node_type).toBe("update_record");
    });

    it("将 action + send_email 转换为 send_email", () => {
      const node = makeNode("action", { action_type: "send_email" });
      expect(normalizeWorkflowNode(node).node_type).toBe("send_email");
    });

    it("将 action + trigger_webhook 转换为 webhook", () => {
      const node = makeNode("action", { action_type: "trigger_webhook" });
      expect(normalizeWorkflowNode(node).node_type).toBe("webhook");
    });

    it("将 action + find_records 转换为 find_records", () => {
      const node = makeNode("action", { action_type: "find_records" });
      expect(normalizeWorkflowNode(node).node_type).toBe("find_records");
    });

    it("对非 action 节点原样返回", () => {
      const node = makeNode("send_email", { recipient_type: "field" });
      const result = normalizeWorkflowNode(node);
      expect(result.node_type).toBe("send_email");
      expect(result.config).toEqual(node.config);
    });

    it("对未知 action_type 保持 action 不变", () => {
      const node = makeNode("action", { action_type: "unknown_type" });
      const result = normalizeWorkflowNode(node);
      expect(result.node_type).toBe("action");
    });

    it("对缺少 action_type 的 action 节点保持 action 不变", () => {
      const node = makeNode("action", {});
      const result = normalizeWorkflowNode(node);
      expect(result.node_type).toBe("action");
    });
  });

  describe("normalizeWorkflowNodes", () => {
    it("批量规范化节点列表", () => {
      const nodes = [
        makeNode("action", { action_type: "create_record" }),
        makeNode("action", { action_type: "update_record" }),
        makeNode("send_email"),
      ];
      const result = normalizeWorkflowNodes(nodes);
      expect(result[0].node_type).toBe("create_record");
      expect(result[1].node_type).toBe("update_record");
      expect(result[2].node_type).toBe("send_email");
    });
  });

  describe("rebuildWorkflowNodeChain", () => {
    it("按 order 把每个节点指向下一个节点", () => {
      const nodes: WorkflowNode[] = [
        { ...makeNode("update_record"), id: "n1", order: 0 },
        { ...makeNode("create_record"), id: "n2", order: 1 },
        { ...makeNode("webhook"), id: "n3", order: 2 },
      ];
      const result = rebuildWorkflowNodeChain(nodes);
      expect(result[0].next_nodes).toEqual(["n2"]);
      expect(result[1].next_nodes).toEqual(["n3"]);
      expect(result[2].next_nodes).toEqual([]);
    });

    it("对乱序输入仍能按 order 正确链接", () => {
      const nodes: WorkflowNode[] = [
        { ...makeNode("update_record"), id: "n2", order: 1 },
        { ...makeNode("webhook"), id: "n3", order: 2 },
        { ...makeNode("create_record"), id: "n1", order: 0 },
      ];
      const result = rebuildWorkflowNodeChain(nodes);
      const byOrder = [...result].sort((a, b) => a.order - b.order);
      expect(byOrder[0].next_nodes).toEqual(["n2"]);
      expect(byOrder[1].next_nodes).toEqual(["n3"]);
      expect(byOrder[2].next_nodes).toEqual([]);
    });

    it("单节点时 next_nodes 为空", () => {
      const nodes: WorkflowNode[] = [{ ...makeNode("update_record"), id: "n1", order: 0 }];
      const result = rebuildWorkflowNodeChain(nodes);
      expect(result[0].next_nodes).toEqual([]);
    });

    it("空节点列表返回空数组", () => {
      expect(rebuildWorkflowNodeChain([])).toEqual([]);
    });

    it("条件节点的 next_nodes 由 branches 的 target_node_id 决定", () => {
      const nodes: WorkflowNode[] = [
        makeConditionNode("cond", 0, ["n1", "n2"]),
        { ...makeNode("webhook"), id: "n1", order: 1 },
        { ...makeNode("webhook"), id: "n2", order: 2 },
      ];
      const result = rebuildWorkflowNodeChain(nodes);
      const conditionNode = result.find((n) => n.id === "cond")!;
      expect(conditionNode.next_nodes).toEqual(["n1", "n2"]);
    });

    it("条件分支目标节点不会被自动串联", () => {
      const nodes: WorkflowNode[] = [
        makeConditionNode("cond", 0, ["branch-a", "branch-b"]),
        { ...makeNode("update_record"), id: "branch-a", order: 1 },
        { ...makeNode("create_record"), id: "branch-b", order: 2 },
      ];
      const result = rebuildWorkflowNodeChain(nodes);
      const branchA = result.find((n) => n.id === "branch-a")!;
      const branchB = result.find((n) => n.id === "branch-b")!;
      expect(branchA.next_nodes).toEqual([]);
      expect(branchB.next_nodes).toEqual([]);
    });

    it("分支目标节点可链接到后续非分支目标节点", () => {
      const nodes: WorkflowNode[] = [
        makeConditionNode("cond", 0, ["branch"]),
        { ...makeNode("update_record"), id: "branch", order: 1 },
        { ...makeNode("webhook"), id: "merge", order: 2 },
      ];
      const result = rebuildWorkflowNodeChain(nodes);
      const branch = result.find((n) => n.id === "branch")!;
      const merge = result.find((n) => n.id === "merge")!;
      expect(branch.next_nodes).toEqual(["merge"]);
      expect(merge.next_nodes).toEqual([]);
    });

    it("条件节点未设置 target 的分支不会出现在 next_nodes 中", () => {
      const nodes: WorkflowNode[] = [
        makeConditionNode("cond", 0, ["n1", undefined]),
        { ...makeNode("webhook"), id: "n1", order: 1 },
      ];
      const result = rebuildWorkflowNodeChain(nodes);
      const conditionNode = result.find((n) => n.id === "cond")!;
      expect(conditionNode.next_nodes).toEqual(["n1"]);
    });
  });

  describe("isSpecifiedTimeTrigger", () => {
    it("对 specified_time 返回 true", () => {
      expect(isSpecifiedTimeTrigger("specified_time")).toBe(true);
    });

    it("对其他 TriggerType 返回 false", () => {
      const otherTypes: TriggerType[] = [
        "record_created",
        "record_updated",
        "field_changed",
        "manual",
      ];
      otherTypes.forEach((type) => {
        expect(isSpecifiedTimeTrigger(type)).toBe(false);
      });
    });

    it("对非预期字符串返回 false", () => {
      expect(isSpecifiedTimeTrigger("unknown_type")).toBe(false);
    });
  });

  describe("createDefaultScheduleConfig", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date("2026-06-29T12:00:00"));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("返回以当前日期和 00:00 为默认值的 no_repeat 定时配置", () => {
      const config: ScheduleConfig = createDefaultScheduleConfig();
      expect(config.start_date).toBe("2026-06-29");
      expect(config.start_time).toBe("00:00");
      expect(config.repeat_type).toBe("no_repeat");
      expect(config.custom_interval).toBe(1);
      expect(config.custom_unit).toBe("day");
      expect(config.end_type).toBe("never");
      expect(config.end_date).toBeUndefined();
    });
  });
});
