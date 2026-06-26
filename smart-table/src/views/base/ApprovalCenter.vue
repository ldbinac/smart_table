<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { useWorkflowStore } from "@/stores/workflowStore";
import { useUserCacheStore } from "@/stores/userCacheStore";
import { tableService } from "@/db/services/tableService";
import { formatDateTime } from "@/utils/timezone";
import ApprovalDetailDialog from "@/components/workflow/ApprovalDetailDialog.vue";
import ApprovalHistoryDrawer from "@/components/workflow/ApprovalHistoryDrawer.vue";
import type { ApprovalTask } from "@/components/workflow/types";
import type { TaskStatus, Workflow } from "@/types/workflow";
import type { TableEntity } from "@/db/schema";

type StatusFilter = TaskStatus | "all";

const route = useRoute();
const workflowStore = useWorkflowStore();
const userCacheStore = useUserCacheStore();

const baseId = computed(() => route.params.id as string);

const statusFilter = ref<StatusFilter>("all");
const tableFilter = ref<string>("");
const workflowFilter = ref<string>("");
const workflows = ref<Workflow[]>([]);
const tables = ref<TableEntity[]>([]);
const detailVisible = ref(false);
const selectedTask = ref<ApprovalTask | null>(null);
const historyVisible = ref(false);
const historyRecordId = ref<string>("");

const statusOptions: { label: string; value: StatusFilter }[] = [
  { label: "全部", value: "all" },
  { label: "待审批", value: "pending" },
  { label: "已通过", value: "approved" },
  { label: "已驳回", value: "rejected" },
  { label: "已转办", value: "transferred" },
];

const statusMap: Record<TaskStatus, { label: string; type: "success" | "danger" | "warning" | "info" | "primary" }> = {
  pending: { label: "待审批", type: "primary" },
  approved: { label: "已通过", type: "success" },
  rejected: { label: "已驳回", type: "danger" },
  transferred: { label: "已转办", type: "warning" },
  expired: { label: "已过期", type: "info" },
};

const allTasks = computed<ApprovalTask[]>(() => {
  return [...workflowStore.pendingApprovals, ...workflowStore.approvalHistory] as ApprovalTask[];
});

const filteredTasks = computed(() => {
  return allTasks.value.filter((task) => {
    if (statusFilter.value !== "all" && task.status !== statusFilter.value) {
      return false;
    }
    if (tableFilter.value && task.record?.table_id !== tableFilter.value) {
      return false;
    }
    if (workflowFilter.value && task.workflow?.id !== workflowFilter.value) {
      return false;
    }
    return true;
  });
});

async function loadApprovals() {
  if (!baseId.value) return;

  try {
    const params: Record<string, string> = {};
    if (statusFilter.value !== "all") {
      params.status = statusFilter.value;
    }
    if (tableFilter.value) {
      params.table_id = tableFilter.value;
    }
    if (workflowFilter.value) {
      params.workflow_id = workflowFilter.value;
    }
    await workflowStore.loadApprovals(baseId.value, params);
    await loadUserNames();
  } catch (error) {
    console.error("[ApprovalCenter] 加载审批任务失败:", error);
    ElMessage.error("加载审批任务失败");
  }
}

async function loadFilters() {
  if (!baseId.value) return;

  try {
    const [workflowData, tableData] = await Promise.all([
      workflowStore.loadWorkflows(baseId.value),
      tableService.getTablesByBase(baseId.value),
    ]);
    workflows.value = workflowData;
    tables.value = tableData;
  } catch (error) {
    console.error("[ApprovalCenter] 加载筛选数据失败:", error);
  }
}

async function loadUserNames() {
  const ids = new Set<string>();
  allTasks.value.forEach((task) => {
    if (task.assignee_id) ids.add(task.assignee_id);
    if (task.transferred_from_id) ids.add(task.transferred_from_id);
    const createdBy = task.record?.created_by;
    if (typeof createdBy === "string" && createdBy) ids.add(createdBy);
  });
  if (ids.size > 0) {
    await userCacheStore.fetchUsers(Array.from(ids));
  }
}

function resolveUserName(
  userIdOrUser: string | { id: string; name?: string } | null | undefined
) {
  if (!userIdOrUser) return "未知";
  if (typeof userIdOrUser === "object") {
    return userIdOrUser.name || userIdOrUser.id;
  }
  const cached = userCacheStore.getCachedUser(userIdOrUser);
  return cached?.name || userIdOrUser;
}

function getTaskTitle(task: ApprovalTask): string {
  return task.record?.title || `记录 ${task.record?.id || task.id}`;
}

function getCreatorName(task: ApprovalTask): string {
  return resolveUserName(task.record?.created_by);
}

function getCreatedTime(task: ApprovalTask): string {
  return task.record?.created_at ? formatDateTime(task.record.created_at) : "-";
}

function getNodeName(task: ApprovalTask): string {
  return task.node?.name || "-";
}

function handleRowClick(task: ApprovalTask) {
  selectedTask.value = task;
  detailVisible.value = true;
}

function handleDetailSuccess() {
  loadApprovals();
}

function handleShowHistory(task: ApprovalTask) {
  historyRecordId.value = task.record?.id || "";
  if (!historyRecordId.value) {
    ElMessage.warning("暂无关联记录");
    return;
  }
  historyVisible.value = true;
}

watch([statusFilter, tableFilter, workflowFilter], () => {
  loadApprovals();
});

watch(
  () => baseId.value,
  () => {
    loadFilters();
    loadApprovals();
  }
);

onMounted(() => {
  loadFilters();
  loadApprovals();
});
</script>

<template>
  <div class="approval-center-page">
    <div class="page-header">
      <h1 class="page-title">审批中心</h1>
    </div>

    <div class="page-content">
      <el-card class="filter-card">
        <div class="filter-bar">
          <el-radio-group v-model="statusFilter" size="default">
            <el-radio-button
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.value">
              {{ option.label }}
            </el-radio-button>
          </el-radio-group>

          <div class="filter-selects">
            <el-select
              v-model="tableFilter"
              clearable
              placeholder="按表格筛选"
              size="default"
              style="width: 180px">
              <el-option
                v-for="table in tables"
                :key="table.id"
                :label="table.name"
                :value="table.id" />
            </el-select>

            <el-select
              v-model="workflowFilter"
              clearable
              placeholder="按工作流筛选"
              size="default"
              style="width: 180px">
              <el-option
                v-for="workflow in workflows"
                :key="workflow.id"
                :label="workflow.name"
                :value="workflow.id" />
            </el-select>
          </div>
        </div>
      </el-card>

      <el-card v-loading="workflowStore.loading" class="list-card">
        <el-table
          :data="filteredTasks"
          style="width: 100%"
          highlight-current-row
          @row-click="(_row: ApprovalTask) => handleRowClick(_row)">
          <el-table-column label="标题" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="task-title">{{ getTaskTitle(row as ApprovalTask) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="发起人" width="140">
            <template #default="{ row }">
              {{ getCreatorName(row as ApprovalTask) }}
            </template>
          </el-table-column>

          <el-table-column label="发起时间" width="160">
            <template #default="{ row }">
              {{ getCreatedTime(row as ApprovalTask) }}
            </template>
          </el-table-column>

          <el-table-column label="当前审批节点" width="160">
            <template #default="{ row }">
              {{ getNodeName(row as ApprovalTask) }}
            </template>
          </el-table-column>

          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusMap[(row as ApprovalTask).status].type" size="small" effect="light">
                {{ statusMap[(row as ApprovalTask).status].label }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                @click.stop="handleShowHistory(row as ApprovalTask)">
                历史
              </el-button>
              <el-button
                link
                type="primary"
                size="small"
                @click.stop="handleRowClick(row as ApprovalTask)">
                详情
              </el-button>
            </template>
          </el-table-column>

          <template #empty>
            <el-empty description="暂无审批任务" :image-size="80" />
          </template>
        </el-table>
      </el-card>
    </div>

    <ApprovalDetailDialog
      v-if="selectedTask"
      v-model:visible="detailVisible"
      :task="selectedTask"
      @success="handleDetailSuccess" />

    <ApprovalHistoryDrawer
      v-model:visible="historyVisible"
      :record-id="historyRecordId" />
  </div>
</template>

<style scoped lang="scss">
.approval-center-page {
  padding: 24px;
  min-height: 100%;
  background-color: $gray-50;
}

.page-header {
  margin-bottom: 24px;

  .page-title {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: $text-primary;
  }
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  border-radius: $border-radius-lg;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.filter-selects {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.list-card {
  border-radius: $border-radius-lg;
}

.task-title {
  color: $primary-color;
  font-weight: 500;
  cursor: pointer;
}
</style>
