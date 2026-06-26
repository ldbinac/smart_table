/**
 * 工作流 API 服务
 * 封装工作流、审批、Webhook 与模板的 HTTP 调用
 */
import { apiClient } from '@/api/client';
import type {
  Workflow,
  WorkflowInstance,
  WorkflowTask,
  WebhookConfig,
  WebhookDeliveryLog,
  WorkflowTemplate,
  WorkflowVersion,
} from '@/types';
import type { PaginatedData } from '@/api/types';

type PaginationMeta = {
  meta?: {
    pagination?: PaginatedData<unknown> & { items?: unknown[] };
  };
};

type ListResponse<T> = { data?: T[] } & PaginationMeta;

const extractItems = <T>(response: ListResponse<T>): T[] => {
  const res = response as ListResponse<T>;
  if (res.meta?.pagination?.items) {
    return res.meta.pagination.items as T[];
  }
  return (res.data || []) as T[];
};

// ==================== 工作流 CRUD ====================

export const listWorkflows = async (
  baseId: string,
  params?: object,
): Promise<Workflow[]> => {
  return apiClient.get<Workflow[]>(`/bases/${baseId}/workflows`, params as Record<string, unknown>);
};

export const getWorkflow = async (workflowId: string): Promise<Workflow> => {
  return apiClient.get<Workflow>(`/workflows/${workflowId}`);
};

export const createWorkflow = async (
  baseId: string,
  data: object,
): Promise<Workflow> => {
  return apiClient.post<Workflow>(`/bases/${baseId}/workflows`, data);
};

export const updateWorkflow = async (
  workflowId: string,
  data: object,
): Promise<Workflow> => {
  return apiClient.put<Workflow>(`/workflows/${workflowId}`, data);
};

export const deleteWorkflow = async (workflowId: string): Promise<void> => {
  await apiClient.delete<void>(`/workflows/${workflowId}`);
};

// ==================== 工作流操作 ====================

export const publishWorkflow = async (workflowId: string): Promise<void> => {
  await apiClient.post<void>(`/workflows/${workflowId}/publish`);
};

export const pauseWorkflow = async (workflowId: string): Promise<void> => {
  await apiClient.post<void>(`/workflows/${workflowId}/pause`);
};

export const resumeWorkflow = async (workflowId: string): Promise<void> => {
  await apiClient.post<void>(`/workflows/${workflowId}/resume`);
};

export const cloneWorkflow = async (workflowId: string): Promise<Workflow> => {
  return apiClient.post<Workflow>(`/workflows/${workflowId}/clone`);
};

export const listWorkflowVersions = async (
  workflowId: string,
): Promise<WorkflowVersion[]> => {
  return apiClient.get<WorkflowVersion[]>(`/workflows/${workflowId}/versions`);
};

// ==================== 执行实例 ====================

export const listInstances = async (
  workflowId: string,
  params?: object,
): Promise<WorkflowInstance[]> => {
  const response = await apiClient.get<ListResponse<WorkflowInstance>>(
    `/workflows/${workflowId}/instances`,
    params as Record<string, unknown>,
  );
  return extractItems(response);
};

export const getInstance = async (
  workflowId: string,
  instanceId: string,
): Promise<WorkflowInstance> => {
  return apiClient.get<WorkflowInstance>(
    `/workflows/${workflowId}/instances/${instanceId}`,
  );
};

export const triggerWorkflow = async (
  tableId: string,
  recordId: string,
  data: object,
): Promise<void> => {
  await apiClient.post<void>(`/tables/${tableId}/records/${recordId}/trigger`, data);
};

// ==================== 审批 ====================

export const listApprovals = async (
  baseId: string,
  params?: object,
): Promise<WorkflowTask[]> => {
  return apiClient.get<WorkflowTask[]>(
    `/bases/${baseId}/approvals`,
    params as Record<string, unknown>,
  );
};

export const getApproval = async (taskId: string): Promise<WorkflowTask> => {
  return apiClient.get<WorkflowTask>(`/approvals/${taskId}`);
};

export const approveTask = async (
  taskId: string,
  comment?: string,
): Promise<void> => {
  await apiClient.post<void>(`/approvals/${taskId}/approve`, { comment });
};

export const rejectTask = async (
  taskId: string,
  comment?: string,
): Promise<void> => {
  await apiClient.post<void>(`/approvals/${taskId}/reject`, { comment });
};

export const transferTask = async (
  taskId: string,
  newAssigneeId: string,
  comment?: string,
): Promise<void> => {
  await apiClient.post<void>(`/approvals/${taskId}/transfer`, {
    new_assignee_id: newAssigneeId,
    comment,
  });
};

export const getRecordApprovalHistory = async (
  recordId: string,
): Promise<WorkflowTask[]> => {
  const response = await apiClient.get<
    { data?: Array<{ tasks?: WorkflowTask[] }> } & PaginationMeta
  >(`/records/${recordId}/approval-history`);

  const res = response as { data?: Array<{ tasks?: WorkflowTask[] }> };
  const groups = res.data || [];
  return groups.flatMap((group) => group.tasks || []);
};

// ==================== Webhook ====================

export const listWebhooks = async (
  baseId: string,
): Promise<WebhookConfig[]> => {
  return apiClient.get<WebhookConfig[]>(`/bases/${baseId}/webhooks`);
};

export const createWebhook = async (
  baseId: string,
  data: object,
): Promise<WebhookConfig> => {
  return apiClient.post<WebhookConfig>(`/bases/${baseId}/webhooks`, data);
};

export const updateWebhook = async (
  webhookId: string,
  data: object,
): Promise<WebhookConfig> => {
  return apiClient.put<WebhookConfig>(`/webhooks/${webhookId}`, data);
};

export const deleteWebhook = async (webhookId: string): Promise<void> => {
  await apiClient.delete<void>(`/webhooks/${webhookId}`);
};

export const testWebhook = async (webhookId: string): Promise<object> => {
  return apiClient.post<object>(`/webhooks/${webhookId}/test`);
};

export const listDeliveries = async (
  webhookId: string,
  params?: object,
): Promise<WebhookDeliveryLog[]> => {
  const response = await apiClient.get<ListResponse<WebhookDeliveryLog>>(
    `/webhooks/${webhookId}/deliveries`,
    params as Record<string, unknown>,
  );
  return extractItems(response);
};

// ==================== 模板 ====================

export const listTemplates = async (
  params?: object,
): Promise<WorkflowTemplate[]> => {
  const response = await apiClient.get<ListResponse<WorkflowTemplate>>(
    '/workflow-templates',
    params as Record<string, unknown>,
  );
  return extractItems(response);
};

export const saveAsTemplate = async (
  workflowId: string,
  data: object,
): Promise<WorkflowTemplate> => {
  return apiClient.post<WorkflowTemplate>('/workflow-templates', {
    workflow_id: workflowId,
    ...data,
  });
};

export const instantiateTemplate = async (
  templateId: string,
  tableId: string,
): Promise<Workflow> => {
  const result = await apiClient.post<{ workflow_id?: string }>(
    `/workflow-templates/${templateId}/instantiate`,
    { table_id: tableId },
  );
  return getWorkflow(result.workflow_id || '');
};

export const workflowApiService = {
  listWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  publishWorkflow,
  pauseWorkflow,
  resumeWorkflow,
  cloneWorkflow,
  listWorkflowVersions,
  listInstances,
  getInstance,
  triggerWorkflow,
  listApprovals,
  getApproval,
  approveTask,
  rejectTask,
  transferTask,
  getRecordApprovalHistory,
  listWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  testWebhook,
  listDeliveries,
  listTemplates,
  saveAsTemplate,
  instantiateTemplate,
};

export default workflowApiService;
