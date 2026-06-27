<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import {
  Collection,
  EditPen,
  Timer,
  Link,
} from "@element-plus/icons-vue";
import { useWorkflowStore } from "@/stores/workflowStore";
import { useTableStore } from "@/stores/tableStore";
import { apiClient } from "@/api/client";
import { fieldService } from "@/db/services/fieldService";
import { formatDateTime } from "@/utils/timezone";
import WorkflowListPanel from "@/components/workflow/WorkflowListPanel.vue";
import WorkflowDesigner from "@/components/workflow/WorkflowDesigner.vue";
import WorkflowExecutionLogPanel from "@/components/workflow/WorkflowExecutionLog.vue";
import WebhookConfigPanel from "@/components/workflow/WebhookConfigPanel.vue";
import WebhookDeliveryList from "@/components/workflow/WebhookDeliveryList.vue";
import WorkflowTemplateGallery from "@/components/workflow/WorkflowTemplateGallery.vue";
import WorkflowVersionNodeSnapshot from "@/components/workflow/WorkflowVersionNodeSnapshot.vue";
import type {
  Workflow,
  WorkflowNode,
  WorkflowTrigger,
  WorkflowInstance,
  WorkflowExecutionLog,
  WebhookConfig,
  WorkflowVersion,
} from "@/types/workflow";
import type { FieldEntity } from "@/db/schema";

const route = useRoute();
const router = useRouter();
const baseId = route.params.id as string;

const workflowStore = useWorkflowStore();
const tableStore = useTableStore();

type TabType = "editor" | "history" | "webhook";

const activeTab = ref<TabType>("editor");
const galleryVisible = ref(false);

const currentWorkflow = computed(() => workflowStore.currentWorkflow);
const workflows = computed(() => workflowStore.workflows);
const tables = computed(() => tableStore.tables);

const nodes = ref<WorkflowNode[]>([]);
const trigger = ref<WorkflowTrigger | null>(null);
const fields = ref<FieldEntity[]>([]);
const instances = ref<WorkflowInstance[]>([]);
const selectedInstanceId = ref<string>("");
const executionLogs = ref<WorkflowExecutionLog[]>([]);
const selectedWebhookId = ref<string>("");
const detailLoading = ref(false);

// 编辑工作流弹窗
const editDialogVisible = ref(false);
const editFormRef = ref<FormInstance>();
const editForm = ref({
  id: "",
  name: "",
  description: "",
});
const editFormRules: FormRules = {
  name: [
    { required: true, message: "请输入工作流名称", trigger: "blur" },
    { max: 200, message: "名称不能超过 200 个字符", trigger: "blur" },
  ],
  description: [
    { max: 500, message: "描述不能超过 500 个字符", trigger: "blur" },
  ],
};
const editDescCharCount = computed(() => editForm.value.description.length);

const selectedInstance = computed(() =>
  instances.value.find((item) => item.id === selectedInstanceId.value),
);

const selectedWebhook = computed(() =>
  workflowStore.webhooks.find((item) => item.id === selectedWebhookId.value) ??
  null,
);

const designerTrigger = computed<WorkflowTrigger>(() => {
  return (
    trigger.value ?? {
      id: "",
      workflow_id: currentWorkflow.value?.id || "",
      trigger_type: "manual",
      filter_config: {},
      field_ids: [],
    }
  );
});

onMounted(() => {
  init();
});

watch(
  () => baseId,
  () => {
    init();
  },
);

watch(
  currentWorkflow,
  async (workflow) => {
    if (!workflow) {
      resetDetailState();
      return;
    }
    activeTab.value = "editor";
    await loadWorkflowDetail(workflow);
  },
  { immediate: false },
);

async function init() {
  if (!baseId) return;

  workflowStore.$reset();
  resetDetailState();

  await tableStore.loadTables(baseId);
  await workflowStore.loadWorkflows(baseId);

  if (workflows.value.length > 0) {
    workflowStore.currentWorkflow = workflows.value[0];
  }

  await workflowStore.loadWebhooks(baseId);
  selectedWebhookId.value = workflowStore.webhooks[0]?.id || "";
}

function resetDetailState() {
  nodes.value = [];
  trigger.value = null;
  fields.value = [];
  instances.value = [];
  selectedInstanceId.value = "";
  executionLogs.value = [];
}

async function loadWorkflowDetail(workflow: Workflow) {
  detailLoading.value = true;
  try {
    const [nodesData, triggerData] = await Promise.all([
      apiClient.get<WorkflowNode[]>(`/workflows/${workflow.id}/nodes`),
      apiClient.get<WorkflowTrigger>(`/workflows/${workflow.id}/trigger`),
    ]);
    nodes.value = nodesData;
    trigger.value = triggerData;
  } catch (error) {
    console.error("加载工作流详情失败:", error);
    nodes.value = [];
    trigger.value = null;
  }

  if (workflow.table_id) {
    try {
      fields.value = await fieldService.getFieldsByTable(workflow.table_id);
    } catch (error) {
      console.error("加载字段失败:", error);
      fields.value = [];
    }
  } else {
    fields.value = [];
  }

  try {
    instances.value = await workflowStore.loadInstances(workflow.id);
  } catch (error) {
    console.error("加载执行实例失败:", error);
    instances.value = [];
  }

  selectedInstanceId.value = instances.value[0]?.id || "";
  if (selectedInstanceId.value) {
    await loadExecutionLogs(workflow.id, selectedInstanceId.value);
  } else {
    executionLogs.value = [];
  }

  detailLoading.value = false;
}

async function loadExecutionLogs(workflowId: string, instanceId: string) {
  try {
    const data = await apiClient.get<{
      instance: WorkflowInstance;
      execution_logs: WorkflowExecutionLog[];
    }>(`/workflows/${workflowId}/instances/${instanceId}`);
    executionLogs.value = data.execution_logs;
  } catch (error) {
    console.error("加载执行日志失败:", error);
    executionLogs.value = [];
  }
}

function handleSelectWorkflow(workflow: Workflow) {
  workflowStore.currentWorkflow = workflow;
}

function handleEditWorkflow(workflow: Workflow) {
  editForm.value = {
    id: workflow.id,
    name: workflow.name,
    description: workflow.description || "",
  };
  editDialogVisible.value = true;
}

async function handleUpdateWorkflowInfo() {
  if (!editFormRef.value) return;
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return;
    try {
      await workflowStore.updateWorkflow(editForm.value.id, {
        name: editForm.value.name.trim(),
        description: editForm.value.description.trim(),
      });
      editDialogVisible.value = false;
    } catch (error: unknown) {
      console.error("更新工作流信息失败:", error);
    }
  });
}

async function handleDeleteWorkflow(workflow: Workflow) {
  await workflowStore.deleteWorkflow(workflow.id);
  if (currentWorkflow.value?.id === workflow.id) {
    workflowStore.currentWorkflow = workflows.value[0] || null;
  }
}

async function handlePublishWorkflow(workflow: Workflow) {
  await workflowStore.publishWorkflow(workflow.id);
}

async function handlePauseWorkflow(workflow: Workflow) {
  await workflowStore.pauseWorkflow(workflow.id);
}

async function handleResumeWorkflow(workflow: Workflow) {
  await workflowStore.resumeWorkflow(workflow.id);
}

function openCreateDialog() {
  // 左侧列表的新建按钮通过此函数打开编辑弹窗，复用编辑表单作为新建
  editForm.value = {
    id: "",
    name: "",
    description: "",
  };
  editDialogVisible.value = true;
}

async function handleCreateWorkflow() {
  if (!editFormRef.value) return;
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return;
    try {
      const created = await workflowStore.createWorkflow(baseId, {
        name: editForm.value.name.trim(),
        description: editForm.value.description.trim(),
      });
      editDialogVisible.value = false;
      await workflowStore.loadWorkflows(baseId);
      workflowStore.currentWorkflow = created;
    } catch (error: unknown) {
      console.error("新建工作流失败:", error);
    }
  });
}

function handleBackToBase() {
  router.push(`/base/${baseId}`);
}

async function handleUpdateTable(workflow: Workflow, tableId: string) {
  try {
    await workflowStore.updateWorkflow(workflow.id, { table_id: tableId });
    if (currentWorkflow.value?.id === workflow.id) {
      await loadWorkflowDetail(currentWorkflow.value);
    }
  } catch (error: unknown) {
    console.error("变更数据表失败:", error);
  }
}

function handleOpenGallery() {
  galleryVisible.value = true;
}

function handleGalleryCreated(workflow: Workflow) {
  galleryVisible.value = false;
  workflowStore.currentWorkflow = workflow;
}

async function handleSaveWorkflow(
  updatedNodes: WorkflowNode[],
  updatedTrigger: WorkflowTrigger,
) {
  if (!currentWorkflow.value) return;

  try {
    await Promise.all([
      apiClient.put(`/workflows/${currentWorkflow.value.id}/nodes`, {
        nodes: updatedNodes,
      }),
      apiClient.put(`/workflows/${currentWorkflow.value.id}/trigger`, {
        ...updatedTrigger,
      }),
    ]);
    ElMessage.success("工作流保存成功");
  } catch (error) {
    console.error("保存工作流失败:", error);
    ElMessage.error("保存工作流失败");
  }
}

async function handlePublishFromDesigner() {
  if (!currentWorkflow.value) return;
  await workflowStore.publishWorkflow(currentWorkflow.value.id);
}

async function handleCloneWorkflow() {
  if (!currentWorkflow.value) return;
  try {
    await workflowStore.cloneWorkflow(currentWorkflow.value.id);
    await workflowStore.loadWorkflows(baseId);
    activeTab.value = "editor";
  } catch (error: unknown) {
    console.error("克隆工作流失败:", error);
  }
}

const versionDialogVisible = ref(false);
const versionLoading = ref(false);

async function handleViewVersions() {
  if (!currentWorkflow.value) return;
  versionDialogVisible.value = true;
  versionLoading.value = true;
  try {
    await workflowStore.loadWorkflowVersions(currentWorkflow.value.id);
  } catch (error: unknown) {
    console.error("加载版本历史失败:", error);
  } finally {
    versionLoading.value = false;
  }
}

async function handleInstanceChange(instanceId: string) {
  selectedInstanceId.value = instanceId;
  if (currentWorkflow.value && instanceId) {
    await loadExecutionLogs(currentWorkflow.value.id, instanceId);
  }
}

function handleWebhookRowClick(row: WebhookConfig) {
  selectedWebhookId.value = row.id;
}

function handleWebhookSaved(webhook: WebhookConfig) {
  const idx = workflowStore.webhooks.findIndex((item) => item.id === webhook.id);
  if (idx !== -1) {
    workflowStore.webhooks[idx] = webhook;
  } else {
    workflowStore.webhooks.push(webhook);
  }
  selectedWebhookId.value = webhook.id;
}

function getWebhookStatusType(isActive: boolean): "success" | "info" {
  return isActive ? "success" : "info";
}

function getVersionNodes(version: WorkflowVersion): WorkflowNode[] {
  const nodes = version.config_snapshot?.nodes;
  return Array.isArray(nodes) ? (nodes as WorkflowNode[]) : [];
}
</script>

<template>
  <div v-loading="workflowStore.loading" class="workflow-manager">
    <div class="workflow-sidebar">
      <WorkflowListPanel
        :base-id="baseId"
        :workflows="workflows"
        :loading="workflowStore.loading"
        :current-workflow-id="currentWorkflow?.id"
        :tables="tables"
        @create="openCreateDialog"
        @select="handleSelectWorkflow"
        @back="handleBackToBase"
        @edit="handleEditWorkflow"
        @delete="handleDeleteWorkflow"
        @publish="handlePublishWorkflow"
        @pause="handlePauseWorkflow"
        @resume="handleResumeWorkflow"
        @update-table="handleUpdateTable" />
    </div>

    <div class="workflow-main">
      <div class="workflow-header">
        <div class="header-tabs">
          <el-radio-group v-model="activeTab" size="small">
            <el-radio-button label="editor">
              <el-icon><EditPen /></el-icon>
              <span>工作流编辑器</span>
            </el-radio-button>
            <el-radio-button label="history">
              <el-icon><Timer /></el-icon>
              <span>执行历史</span>
            </el-radio-button>
            <el-radio-button label="webhook">
              <el-icon><Link /></el-icon>
              <span>Webhook 管理</span>
            </el-radio-button>
          </el-radio-group>
        </div>

        <div class="header-actions">
          <el-button :icon="Collection" @click="handleOpenGallery">
            模板库
          </el-button>
        </div>
      </div>

      <div class="workflow-content">
        <div v-if="!currentWorkflow" class="empty-container">
          <el-empty description="请选择或创建一个工作流" />
        </div>

        <template v-else>
          <div
            v-show="activeTab === 'editor'"
            v-loading="detailLoading"
            class="tab-panel">
            <WorkflowDesigner
              :workflow="currentWorkflow"
              :nodes="nodes"
              :trigger="designerTrigger"
              :fields="fields"
              :tables="tables"
              :webhooks="workflowStore.webhooks"
              @update:nodes="nodes = $event"
              @update:trigger="trigger = $event"
              @save="handleSaveWorkflow(nodes, designerTrigger)"
              @publish="handlePublishFromDesigner"
              @clone="handleCloneWorkflow"
              @view-versions="handleViewVersions" />
          </div>

          <div v-show="activeTab === 'history'" class="tab-panel history-panel">
            <div class="instance-selector">
              <span class="selector-label">执行实例：</span>
              <el-select
                v-model="selectedInstanceId"
                placeholder="请选择执行实例"
                style="width: 320px"
                @change="handleInstanceChange">
                <el-option
                  v-for="instance in instances"
                  :key="instance.id"
                  :label="`#${instance.id.slice(0, 8)} - ${instance.status}`"
                  :value="instance.id" />
              </el-select>
            </div>

            <div class="log-container">
              <WorkflowExecutionLogPanel
                v-if="selectedInstance"
                :instance="selectedInstance"
                :logs="executionLogs" />
              <el-empty v-else description="暂无执行实例" />
            </div>
          </div>

          <div v-show="activeTab === 'webhook'" class="tab-panel webhook-panel">
            <div class="webhook-layout">
              <div class="webhook-list">
                <div class="webhook-list-header">
                  <span class="list-title">Webhook 列表</span>
                  <el-button
                    type="primary"
                    size="small"
                    @click="selectedWebhookId = ''">
                    新建
                  </el-button>
                </div>
                <el-table
                  :data="workflowStore.webhooks"
                  highlight-current-row
                  style="width: 100%"
                  @row-click="handleWebhookRowClick">
                  <el-table-column prop="name" label="名称" min-width="140" />
                  <el-table-column prop="method" label="方法" width="80" />
                  <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
                  <el-table-column label="状态" width="80" fixed="right">
                    <template #default="{ row }">
                      <el-tag :type="getWebhookStatusType(row.is_active)" size="small">
                        {{ row.is_active ? "启用" : "禁用" }}
                      </el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </div>

              <div class="webhook-detail">
                <WebhookConfigPanel
                  :webhook="selectedWebhook"
                  :base-id="baseId"
                  @saved="handleWebhookSaved"
                  @cancel="selectedWebhookId = ''" />

                <div
                  v-if="selectedWebhook"
                  class="webhook-deliveries">
                  <div class="section-title">投递记录</div>
                  <WebhookDeliveryList :webhook-id="selectedWebhook.id" />
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 编辑/新建工作流弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="editForm.id ? '编辑工作流' : '新建工作流'"
      width="520px"
      destroy-on-close>
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-position="top">
        <el-form-item label="工作流名称" prop="name">
          <el-input
            v-model="editForm.name"
            placeholder="请输入工作流名称"
            maxlength="200"
            show-word-limit
            clearable />
        </el-form-item>

        <el-form-item label="工作流描述" prop="description">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="4"
            placeholder="请描述工作流的用途、功能和注意事项（可选）"
            maxlength="500"
            show-word-limit
            resize="none" />
          <div class="form-char-count">
            {{ editDescCharCount }} / 500
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="editForm.id ? handleUpdateWorkflowInfo() : handleCreateWorkflow()">
          {{ editForm.id ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 版本历史弹窗 -->
    <el-dialog
      v-model="versionDialogVisible"
      title="版本历史"
      width="680px"
      destroy-on-close>
      <el-table
        v-loading="versionLoading"
        :data="workflowStore.versions"
        row-key="id"
        style="width: 100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="version-snapshot">
              <div class="snapshot-section">
                <div class="snapshot-label">节点列表：</div>
                <el-empty
                  v-if="getVersionNodes(row).length === 0"
                  description="无节点信息"
                  :image-size="60" />
                <el-collapse v-else>
                  <el-collapse-item
                    v-for="(node, index) in getVersionNodes(row)"
                    :key="node.id || index"
                    :title="`${node.name || '未命名节点'} (#${node.order + 1 || index + 1})`">
                    <WorkflowVersionNodeSnapshot
                      :node="node"
                      :fields="fields"
                      :tables="tables"
                      :webhooks="workflowStore.webhooks" />
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="版本号" width="100">
          <template #default="{ row }">
            <el-tag type="primary" size="small">v{{ row.version_number }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ row.created_at ? formatDateTime(row.created_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="创建者" min-width="140">
          <template #default="{ row }">
            {{ row.created_by_name || row.created_by || '-' }}
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="versionDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <WorkflowTemplateGallery
      v-model:visible="galleryVisible"
      :base-id="baseId"
      :tables="tables"
      @created="handleGalleryCreated" />
  </div>
</template>

<style lang="scss" scoped>
.workflow-manager {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: $bg-color;
}

.workflow-sidebar {
  flex-shrink: 0;
  height: 100%;
  border-right: 1px solid $border-color;
  background-color: white;
  overflow: hidden;
}

.workflow-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.workflow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  border-bottom: 1px solid $border-color;
  background-color: white;
}

.header-tabs {
  :deep(.el-radio-button__inner) {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xs;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.workflow-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.tab-panel {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.history-panel {
  display: flex;
  flex-direction: column;
  padding: $spacing-md;
  gap: $spacing-md;
}

.instance-selector {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.selector-label {
  font-size: $font-size-sm;
  color: $text-secondary;
  white-space: nowrap;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background-color: white;
  border-radius: $border-radius-md;
  padding: $spacing-md;
}

.webhook-panel {
  display: flex;
  flex-direction: column;
  padding: $spacing-md;
}

.webhook-layout {
  display: flex;
  gap: $spacing-md;
  height: 100%;
  overflow: hidden;
}

.webhook-list {
  width: 45%;
  min-width: 360px;
  background-color: white;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  overflow-y: auto;
}

.webhook-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-md;
}

.list-title {
  font-weight: 600;
  color: $text-primary;
}

.webhook-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  overflow-y: auto;
}

.webhook-detail > * {
  background-color: white;
  border-radius: $border-radius-md;
  padding: $spacing-md;
}

.webhook-deliveries {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.section-title {
  font-weight: 600;
  color: $text-primary;
}

.form-help-text {
  margin-top: 4px;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.5;
}

.form-char-count {
  margin-top: 4px;
  font-size: 12px;
  color: $text-disabled;
  text-align: right;
}

.version-snapshot {
  padding: $spacing-sm $spacing-md;
  background-color: $bg-color;
  border-radius: $border-radius-md;
}

.snapshot-section {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.snapshot-label {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-secondary;
}
</style>
