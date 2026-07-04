import type { WorkflowTask } from "@/types/workflow";

export interface ApprovalUser {
  id: string;
  name: string;
  avatar?: string | null;
}

export interface ApprovalRecord {
  id: string;
  title?: string;
  values?: Record<string, unknown>;
  created_by?: string | ApprovalUser | null;
  created_at?: string;
  table_id?: string | null;
}

export interface ApprovalNode {
  id: string;
  name: string;
}

export interface ApprovalWorkflow {
  id: string;
  name: string;
  table_id?: string | null;
}

export interface ApprovalInstance {
  id: string;
  started_at?: string;
  trigger_record_id?: string | null;
}

export interface ApprovalTask extends WorkflowTask {
  record?: ApprovalRecord | null;
  node?: ApprovalNode | null;
  workflow?: ApprovalWorkflow | null;
  instance?: ApprovalInstance | null;
  assignee?: ApprovalUser | null;
  actor?: ApprovalUser | null;
}
