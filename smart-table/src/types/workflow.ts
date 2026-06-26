/**
 * 工作流类型定义
 * 与后端 Workflow / Approval / Webhook / Template 模型保持一致
 */

export type WorkflowNodeType =
  | 'trigger'
  | 'approval'
  | 'action'
  | 'condition'
  | 'update_record'
  | 'create_record'
  | 'send_email'
  | 'webhook';

export type TriggerType =
  | 'record_created'
  | 'record_updated'
  | 'field_changed'
  | 'manual';

export type ApprovalMode = 'any' | 'all' | 'serial';

export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'archived';

export type InstanceStatus =
  | 'running'
  | 'completed'
  | 'rejected'
  | 'cancelled'
  | 'error';

export type TaskStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'transferred'
  | 'expired';

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

export interface WorkflowTask {
  id: string;
  instance_id: string;
  node_id?: string | null;
  assignee_id?: string | null;
  status: TaskStatus;
  comment?: string | null;
  acted_at?: string | null;
  transferred_from_id?: string | null;
}

export interface WorkflowExecutionLog {
  id: string;
  instance_id: string;
  node_id?: string | null;
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
