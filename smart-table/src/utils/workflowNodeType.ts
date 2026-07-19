/**
 * 工作流节点类型公共定义
 * 统一管理节点类型、名称和图标的映射关系，避免各组件重复定义导致不一致
 */
import {
  CircleCheck,
  Share,
  EditPen,
  Plus,
  Message,
  Link,
  Search,
} from "@element-plus/icons-vue";
import type { WorkflowNodeType } from "@/types/workflow";

/** 节点类型选项（含 type + label + icon） */
export interface WorkflowNodeTypeOption {
  type: string;
  label: string;
  icon: typeof CircleCheck;
}

/** 所有可添加的节点类型列表（不含 trigger，触发器由系统自动创建） */
export const ADDABLE_NODE_TYPES: WorkflowNodeTypeOption[] = [
  { type: "update_record", label: "更新记录", icon: EditPen },
  { type: "create_record", label: "创建记录", icon: Plus },
  { type: "find_records", label: "查找记录", icon: Search },
  { type: "send_email", label: "发送邮件", icon: Message },
  { type: "webhook", label: "Webhook", icon: Link },
  { type: "condition", label: "条件节点", icon: Share },
];

/** 所有节点类型列表（含 trigger） */
export const ALL_NODE_TYPES: WorkflowNodeTypeOption[] = [
  { type: "trigger", label: "触发器", icon: CircleCheck },
  ...ADDABLE_NODE_TYPES,
];

/** 节点类型 → 图标映射 */
export const NODE_TYPE_ICON_MAP: Record<string, typeof CircleCheck> = {
  trigger: CircleCheck,
  condition: Share,
  update_record: EditPen,
  create_record: Plus,
  find_records: Search,
  send_email: Message,
  webhook: Link,
  action: EditPen,
};

/** 节点类型 → 中文名称映射 */
export const NODE_TYPE_LABEL_MAP: Record<string, string> = {
  trigger: "触发器",
  condition: "条件节点",
  update_record: "更新记录",
  create_record: "创建记录",
  find_records: "查找记录",
  send_email: "发送邮件",
  webhook: "Webhook",
  action: "动作节点",
};

/** 获取节点类型的中文名称 */
export function getNodeLabel(type: WorkflowNodeType | string): string {
  return NODE_TYPE_LABEL_MAP[type] ?? type;
}

/** 获取节点类型的图标组件 */
export function getNodeIcon(type: WorkflowNodeType | string): typeof CircleCheck {
  return NODE_TYPE_ICON_MAP[type] ?? CircleCheck;
}
