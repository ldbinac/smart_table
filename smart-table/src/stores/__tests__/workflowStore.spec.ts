/**
 * workflowStore 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useWorkflowStore } from '../workflowStore';
import { workflowApiService } from '@/services/api/workflowApiService';

vi.mock('@/services/api/workflowApiService');
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus');
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
    },
  };
});

describe('workflowStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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
    assignee_id: 'user-1',
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

  it('应该使用正确的默认状态初始化', () => {
    const store = useWorkflowStore();
    expect(store.workflows).toEqual([]);
    expect(store.currentWorkflow).toBeNull();
    expect(store.instances).toEqual([]);
    expect(store.pendingApprovals).toEqual([]);
    expect(store.approvalHistory).toEqual([]);
    expect(store.webhooks).toEqual([]);
    expect(store.templates).toEqual([]);
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
    expect(store.pendingApprovalCount).toBe(0);
    expect(store.activeWorkflowCount).toBe(0);
  });

  describe('工作流操作', () => {
    it('应该加载工作流列表', async () => {
      const store = useWorkflowStore();
      (workflowApiService.listWorkflows as any).mockResolvedValue([mockWorkflow]);
      const result = await store.loadWorkflows('base-1', { status: 'active' });
      expect(workflowApiService.listWorkflows).toHaveBeenCalledWith('base-1', { status: 'active' });
      expect(store.workflows).toEqual([mockWorkflow]);
      expect(result).toEqual([mockWorkflow]);
    });

    it('应该加载单个工作流', async () => {
      const store = useWorkflowStore();
      (workflowApiService.getWorkflow as any).mockResolvedValue(mockWorkflow);
      const result = await store.loadWorkflow('wf-1');
      expect(workflowApiService.getWorkflow).toHaveBeenCalledWith('wf-1');
      expect(store.currentWorkflow).toEqual(mockWorkflow);
      expect(result).toEqual(mockWorkflow);
    });

    it('应该创建工作流并更新状态', async () => {
      const store = useWorkflowStore();
      (workflowApiService.createWorkflow as any).mockResolvedValue(mockWorkflow);
      const data = { name: '测试工作流', table_id: 'table-1' };
      const result = await store.createWorkflow('base-1', data);
      expect(workflowApiService.createWorkflow).toHaveBeenCalledWith('base-1', data);
      expect(store.workflows).toContainEqual(mockWorkflow);
      expect(store.currentWorkflow).toEqual(mockWorkflow);
      expect(result).toEqual(mockWorkflow);
    });

    it('应该更新工作流列表和当前工作流', async () => {
      const store = useWorkflowStore();
      store.workflows = [mockWorkflow];
      store.currentWorkflow = mockWorkflow;
      const updated = { ...mockWorkflow, name: '已更新' };
      (workflowApiService.updateWorkflow as any).mockResolvedValue(updated);
      const result = await store.updateWorkflow('wf-1', { name: '已更新' });
      expect(workflowApiService.updateWorkflow).toHaveBeenCalledWith('wf-1', { name: '已更新' });
      expect(store.workflows[0]).toEqual(updated);
      expect(store.currentWorkflow).toEqual(updated);
      expect(result).toEqual(updated);
    });

    it('应该删除工作流并清空当前工作流', async () => {
      const store = useWorkflowStore();
      store.workflows = [mockWorkflow];
      store.currentWorkflow = mockWorkflow;
      (workflowApiService.deleteWorkflow as any).mockResolvedValue(undefined);
      await store.deleteWorkflow('wf-1');
      expect(workflowApiService.deleteWorkflow).toHaveBeenCalledWith('wf-1');
      expect(store.workflows).toEqual([]);
      expect(store.currentWorkflow).toBeNull();
    });

    it.each([
      ['publishWorkflow', 'active'],
      ['pauseWorkflow', 'paused'],
      ['resumeWorkflow', 'active'],
    ] as const)('%s 应该更新工作流状态', async (method, expectedStatus) => {
      const store = useWorkflowStore();
      store.workflows = [mockWorkflow];
      store.currentWorkflow = mockWorkflow;
      (workflowApiService[method] as any).mockResolvedValue(undefined);
      await (store as any)[method]('wf-1');
      expect(workflowApiService[method]).toHaveBeenCalledWith('wf-1');
      expect(store.workflows[0].status).toBe(expectedStatus);
      expect(store.currentWorkflow?.status).toBe(expectedStatus);
    });

    it('失败时应该设置错误状态并抛出异常', async () => {
      const store = useWorkflowStore();
      const error = new Error('网络错误');
      (workflowApiService.listWorkflows as any).mockRejectedValue(error);
      await expect(store.loadWorkflows('base-1')).rejects.toThrow('网络错误');
      expect(store.error).toBe('网络错误');
      expect(store.loading).toBe(false);
    });
  });

  describe('实例操作', () => {
    it('应该加载实例列表', async () => {
      const store = useWorkflowStore();
      (workflowApiService.listInstances as any).mockResolvedValue([mockInstance]);
      const result = await store.loadInstances('wf-1');
      expect(workflowApiService.listInstances).toHaveBeenCalledWith('wf-1');
      expect(store.instances).toEqual([mockInstance]);
      expect(result).toEqual([mockInstance]);
    });

    it('应该加载单个实例', async () => {
      const store = useWorkflowStore();
      (workflowApiService.getInstance as any).mockResolvedValue(mockInstance);
      const result = await store.loadInstance('wf-1', 'inst-1');
      expect(workflowApiService.getInstance).toHaveBeenCalledWith('wf-1', 'inst-1');
      expect(store.currentInstance).toEqual(mockInstance);
      expect(result).toEqual(mockInstance);
    });

    it('应该触发工作流', async () => {
      const store = useWorkflowStore();
      (workflowApiService.triggerWorkflow as any).mockResolvedValue(undefined);
      await store.triggerWorkflow('table-1', 'record-1', 'wf-1');
      expect(workflowApiService.triggerWorkflow).toHaveBeenCalledWith('table-1', 'record-1', {
        workflow_id: 'wf-1',
      });
    });
  });

  describe('审批操作', () => {
    it('应该加载审批列表并分类', async () => {
      const store = useWorkflowStore();
      const approvedTask = { ...mockTask, id: 'task-2', status: 'approved' as const };
      (workflowApiService.listApprovals as any).mockResolvedValue([mockTask, approvedTask]);
      const result = await store.loadApprovals('base-1');
      expect(workflowApiService.listApprovals).toHaveBeenCalledWith('base-1', undefined);
      expect(store.pendingApprovals).toEqual([mockTask]);
      expect(store.approvalHistory).toEqual([approvedTask]);
      expect(result).toEqual([mockTask, approvedTask]);
    });

    it.each([
      ['approveTask', 'approved'],
      ['rejectTask', 'rejected'],
    ] as const)('%s 应该移动任务到历史记录', async (method, expectedStatus) => {
      const store = useWorkflowStore();
      store.pendingApprovals = [mockTask];
      (workflowApiService[method] as any).mockResolvedValue(undefined);
      await (store as any)[method]('task-1', '同意');
      expect(workflowApiService[method]).toHaveBeenCalledWith('task-1', '同意');
      expect(store.pendingApprovals).toEqual([]);
      expect(store.approvalHistory[0].status).toBe(expectedStatus);
      expect(store.approvalHistory[0].comment).toBe('同意');
    });

    it('应该转交审批任务', async () => {
      const store = useWorkflowStore();
      store.pendingApprovals = [mockTask];
      (workflowApiService.transferTask as any).mockResolvedValue(undefined);
      await store.transferTask('task-1', 'user-2', '转交');
      expect(workflowApiService.transferTask).toHaveBeenCalledWith('task-1', 'user-2', '转交');
      expect(store.pendingApprovals).toEqual([]);
      expect(store.approvalHistory[0].status).toBe('transferred');
      expect(store.approvalHistory[0].assignee_id).toBe('user-2');
      expect(store.approvalHistory[0].transferred_from_id).toBe('user-1');
    });
  });

  describe('Webhook 操作', () => {
    it('应该加载 Webhook 列表', async () => {
      const store = useWorkflowStore();
      (workflowApiService.listWebhooks as any).mockResolvedValue([mockWebhook]);
      const result = await store.loadWebhooks('base-1');
      expect(workflowApiService.listWebhooks).toHaveBeenCalledWith('base-1');
      expect(store.webhooks).toEqual([mockWebhook]);
      expect(result).toEqual([mockWebhook]);
    });

    it('应该创建 Webhook', async () => {
      const store = useWorkflowStore();
      (workflowApiService.createWebhook as any).mockResolvedValue(mockWebhook);
      const data = { name: '测试 Webhook', url: 'https://example.com/webhook' };
      const result = await store.createWebhook('base-1', data);
      expect(workflowApiService.createWebhook).toHaveBeenCalledWith('base-1', data);
      expect(store.webhooks).toContainEqual(mockWebhook);
      expect(result).toEqual(mockWebhook);
    });

    it('应该更新 Webhook', async () => {
      const store = useWorkflowStore();
      store.webhooks = [mockWebhook];
      const updated = { ...mockWebhook, name: '已更新' };
      (workflowApiService.updateWebhook as any).mockResolvedValue(updated);
      const result = await store.updateWebhook('wh-1', { name: '已更新' });
      expect(workflowApiService.updateWebhook).toHaveBeenCalledWith('wh-1', { name: '已更新' });
      expect(store.webhooks[0]).toEqual(updated);
      expect(result).toEqual(updated);
    });

    it('应该删除 Webhook', async () => {
      const store = useWorkflowStore();
      store.webhooks = [mockWebhook];
      (workflowApiService.deleteWebhook as any).mockResolvedValue(undefined);
      await store.deleteWebhook('wh-1');
      expect(workflowApiService.deleteWebhook).toHaveBeenCalledWith('wh-1');
      expect(store.webhooks).toEqual([]);
    });

    it('应该测试 Webhook', async () => {
      const store = useWorkflowStore();
      (workflowApiService.testWebhook as any).mockResolvedValue({ success: true });
      const result = await store.testWebhook('wh-1');
      expect(workflowApiService.testWebhook).toHaveBeenCalledWith('wh-1');
      expect(result).toEqual({ success: true });
    });
  });

  describe('模板操作', () => {
    it('应该加载模板列表', async () => {
      const store = useWorkflowStore();
      (workflowApiService.listTemplates as any).mockResolvedValue([mockTemplate]);
      const result = await store.loadTemplates({ category: 'approval' });
      expect(workflowApiService.listTemplates).toHaveBeenCalledWith({ category: 'approval' });
      expect(store.templates).toEqual([mockTemplate]);
      expect(result).toEqual([mockTemplate]);
    });

    it('应该保存为模板', async () => {
      const store = useWorkflowStore();
      (workflowApiService.saveAsTemplate as any).mockResolvedValue(mockTemplate);
      const data = { name: '测试模板' };
      const result = await store.saveAsTemplate('wf-1', data);
      expect(workflowApiService.saveAsTemplate).toHaveBeenCalledWith('wf-1', data);
      expect(store.templates).toContainEqual(mockTemplate);
      expect(result).toEqual(mockTemplate);
    });

    it('应该实例化模板', async () => {
      const store = useWorkflowStore();
      (workflowApiService.instantiateTemplate as any).mockResolvedValue(mockWorkflow);
      const result = await store.instantiateTemplate('tpl-1', 'table-1');
      expect(workflowApiService.instantiateTemplate).toHaveBeenCalledWith('tpl-1', 'table-1');
      expect(store.workflows).toContainEqual(mockWorkflow);
      expect(store.currentWorkflow).toEqual(mockWorkflow);
      expect(result).toEqual(mockWorkflow);
    });
  });

  it('reset 应该清空所有状态', () => {
    const store = useWorkflowStore();
    store.workflows = [mockWorkflow];
    store.currentWorkflow = mockWorkflow;
    store.instances = [mockInstance];
    store.pendingApprovals = [mockTask];
    store.webhooks = [mockWebhook];
    store.templates = [mockTemplate];
    store.error = 'error';
    store.$reset();
    expect(store.workflows).toEqual([]);
    expect(store.currentWorkflow).toBeNull();
    expect(store.instances).toEqual([]);
    expect(store.pendingApprovals).toEqual([]);
    expect(store.approvalHistory).toEqual([]);
    expect(store.webhooks).toEqual([]);
    expect(store.templates).toEqual([]);
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
  });
});
