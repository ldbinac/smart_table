import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { WorkflowNode, TriggerType, ScheduleConfig } from "@/types/workflow";
import {
  normalizeWorkflowNode,
  normalizeWorkflowNodes,
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

    it("对非 action 节点原样返回", () => {
      const node = makeNode("approval", { mode: "any" });
      const result = normalizeWorkflowNode(node);
      expect(result.node_type).toBe("approval");
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
        makeNode("approval"),
      ];
      const result = normalizeWorkflowNodes(nodes);
      expect(result[0].node_type).toBe("create_record");
      expect(result[1].node_type).toBe("update_record");
      expect(result[2].node_type).toBe("approval");
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
