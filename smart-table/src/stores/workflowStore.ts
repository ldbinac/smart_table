/**
 * 工作流状态管理
 * 管理工作流、审批任务、Webhook 与模板的交互状态
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import { workflowApiService } from "@/services/api/workflowApiService";
import type {
  Workflow,
  WorkflowInstance,
  WorkflowTask,
  WebhookConfig,
  WorkflowTemplate,
} from "@/types/workflow";

export const useWorkflowStore = defineStore("workflow", () => {
  // ==================== State ====================
  const workflows = ref<Workflow[]>([]);
  const currentWorkflow = ref<Workflow | null>(null);
  const instances = ref<WorkflowInstance[]>([]);
  const currentInstance = ref<WorkflowInstance | null>(null);
  const pendingApprovals = ref<WorkflowTask[]>([]);
  const approvalHistory = ref<WorkflowTask[]>([]);
  const webhooks = ref<WebhookConfig[]>([]);
  const templates = ref<WorkflowTemplate[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // ==================== Getters ====================
  const pendingApprovalCount = computed(() => pendingApprovals.value.length);

  const activeWorkflowCount = computed(
    () => workflows.value.filter((w) => w.status === "active").length
  );

  const getWorkflowById = (id: string): Workflow | undefined => {
    return workflows.value.find((w) => w.id === id);
  };

  // ==================== Helpers ====================
  function handleError(action: string, e: unknown): string {
    const msg = e instanceof Error ? e.message : `${action}失败`;
    error.value = msg;
    console.error(`[workflowStore] ${action} failed:`, e);
    ElMessage.error(msg);
    return msg;
  }

  function setLoading(value: boolean) {
    loading.value = value;
  }

  function clearError() {
    error.value = null;
  }

  // ==================== Workflow Actions ====================
  async function loadWorkflows(
    baseId: string,
    params?: object
  ): Promise<Workflow[]> {
    setLoading(true);
    clearError();
    try {
      const data = await workflowApiService.listWorkflows(baseId, params);
      workflows.value = data;
      return data;
    } catch (e: unknown) {
      handleError("loadWorkflows", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function loadWorkflow(workflowId: string): Promise<Workflow> {
    setLoading(true);
    clearError();
    try {
      const data = await workflowApiService.getWorkflow(workflowId);
      currentWorkflow.value = data;
      return data;
    } catch (e: unknown) {
      handleError("loadWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function createWorkflow(
    baseId: string,
    data: object
  ): Promise<Workflow> {
    setLoading(true);
    clearError();
    try {
      const created = await workflowApiService.createWorkflow(baseId, data);
      workflows.value.push(created);
      currentWorkflow.value = created;
      ElMessage.success("工作流创建成功");
      return created;
    } catch (e: unknown) {
      handleError("createWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function updateWorkflow(
    workflowId: string,
    data: object
  ): Promise<Workflow> {
    setLoading(true);
    clearError();
    try {
      const updated = await workflowApiService.updateWorkflow(workflowId, data);
      const idx = workflows.value.findIndex((w) => w.id === workflowId);
      if (idx !== -1) {
        workflows.value[idx] = updated;
      }
      if (currentWorkflow.value?.id === workflowId) {
        currentWorkflow.value = updated;
      }
      ElMessage.success("工作流更新成功");
      return updated;
    } catch (e: unknown) {
      handleError("updateWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function deleteWorkflow(workflowId: string): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.deleteWorkflow(workflowId);
      workflows.value = workflows.value.filter((w) => w.id !== workflowId);
      if (currentWorkflow.value?.id === workflowId) {
        currentWorkflow.value = null;
      }
      ElMessage.success("工作流删除成功");
    } catch (e: unknown) {
      handleError("deleteWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function publishWorkflow(workflowId: string): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.publishWorkflow(workflowId);
      const idx = workflows.value.findIndex((w) => w.id === workflowId);
      if (idx !== -1) {
        workflows.value[idx] = { ...workflows.value[idx], status: "active" };
      }
      if (currentWorkflow.value?.id === workflowId) {
        currentWorkflow.value = { ...currentWorkflow.value, status: "active" };
      }
      ElMessage.success("工作流已发布");
    } catch (e: unknown) {
      handleError("publishWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function pauseWorkflow(workflowId: string): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.pauseWorkflow(workflowId);
      const idx = workflows.value.findIndex((w) => w.id === workflowId);
      if (idx !== -1) {
        workflows.value[idx] = { ...workflows.value[idx], status: "paused" };
      }
      if (currentWorkflow.value?.id === workflowId) {
        currentWorkflow.value = { ...currentWorkflow.value, status: "paused" };
      }
      ElMessage.success("工作流已暂停");
    } catch (e: unknown) {
      handleError("pauseWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function resumeWorkflow(workflowId: string): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.resumeWorkflow(workflowId);
      const idx = workflows.value.findIndex((w) => w.id === workflowId);
      if (idx !== -1) {
        workflows.value[idx] = { ...workflows.value[idx], status: "active" };
      }
      if (currentWorkflow.value?.id === workflowId) {
        currentWorkflow.value = { ...currentWorkflow.value, status: "active" };
      }
      ElMessage.success("工作流已恢复");
    } catch (e: unknown) {
      handleError("resumeWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  // ==================== Instance Actions ====================
  async function loadInstances(workflowId: string): Promise<WorkflowInstance[]> {
    setLoading(true);
    clearError();
    try {
      const data = await workflowApiService.listInstances(workflowId);
      instances.value = data;
      return data;
    } catch (e: unknown) {
      handleError("loadInstances", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function loadInstance(
    workflowId: string,
    instanceId: string
  ): Promise<WorkflowInstance> {
    setLoading(true);
    clearError();
    try {
      const data = await workflowApiService.getInstance(workflowId, instanceId);
      currentInstance.value = data;
      return data;
    } catch (e: unknown) {
      handleError("loadInstance", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function triggerWorkflow(
    tableId: string,
    recordId: string,
    workflowId: string
  ): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.triggerWorkflow(tableId, recordId, {
        workflow_id: workflowId,
      });
      ElMessage.success("工作流触发成功");
    } catch (e: unknown) {
      handleError("triggerWorkflow", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  // ==================== Approval Actions ====================
  async function loadApprovals(
    baseId: string,
    params?: object
  ): Promise<WorkflowTask[]> {
    setLoading(true);
    clearError();
    try {
      const data = await workflowApiService.listApprovals(baseId, params);
      pendingApprovals.value = data.filter((task) => task.status === "pending");
      approvalHistory.value = data.filter((task) => task.status !== "pending");
      return data;
    } catch (e: unknown) {
      handleError("loadApprovals", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function approveTask(taskId: string, comment?: string): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.approveTask(taskId, comment);
      const pendingIdx = pendingApprovals.value.findIndex((t) => t.id === taskId);
      if (pendingIdx !== -1) {
        const task = pendingApprovals.value[pendingIdx];
        const updatedTask: WorkflowTask = {
          ...task,
          status: "approved",
          comment: comment || task.comment,
          acted_at: new Date().toISOString(),
        };
        pendingApprovals.value.splice(pendingIdx, 1);
        approvalHistory.value.unshift(updatedTask);
      }
      ElMessage.success("审批已通过");
    } catch (e: unknown) {
      handleError("approveTask", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function rejectTask(taskId: string, comment?: string): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.rejectTask(taskId, comment);
      const pendingIdx = pendingApprovals.value.findIndex((t) => t.id === taskId);
      if (pendingIdx !== -1) {
        const task = pendingApprovals.value[pendingIdx];
        const updatedTask: WorkflowTask = {
          ...task,
          status: "rejected",
          comment: comment || task.comment,
          acted_at: new Date().toISOString(),
        };
        pendingApprovals.value.splice(pendingIdx, 1);
        approvalHistory.value.unshift(updatedTask);
      }
      ElMessage.success("审批已拒绝");
    } catch (e: unknown) {
      handleError("rejectTask", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function transferTask(
    taskId: string,
    newAssigneeId: string,
    comment?: string
  ): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.transferTask(taskId, newAssigneeId, comment);
      const pendingIdx = pendingApprovals.value.findIndex((t) => t.id === taskId);
      if (pendingIdx !== -1) {
        const task = pendingApprovals.value[pendingIdx];
        const updatedTask: WorkflowTask = {
          ...task,
          status: "transferred",
          comment: comment || task.comment,
          assignee_id: newAssigneeId,
          transferred_from_id: task.assignee_id,
          acted_at: new Date().toISOString(),
        };
        pendingApprovals.value.splice(pendingIdx, 1);
        approvalHistory.value.unshift(updatedTask);
      }
      ElMessage.success("审批已转交");
    } catch (e: unknown) {
      handleError("transferTask", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  // ==================== Webhook Actions ====================
  async function loadWebhooks(baseId: string): Promise<WebhookConfig[]> {
    setLoading(true);
    clearError();
    try {
      const data = await workflowApiService.listWebhooks(baseId);
      webhooks.value = data;
      return data;
    } catch (e: unknown) {
      handleError("loadWebhooks", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function createWebhook(
    baseId: string,
    data: object
  ): Promise<WebhookConfig> {
    setLoading(true);
    clearError();
    try {
      const created = await workflowApiService.createWebhook(baseId, data);
      webhooks.value.push(created);
      ElMessage.success("Webhook 创建成功");
      return created;
    } catch (e: unknown) {
      handleError("createWebhook", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function updateWebhook(
    webhookId: string,
    data: object
  ): Promise<WebhookConfig> {
    setLoading(true);
    clearError();
    try {
      const updated = await workflowApiService.updateWebhook(webhookId, data);
      const idx = webhooks.value.findIndex((w) => w.id === webhookId);
      if (idx !== -1) {
        webhooks.value[idx] = updated;
      }
      ElMessage.success("Webhook 更新成功");
      return updated;
    } catch (e: unknown) {
      handleError("updateWebhook", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function deleteWebhook(webhookId: string): Promise<void> {
    setLoading(true);
    clearError();
    try {
      await workflowApiService.deleteWebhook(webhookId);
      webhooks.value = webhooks.value.filter((w) => w.id !== webhookId);
      ElMessage.success("Webhook 删除成功");
    } catch (e: unknown) {
      handleError("deleteWebhook", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function testWebhook(webhookId: string): Promise<object> {
    setLoading(true);
    clearError();
    try {
      const result = await workflowApiService.testWebhook(webhookId);
      ElMessage.success("Webhook 测试请求已发送");
      return result;
    } catch (e: unknown) {
      handleError("testWebhook", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  // ==================== Template Actions ====================
  async function loadTemplates(params?: object): Promise<WorkflowTemplate[]> {
    setLoading(true);
    clearError();
    try {
      const data = await workflowApiService.listTemplates(params);
      templates.value = data;
      return data;
    } catch (e: unknown) {
      handleError("loadTemplates", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function saveAsTemplate(
    workflowId: string,
    data: object
  ): Promise<WorkflowTemplate> {
    setLoading(true);
    clearError();
    try {
      const created = await workflowApiService.saveAsTemplate(workflowId, data);
      templates.value.push(created);
      ElMessage.success("已保存为模板");
      return created;
    } catch (e: unknown) {
      handleError("saveAsTemplate", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function instantiateTemplate(
    templateId: string,
    tableId: string
  ): Promise<Workflow> {
    setLoading(true);
    clearError();
    try {
      const created = await workflowApiService.instantiateTemplate(
        templateId,
        tableId
      );
      workflows.value.push(created);
      currentWorkflow.value = created;
      ElMessage.success("模板实例化成功");
      return created;
    } catch (e: unknown) {
      handleError("instantiateTemplate", e);
      throw e;
    } finally {
      setLoading(false);
    }
  }

  function $reset() {
    workflows.value = [];
    currentWorkflow.value = null;
    instances.value = [];
    currentInstance.value = null;
    pendingApprovals.value = [];
    approvalHistory.value = [];
    webhooks.value = [];
    templates.value = [];
    loading.value = false;
    error.value = null;
  }

  return {
    // state
    workflows,
    currentWorkflow,
    instances,
    currentInstance,
    pendingApprovals,
    approvalHistory,
    webhooks,
    templates,
    loading,
    error,
    // getters
    pendingApprovalCount,
    activeWorkflowCount,
    getWorkflowById,
    // actions
    loadWorkflows,
    loadWorkflow,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    publishWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    loadInstances,
    loadInstance,
    triggerWorkflow,
    loadApprovals,
    approveTask,
    rejectTask,
    transferTask,
    loadWebhooks,
    createWebhook,
    updateWebhook,
    deleteWebhook,
    testWebhook,
    loadTemplates,
    saveAsTemplate,
    instantiateTemplate,
    clearError,
    $reset,
  };
});
