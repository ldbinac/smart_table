/**
 * 工作流类型定义
 * 与后端 Workflow / Webhook / Template 模型保持一致
 */

export type WorkflowNodeType =
  | 'trigger'
  | 'action'
  | 'condition'
  | 'update_record'
  | 'create_record'
  | 'send_email'
  | 'webhook'
  | 'find_records'
  | 'loop'
  | 'script';

/** 循环节点数据源类型 */
export type LoopDataSourceType =
  | 'find_records_all'
  | 'find_records_column'
  | 'trigger_field'
  | 'webhook_array';

/** 循环节点数据源配置 */
export interface LoopDataSource {
  /** 数据源类型 */
  type: LoopDataSourceType;
  /** 前序节点 ID（find_records / webhook 节点） */
  node_id?: string;
  /** 字段 ID（find_records_column / trigger_field 时使用，仅限人员/群组/附件/关联字段） */
  field_id?: string;
  /** 触发器字段所属的 field_id（trigger_field 类型时使用） */
  trigger_field_id?: string;
}

/** 循环节点配置 */
export interface LoopNodeConfig {
  /** 循环方式：仅支持 sequential（依次处理每条数据） */
  loop_mode: 'sequential';
  /** 数据源配置 */
  data_source: LoopDataSource;
  /** 最大循环次数（1-1000，默认 100） */
  max_iterations: number;
  /** 错误处理：skip（跳过当次继续）或 terminate（终止流程） */
  error_handling: 'skip' | 'terminate';
  /** 空结果处理：skip（跳过循环）或 error（报错） */
  empty_result_action: 'skip' | 'error';
  /** 循环体子节点列表（结构同主节点列表） */
  loop_body_nodes: WorkflowNode[];
}

/** 脚本节点分支路由配置 */
export interface ScriptBranch {
  /** 分支标签（脚本中通过 set_branch(label) 引用） */
  label: string;
  /** 目标节点 ID */
  target_node_id: string;
}

/** 脚本节点配置 */
export interface ScriptNodeConfig {
  /** 脚本语言：固定为 python */
  language: 'python';
  /** 脚本源代码（≤50000 字符） */
  script_source: string;
  /** 执行超时（秒，1-300，默认 30） */
  timeout: number;
  /** 结果变量名（默认 script_result，下游可通过 {{<result_variable>.field}} 引用） */
  result_variable: string;
  /** 输入来源节点 ID（缺省取最近一个前驱节点的输出） */
  input_node_id?: string | null;
  /** 分支路由配置 */
  branches: ScriptBranch[];
}

export type TriggerType =
  | 'record_created'
  | 'record_updated'
  | 'field_changed'
  | 'manual'
  | 'specified_time'
  | 'record_time_reached';

export type ScheduleRepeatType =
  | 'no_repeat'
  | 'daily'
  | 'weekly'
  | 'monthly'
  | 'yearly'
  | 'weekdays'
  | 'custom';

export type ScheduleCustomUnit = 'day' | 'week' | 'month' | 'year';

export type ScheduleEndType = 'never' | 'end_date';

export interface ScheduleConfig {
  start_date: string;
  start_time: string;
  repeat_type: ScheduleRepeatType;
  custom_interval: number;
  custom_unit: ScheduleCustomUnit;
  end_type: ScheduleEndType;
  end_date?: string;
  timezone?: string;
}

export interface ConditionItem {
  field_id: string;
  operator: import('@/types/filters').FilterOperatorValue;
  value?: unknown;
}

export interface ConditionBranch {
  id: string;
  name: string;
  conditions: ConditionItem[];
  conjunction: 'and' | 'or';
  target_node_id?: string;
  is_default?: boolean;
}

export interface ConditionNodeConfig {
  branches: ConditionBranch[];
}

export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'archived';

export type InstanceStatus =
  | 'running'
  | 'completed'
  | 'rejected'
  | 'cancelled'
  | 'error';

export type WebhookMethod = 'GET' | 'POST' | 'PUT';

export type WebhookDeliveryStatus = 'pending' | 'success' | 'failed';

export interface Workflow {
  id: string;
  base_id: string;
  table_id?: string | null;
  name: string;
  description?: string | null;
  status: WorkflowStatus;
  current_version: number;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface WorkflowVersion {
  id: string;
  workflow_id: string;
  version_number: number;
  config_snapshot: Record<string, unknown>;
  created_by?: string | null;
  created_by_name?: string | null;
  created_at: string;
}

export interface WorkflowNode {
  id: string;
  workflow_id: string;
  node_type: WorkflowNodeType;
  name: string;
  config: Record<string, unknown>;
  order: number;
  next_nodes: string[];
  ui_layout?: { x: number; y: number };
}

export interface WorkflowTrigger {
  id: string;
  workflow_id: string;
  trigger_type: TriggerType;
  filter_config: Record<string, unknown>;
  field_ids: string[];
}

export interface WorkflowInstance {
  id: string;
  workflow_id: string;
  version_number: number;
  trigger_type: TriggerType;
  trigger_record_id?: string | null;
  status: InstanceStatus;
  context: Record<string, unknown>;
  started_at: string;
  completed_at?: string | null;
}

export interface WorkflowExecutionLog {
  id: string;
  instance_id: string;
  node_id?: string | null;
  node_name?: string | null;
  node_type: WorkflowNodeType;
  status: string;
  input_context: Record<string, unknown>;
  output_result: Record<string, unknown>;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface WebhookConfig {
  id: string;
  base_id: string;
  name: string;
  url: string;
  method: WebhookMethod;
  headers: Record<string, unknown>;
  body_template?: string | null;
  secret?: string | null;
  retry_policy: Record<string, unknown>;
  is_active: boolean;
  created_by?: string | null;
  created_at: string;
}

export interface WebhookDeliveryLog {
  id: string;
  webhook_config_id: string;
  instance_id?: string | null;
  payload?: string | null;
  status: WebhookDeliveryStatus;
  response_status?: number | null;
  response_body?: string | null;
  retry_count: number;
  error_message?: string | null;
  next_retry_at?: string | null;
  delivered_at?: string | null;
  created_at: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description?: string | null;
  category?: string | null;
  config_snapshot: Record<string, unknown>;
  is_system: boolean;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}
