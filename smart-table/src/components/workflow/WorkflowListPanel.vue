<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useWorkflowStore } from "@/stores/workflowStore";
import type { Workflow, WorkflowStatus } from "@/types/workflow";
import type { TableEntity } from "@/db/schema";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Plus,
  Edit,
  Delete,
  VideoPlay,
  VideoPause,
  RefreshRight,
  Connection,
  Switch,
  Fold,
  Expand,
  Search,
} from "@element-plus/icons-vue";

interface Props {
  baseId: string;
  workflows?: Workflow[];
  loading?: boolean;
  currentWorkflowId?: string;
  tables?: TableEntity[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "create"): void;
  (e: "select", workflow: Workflow): void;
  (e: "edit", workflow: Workflow): void;
  (e: "delete", workflow: Workflow): void;
  (e: "publish", workflow: Workflow): void;
  (e: "pause", workflow: Workflow): void;
  (e: "resume", workflow: Workflow): void;
  (e: "updateTable", workflow: Workflow, tableId: string): void;
}>();

const workflowStore = useWorkflowStore();

const isCollapsed = ref(false);
function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value;
}

const statusFilter = ref<WorkflowStatus | "all">("all");
const searchKeyword = ref("");
const relationDialogVisible = ref(false);
const switchTableDialogVisible = ref(false);
const switchTableWorkflow = ref<Workflow | null>(null);
const switchTableId = ref("");

const tableMap = computed(() => {
  const map: Record<string, TableEntity> = {};
  (props.tables ?? []).forEach((t) => {
    map[t.id] = t;
  });
  return map;
});

const tableNameMap = computed(() => {
  const map: Record<string, string> = {};
  (props.tables ?? []).forEach((t) => {
    map[t.id] = t.name;
  });
  return map;
});

const groupedByTable = computed(() => {
  const groups: Record<string, Workflow[]> = {};
  const unlinked: Workflow[] = [];
  workflows.value.forEach((w) => {
    if (w.table_id && tableMap.value[w.table_id]) {
      if (!groups[w.table_id]) groups[w.table_id] = [];
      groups[w.table_id].push(w);
    } else {
      unlinked.push(w);
    }
  });
  return { groups, unlinked };
});

const statusOptions: { value: WorkflowStatus | "all"; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "draft", label: "草稿" },
  { value: "active", label: "已发布" },
  { value: "paused", label: "已暂停" },
  { value: "archived", label: "已归档" },
];

const workflows = computed(() => props.workflows ?? workflowStore.workflows);
const isLoading = computed(() => props.loading ?? workflowStore.loading);

const filteredWorkflows = computed(() => {
  if (statusFilter.value === "all") return workflows.value;
  return workflows.value.filter((w) => w.status === statusFilter.value);
});

const searchFilteredWorkflows = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  if (!keyword) return filteredWorkflows.value;
  return filteredWorkflows.value.filter(
    (w) =>
      w.name.toLowerCase().includes(keyword) ||
      (w.description ?? "").toLowerCase().includes(keyword),
  );
});

async function loadWorkflows() {
  if (props.workflows) return;
  await workflowStore.loadWorkflows(props.baseId);
}

onMounted(() => {
  loadWorkflows();
});

watch(
  () => props.baseId,
  () => {
    loadWorkflows();
  },
);

function getStatusType(status: WorkflowStatus) {
  const map: Record<WorkflowStatus, "info" | "success" | "warning" | "danger"> =
    {
      draft: "info",
      active: "success",
      paused: "warning",
      archived: "danger",
    };
  return map[status] ?? "info";
}

function getStatusLabel(status: WorkflowStatus) {
  const map: Record<WorkflowStatus, string> = {
    draft: "草稿",
    active: "已发布",
    paused: "已暂停",
    archived: "已归档",
  };
  return map[status] ?? status;
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString("zh-CN");
}

async function handleDelete(workflow: Workflow) {
  try {
    await ElMessageBox.confirm(
      `确定要删除工作流 "${workflow.name}" 吗？`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
    emit("delete", workflow);
  } catch {
    // 用户取消
  }
}

function handlePublish(workflow: Workflow) {
  emit("publish", workflow);
}

function handlePause(workflow: Workflow) {
  emit("pause", workflow);
}

function handleResume(workflow: Workflow) {
  emit("resume", workflow);
}

function handleEdit(workflow: Workflow) {
  emit("edit", workflow);
}

function handleCreate() {
  emit("create");
}

function openRelationDialog() {
  relationDialogVisible.value = true;
}

function openSwitchTableDialog(workflow: Workflow) {
  switchTableWorkflow.value = workflow;
  switchTableId.value = workflow.table_id || "";
  switchTableDialogVisible.value = true;
}

function handleSwitchTable() {
  if (!switchTableWorkflow.value) return;
  if (!switchTableId.value) {
    ElMessage.warning("请选择关联数据表");
    return;
  }
  emit("updateTable", switchTableWorkflow.value, switchTableId.value);
  switchTableDialogVisible.value = false;
  switchTableWorkflow.value = null;
  switchTableId.value = "";
}
</script>

<template>
  <div class="workflow-list-panel" :class="{ collapsed: isCollapsed }">
    <div class="header-actions">
      <el-button class="action-btn" :icon="Connection" @click="openRelationDialog">
        <span class="btn-text">关联关系</span>
      </el-button>
      <el-button class="action-btn" type="primary" :icon="Plus" @click="handleCreate">
        <span class="btn-text">新建工作流</span>
      </el-button>
      <el-button
        class="collapse-btn"
        text
        circle
        size="small"
        :icon="isCollapsed ? Expand : Fold"
        :title="isCollapsed ? '展开' : '收缩'"
        @click="toggleCollapse" />
    </div>
    <div class="panel-header">
      <div class="filter-tabs">
        <el-radio-group v-model="statusFilter" size="small">
          <el-radio-button
            v-for="option in statusOptions"
            :key="option.value"
            :label="option.value">
            {{ option.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="workflow-search">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索工作流名称或描述"
        :prefix-icon="Search"
        clearable
        size="small" />
    </div>

    <div v-loading="isLoading" class="workflow-list">
      <el-card
        v-for="workflow in searchFilteredWorkflows"
        :key="workflow.id"
        class="workflow-card"
        :class="{ 'is-active': workflow.id === currentWorkflowId }"
        shadow="hover"
        @click="emit('select', workflow)">
        <div class="card-header">
          <div class="workflow-info">
            <div class="workflow-name">{{ workflow.name }}</div>
            <el-tag size="small" :type="getStatusType(workflow.status)">
              {{ getStatusLabel(workflow.status) }}
            </el-tag>
          </div>
          <div class="workflow-version">v{{ workflow.current_version }}</div>
        </div>

        <div class="workflow-table-link">
          <el-icon><Connection /></el-icon>
          <span class="table-name">
            {{
              workflow.table_id
                ? tableNameMap[workflow.table_id] || "未知数据表"
                : "未关联数据表"
            }}
          </span>
          <el-button
            v-if="workflow.status === 'draft'"
            type="primary"
            link
            size="small"
            :icon="Switch"
            @click.stop="openSwitchTableDialog(workflow)">
            变更
          </el-button>
        </div>

        <div class="workflow-description">
          {{ workflow.description || "暂无描述" }}
        </div>

        <div class="workflow-meta">
          <span>创建于 {{ formatDate(workflow.created_at) }}</span>
          <span>更新于 {{ formatDate(workflow.updated_at) }}</span>
        </div>

        <div class="card-actions">
          <el-button
            type="primary"
            :icon="Edit"
            text
            size="small"
            @click.stop="handleEdit(workflow)">
            编辑
          </el-button>

          <template v-if="workflow.status === 'draft'">
            <el-button
              type="success"
              :icon="VideoPlay"
              text
              size="small"
              @click="handlePublish(workflow)">
              发布
            </el-button>
          </template>

          <template v-if="workflow.status === 'active'">
            <el-button
              type="warning"
              :icon="VideoPause"
              text
              size="small"
              @click="handlePause(workflow)">
              暂停
            </el-button>
          </template>

          <template v-if="workflow.status === 'paused'">
            <el-button
              type="success"
              :icon="RefreshRight"
              text
              size="small"
              @click="handleResume(workflow)">
              恢复
            </el-button>
          </template>

          <el-button
            type="danger"
            :icon="Delete"
            text
            size="small"
            @click="handleDelete(workflow)">
            删除
          </el-button>
        </div>
      </el-card>

      <el-empty
        v-if="searchFilteredWorkflows.length === 0 && !isLoading"
        description="没有找到匹配的工作流" />
    </div>

    <!-- 关联关系可视化弹窗 -->
    <el-dialog
      v-model="relationDialogVisible"
      title="工作流与数据表关联关系"
      width="720px"
      destroy-on-close>
      <div class="relation-dialog-content">
        <div
          v-for="(groupWorkflows, tableId) in groupedByTable.groups"
          :key="tableId"
          class="relation-group">
          <div class="relation-table-header">
            <el-icon><Connection /></el-icon>
            <span class="relation-table-name">{{
              tableNameMap[tableId] || "未知数据表"
            }}</span>
            <el-tag size="small" type="info"
              >{{ groupWorkflows.length }} 个工作流</el-tag
            >
          </div>
          <div class="relation-workflow-list">
            <el-tag
              v-for="w in groupWorkflows"
              :key="w.id"
              :type="getStatusType(w.status)"
              size="small"
              class="relation-workflow-tag"
              @click="
                emit('select', w);
                relationDialogVisible = false;
              ">
              {{ w.name }}
            </el-tag>
          </div>
        </div>

        <div
          v-if="groupedByTable.unlinked.length > 0"
          class="relation-group unlinked-group">
          <div class="relation-table-header">
            <el-icon><Connection /></el-icon>
            <span class="relation-table-name">未关联数据表</span>
            <el-tag size="small" type="warning"
              >{{ groupedByTable.unlinked.length }} 个工作流</el-tag
            >
          </div>
          <div class="relation-workflow-list">
            <el-tag
              v-for="w in groupedByTable.unlinked"
              :key="w.id"
              :type="getStatusType(w.status)"
              size="small"
              class="relation-workflow-tag"
              @click="
                emit('select', w);
                relationDialogVisible = false;
              ">
              {{ w.name }}
            </el-tag>
          </div>
        </div>

        <el-empty v-if="workflows.length === 0" description="暂无工作流" />
      </div>
    </el-dialog>

    <!-- 变更数据表弹窗 -->
    <el-dialog
      v-model="switchTableDialogVisible"
      title="变更关联数据表"
      width="480px"
      destroy-on-close>
      <div class="switch-table-form">
        <div class="switch-table-info">
          <div class="info-label">当前工作流</div>
          <div class="info-value">{{ switchTableWorkflow?.name }}</div>
        </div>
        <div class="switch-table-info">
          <div class="info-label">当前关联数据表</div>
          <div class="info-value">
            {{
              switchTableWorkflow?.table_id
                ? tableNameMap[switchTableWorkflow.table_id] || "未知数据表"
                : "未关联"
            }}
          </div>
        </div>
        <el-form label-position="top">
          <el-form-item label="选择新的关联数据表" required>
            <el-select
              v-model="switchTableId"
              placeholder="请选择数据表"
              style="width: 100%">
              <el-option
                v-for="table in tables"
                :key="table.id"
                :label="table.name"
                :value="table.id" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="switchTableDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSwitchTable"
          >确认变更</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.workflow-list-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  width: 360px;
  transition: width 0.3s ease;
  overflow: hidden;

  &.collapsed {
    width: 72px;
  }
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  border-bottom: 1px solid $border-color;
}

.filter-tabs {
  .collapsed & {
    display: none;
  }
}

.workflow-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: $spacing-md;
  display: grid;
  grid-template-columns: 1fr;
  gap: $spacing-md;
  align-content: start;

  .collapsed & {
    padding: $spacing-sm;
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }
}

.workflow-search {
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid $border-color;

  .collapsed & {
    display: none;
  }
}

.workflow-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid #2a2a2a24;

  &:hover {
    border-color: $primary-hover;
  }

  &.is-active {
    border-color: $primary-color;
    background-color: $primary-light;

    :deep(.el-card__body) {
      background-color: $primary-light;
    }

    .workflow-name {
      color: $primary-color;
      font-weight: 700;
    }
  }

  :deep(.el-card__body) {
    padding: $spacing-md;
  }

  .collapsed & {
    :deep(.el-card__body) {
      padding: $spacing-sm;
    }

    .card-header {
      flex-direction: column;
      align-items: center;
      margin-bottom: 0;
    }

    .workflow-info {
      flex-direction: column;
      align-items: center;
      gap: $spacing-xs;
    }

    .workflow-name {
      font-size: $font-size-sm;
      text-align: center;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      /* autoprefixer: ignore next */
      -webkit-box-orient: vertical;
      overflow: hidden;
      width: 100%;
    }

    .workflow-version,
    .workflow-table-link,
    .workflow-description,
    .workflow-meta,
    .card-actions {
      display: none;
    }

    .el-tag {
      transform: scale(0.85);
    }
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: $spacing-sm;
}

.workflow-info {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.workflow-name {
  font-weight: 600;
  font-size: $font-size-base;
  color: $text-primary;
}

.workflow-version {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.workflow-table-link {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-bottom: $spacing-sm;

  .table-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.workflow-description {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-bottom: $spacing-sm;
  min-height: 20px;
}

.workflow-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: $text-disabled;
  margin-bottom: $spacing-sm;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
  padding-top: $spacing-sm;
  border-top: 1px solid $border-color;
}

/* 关联关系弹窗 */
.relation-dialog-content {
  max-height: 520px;
  overflow-y: auto;
}

.relation-group {
  margin-bottom: $spacing-md;
  padding: $spacing-md;
  background-color: $gray-50;
  border-radius: $border-radius-md;

  &.unlinked-group {
    background-color: $warning-light;
  }
}

.relation-table-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;
  font-weight: 600;
  color: $text-primary;
}

.relation-table-name {
  flex: 1;
}

.relation-workflow-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.relation-workflow-tag {
  cursor: pointer;
}

/* 变更数据表弹窗 */
.switch-table-form {
  .switch-table-info {
    display: flex;
    align-items: center;
    margin-bottom: $spacing-md;
    padding: $spacing-sm $spacing-md;
    background-color: $gray-50;
    border-radius: $border-radius-sm;

    .info-label {
      width: 120px;
      font-size: $font-size-sm;
      color: $text-secondary;
    }

    .info-value {
      flex: 1;
      font-weight: 600;
      color: $text-primary;
    }
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-top: $spacing-md;
  margin-left: $spacing-lg;

  .btn-text {
    transition: opacity 0.2s ease;
  }

  .collapse-btn {
    margin-left: auto;
    transition: background-color 0.2s;

    &:hover {
      background-color: var(--el-fill-color-light);
    }
  }

  .collapsed & {
    margin-left: $spacing-sm;
    margin-right: $spacing-sm;

    .action-btn {
      display: none;
    }

    .btn-text {
      display: none;
    }

    .collapse-btn {
      margin-left: 0;
      width: 100%;
    }
  }
}
</style>
