/**
 * workflowApiService 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { workflowApiService } from '../workflowApiService';
import { apiClient } from '@/api/client';

vi.mock('@/api/client');

describe('workflowApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockWorkflow = {
    id: 'wf-1',
    base_id: 'base-1',
    table_id: 'table-1',
    name: '测试工作流',
    status: 'draft' as const,
    current_version: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_deleted: false,
  };

  const mockInstance = {
    id: 'inst-1',
    workflow_id: 'wf-1',
    version_number: 1,
    trigger_type: 'record_created' as const,
    status: 'running' as const,
    context: {},
    started_at: new Date().toISOString(),
  };

  const mockTask = {
    id: 'task-1',
    instance_id: 'inst-1',
    status: 'pending' as const,
  };

  const mockWebhook = {
    id: 'wh-1',
    base_id: 'base-1',
    name: '测试 Webhook',
    url: 'https://example.com/webhook',
    method: 'POST' as const,
    headers: {},
    retry_policy: {},
    is_active: true,
    created_at: new Date().toISOString(),
  };

  const mockTemplate = {
    id: 'tpl-1',
    name: '测试模板',
    config_snapshot: {},
    is_system: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  describe('工作流 CRUD', () => {
    it('应该获取工作流列表', async () => {
      (apiClient.get as any).mockResolvedValue([mockWorkflow]);
      const result = await workflowApiService.listWorkflows('base-1', { status: 'active' });
      expect(apiClient.get).toHaveBeenCalledWith('/bases/base-1/workflows', { status: 'active' });
      expect(result).toEqual([mockWorkflow]);
    });

    it('应该获取单个工作流', async () => {
      (apiClient.get as any).mockResolvedValue(mockWorkflow);
      const result = await workflowApiService.getWorkflow('wf-1');
      expect(apiClient.get).toHaveBeenCalledWith('/workflows/wf-1');
      expect(result).toEqual(mockWorkflow);
    });

    it('应该创建工作流', async () => {
      (apiClient.post as any).mockResolvedValue(mockWorkflow);
      const data = { name: '测试工作流', table_id: 'table-1' };
      const result = await workflowApiService.createWorkflow('base-1', data);
      expect(apiClient.post).toHaveBeenCalledWith('/bases/base-1/workflows', data);
      expect(result).toEqual(mockWorkflow);
    });

    it('应该更新工作流', async () => {
      const updated = { ...mockWorkflow, name: '已更新' };
      (apiClient.put as any).mockResolvedValue(updated);
      const result = await workflowApiService.updateWorkflow('wf-1', { name: '已更新' });
      expect(apiClient.put).toHaveBeenCalledWith('/workflows/wf-1', { name: '已更新' });
      expect(result).toEqual(updated);
    });

    it('应该删除工作流', async () => {
      (apiClient.delete as any).mockResolvedValue(undefined);
      await workflowApiService.deleteWorkflow('wf-1');
      expect(apiClient.delete).toHaveBeenCalledWith('/workflows/wf-1');
    });
  });

  describe('工作流操作', () => {
    it.each([
      ['publishWorkflow', '/workflows/wf-1/publish'],
      ['pauseWorkflow', '/workflows/wf-1/pause'],
      ['resumeWorkflow', '/workflows/wf-1/resume'],
    ] as const)('%s 应该调用正确端点', async (method, url) => {
      (apiClient.post as any).mockResolvedValue(undefined);
      await (workflowApiService as any)[method]('wf-1');
      expect(apiClient.post).toHaveBeenCalledWith(url);
    });
  });

  describe('执行实例', () => {
    it('应该获取实例列表（支持分页结构）', async () => {
      (apiClient.get as any).mockResolvedValue({
        data: [mockInstance],
        meta: { pagination: { items: [mockInstance], total: 1 } },
      });
      const result = await workflowApiService.listInstances('wf-1', { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith('/workflows/wf-1/instances', { page: 1 });
      expect(result).toEqual([mockInstance]);
    });

    it('应该获取单个实例', async () => {
      (apiClient.get as any).mockResolvedValue(mockInstance);
      const result = await workflowApiService.getInstance('wf-1', 'inst-1');
      expect(apiClient.get).toHaveBeenCalledWith('/workflows/wf-1/instances/inst-1');
      expect(result).toEqual(mockInstance);
    });

    it('应该触发工作流', async () => {
      (apiClient.post as any).mockResolvedValue(undefined);
      await workflowApiService.triggerWorkflow('table-1', 'record-1', { workflow_id: 'wf-1' });
      expect(apiClient.post).toHaveBeenCalledWith('/tables/table-1/records/record-1/trigger', {
        workflow_id: 'wf-1',
      });
    });
  });

  describe('审批任务', () => {
    it('应该获取审批列表', async () => {
      (apiClient.get as any).mockResolvedValue([mockTask]);
      const result = await workflowApiService.listApprovals('base-1', { status: 'pending' });
      expect(apiClient.get).toHaveBeenCalledWith('/bases/base-1/approvals', { status: 'pending' });
      expect(result).toEqual([mockTask]);
    });

    it('应该获取单个审批', async () => {
      (apiClient.get as any).mockResolvedValue(mockTask);
      const result = await workflowApiService.getApproval('task-1');
      expect(apiClient.get).toHaveBeenCalledWith('/approvals/task-1');
      expect(result).toEqual(mockTask);
    });

    it.each([
      ['approveTask', '/approvals/task-1/approve', '同意', { comment: '同意' }],
      ['rejectTask', '/approvals/task-1/reject', '拒绝', { comment: '拒绝' }],
    ] as const)('%s 应该提交正确参数', async (method, url, comment, body) => {
      (apiClient.post as any).mockResolvedValue(undefined);
      await (workflowApiService as any)[method]('task-1', comment);
      expect(apiClient.post).toHaveBeenCalledWith(url, body);
    });

    it('应该转交审批任务', async () => {
      (apiClient.post as any).mockResolvedValue(undefined);
      await workflowApiService.transferTask('task-1', 'user-2', '转交');
      expect(apiClient.post).toHaveBeenCalledWith('/approvals/task-1/transfer', {
        new_assignee_id: 'user-2',
        comment: '转交',
      });
    });

    it('应该获取记录审批历史', async () => {
      (apiClient.get as any).mockResolvedValue({
        data: [{ tasks: [mockTask] }],
      });
      const result = await workflowApiService.getRecordApprovalHistory('record-1');
      expect(apiClient.get).toHaveBeenCalledWith('/records/record-1/approval-history');
      expect(result).toEqual([mockTask]);
    });
  });

  describe('Webhook', () => {
    it('应该获取 Webhook 列表', async () => {
      (apiClient.get as any).mockResolvedValue([mockWebhook]);
      const result = await workflowApiService.listWebhooks('base-1');
      expect(apiClient.get).toHaveBeenCalledWith('/bases/base-1/webhooks');
      expect(result).toEqual([mockWebhook]);
    });

    it('应该创建 Webhook', async () => {
      (apiClient.post as any).mockResolvedValue(mockWebhook);
      const data = { name: '测试 Webhook', url: 'https://example.com/webhook' };
      const result = await workflowApiService.createWebhook('base-1', data);
      expect(apiClient.post).toHaveBeenCalledWith('/bases/base-1/webhooks', data);
      expect(result).toEqual(mockWebhook);
    });

    it('应该更新 Webhook', async () => {
      const updated = { ...mockWebhook, name: '已更新' };
      (apiClient.put as any).mockResolvedValue(updated);
      const result = await workflowApiService.updateWebhook('wh-1', { name: '已更新' });
      expect(apiClient.put).toHaveBeenCalledWith('/webhooks/wh-1', { name: '已更新' });
      expect(result).toEqual(updated);
    });

    it('应该删除 Webhook', async () => {
      (apiClient.delete as any).mockResolvedValue(undefined);
      await workflowApiService.deleteWebhook('wh-1');
      expect(apiClient.delete).toHaveBeenCalledWith('/webhooks/wh-1');
    });

    it('应该测试 Webhook', async () => {
      (apiClient.post as any).mockResolvedValue({ success: true });
      const result = await workflowApiService.testWebhook('wh-1');
      expect(apiClient.post).toHaveBeenCalledWith('/webhooks/wh-1/test');
      expect(result).toEqual({ success: true });
    });

    it('应该获取 Webhook 投递日志', async () => {
      const mockDelivery = {
        id: 'dlv-1',
        webhook_config_id: 'wh-1',
        status: 'success' as const,
        retry_count: 0,
        created_at: new Date().toISOString(),
      };
      (apiClient.get as any).mockResolvedValue({
        data: [mockDelivery],
        meta: { pagination: { items: [mockDelivery], total: 1 } },
      });
      const result = await workflowApiService.listDeliveries('wh-1', { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith('/webhooks/wh-1/deliveries', { page: 1 });
      expect(result).toEqual([mockDelivery]);
    });
  });

  describe('模板', () => {
    it('应该获取模板列表', async () => {
      (apiClient.get as any).mockResolvedValue({
        data: [mockTemplate],
        meta: { pagination: { items: [mockTemplate], total: 1 } },
      });
      const result = await workflowApiService.listTemplates({ category: 'approval' });
      expect(apiClient.get).toHaveBeenCalledWith('/workflow-templates', { category: 'approval' });
      expect(result).toEqual([mockTemplate]);
    });

    it('应该保存为模板', async () => {
      (apiClient.post as any).mockResolvedValue(mockTemplate);
      const data = { name: '测试模板' };
      const result = await workflowApiService.saveAsTemplate('wf-1', data);
      expect(apiClient.post).toHaveBeenCalledWith('/workflow-templates', {
        workflow_id: 'wf-1',
        ...data,
      });
      expect(result).toEqual(mockTemplate);
    });

    it('应该实例化模板并拉取工作流详情', async () => {
      (apiClient.post as any).mockResolvedValue({ workflow_id: 'wf-1' });
      (apiClient.get as any).mockResolvedValue(mockWorkflow);
      const result = await workflowApiService.instantiateTemplate('tpl-1', 'table-1');
      expect(apiClient.post).toHaveBeenCalledWith('/workflow-templates/tpl-1/instantiate', {
        table_id: 'table-1',
      });
      expect(apiClient.get).toHaveBeenCalledWith('/workflows/wf-1');
      expect(result).toEqual(mockWorkflow);
    });
  });
});
