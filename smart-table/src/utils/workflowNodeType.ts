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
  Refresh,
  Cpu,
} from "@element-plus/icons-vue";
import type { WorkflowNodeType } from "@/types/workflow";
import { useI18n } from "vue-i18n";

/** 节点类型选项（含 type + label + icon） */
export interface WorkflowNodeTypeOption {
  type: string;
  label: string;
  icon: typeof CircleCheck;
}

/** 节点类型 → i18n key 映射（label 字段存 i18n key，运行时通过 getNodeLabel 翻译） */
export const NODE_TYPE_I18N_KEY: Record<string, string> = {
  trigger: "workflow.nodeType.trigger",
  condition: "workflow.nodeType.condition",
  update_record: "workflow.nodeType.update_record",
  create_record: "workflow.nodeType.create_record",
  find_records: "workflow.nodeType.find_records",
  send_email: "workflow.nodeType.send_email",
  webhook: "workflow.nodeType.webhook",
  action: "workflow.nodeType.action",
  loop: "workflow.nodeType.loop",
  script: "workflow.nodeType.script",
};

/** 节点类型 → 中文名称映射（i18n 不可用时回退） */
export const NODE_TYPE_LABEL_MAP: Record<string, string> = {
  trigger: "触发器",
  condition: "条件节点",
  update_record: "更新记录",
  create_record: "创建记录",
  find_records: "查找记录",
  send_email: "发送邮件",
  webhook: "Webhook",
  action: "动作节点",
  loop: "循环",
  script: "自定义脚本",
};

/** 所有可添加的节点类型列表（不含 trigger，触发器由系统自动创建） */
export const ADDABLE_NODE_TYPES: WorkflowNodeTypeOption[] = [
  { type: "update_record", label: NODE_TYPE_I18N_KEY.update_record, icon: EditPen },
  { type: "create_record", label: NODE_TYPE_I18N_KEY.create_record, icon: Plus },
  { type: "find_records", label: NODE_TYPE_I18N_KEY.find_records, icon: Search },
  { type: "send_email", label: NODE_TYPE_I18N_KEY.send_email, icon: Message },
  { type: "webhook", label: NODE_TYPE_I18N_KEY.webhook, icon: Link },
  { type: "condition", label: NODE_TYPE_I18N_KEY.condition, icon: Share },
  { type: "loop", label: NODE_TYPE_I18N_KEY.loop, icon: Refresh },
  { type: "script", label: NODE_TYPE_I18N_KEY.script, icon: Cpu },
];

/** 循环体内允许的节点类型（不含 condition） */
export const LOOP_BODY_ALLOWED_NODE_TYPES: WorkflowNodeTypeOption[] = [
  { type: "update_record", label: NODE_TYPE_I18N_KEY.update_record, icon: EditPen },
  { type: "create_record", label: NODE_TYPE_I18N_KEY.create_record, icon: Plus },
  { type: "find_records", label: NODE_TYPE_I18N_KEY.find_records, icon: Search },
  { type: "send_email", label: NODE_TYPE_I18N_KEY.send_email, icon: Message },
  { type: "webhook", label: NODE_TYPE_I18N_KEY.webhook, icon: Link },
  { type: "loop", label: NODE_TYPE_I18N_KEY.loop, icon: Refresh },
  { type: "script", label: NODE_TYPE_I18N_KEY.script, icon: Cpu },
];

/** 所有节点类型列表（含 trigger） */
export const ALL_NODE_TYPES: WorkflowNodeTypeOption[] = [
  { type: "trigger", label: NODE_TYPE_I18N_KEY.trigger, icon: CircleCheck },
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
  loop: Refresh,
  script: Cpu,
};

/** 获取节点类型名称（优先 i18n 翻译，无可用实例时回退中文） */
export function getNodeLabel(type: WorkflowNodeType | string): string {
  const fallback = NODE_TYPE_LABEL_MAP[type] ?? (type as string);
  try {
    const { t } = useI18n();
    const key = NODE_TYPE_I18N_KEY[type];
    return key ? t(key) : fallback;
  } catch {
    return fallback;
  }
}

/** 获取节点类型的图标组件 */
export function getNodeIcon(type: WorkflowNodeType | string): typeof CircleCheck {
  return NODE_TYPE_ICON_MAP[type] ?? CircleCheck;
}

/** 循环节点最大数量限制 */
export const MAX_LOOP_NODES_PER_WORKFLOW = 5;

/** 循环节点最大嵌套深度 */
export const MAX_LOOP_NESTING_DEPTH = 3;
