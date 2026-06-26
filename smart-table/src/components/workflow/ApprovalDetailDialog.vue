<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import { useWorkflowStore } from "@/stores/workflowStore";
import { useUserCacheStore } from "@/stores/userCacheStore";
import { formatDateTime } from "@/utils/timezone";
import MemberSelect from "@/components/common/MemberSelect.vue";
import ApprovalHistoryDrawer from "./ApprovalHistoryDrawer.vue";
import type { ApprovalTask } from "./types";
import type { TaskStatus } from "@/types/workflow";

type ActionType = "approve" | "reject" | "transfer";

const props = defineProps<{
  task: ApprovalTask;
  visible: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  success: [];
}>();

const workflowStore = useWorkflowStore();
const userCacheStore = useUserCacheStore();

const actionLoading = ref(false);
const comment = ref("");
const newAssigneeIds = ref<string[]>([]);
const currentAction = ref<ActionType | null>(null);
const historyVisible = ref(false);

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit("update:visible", value),
});

const isPending = computed(() => props.task.status === "pending");

const statusMap: Record<TaskStatus, { label: string; type: "success" | "danger" | "warning" | "info" | "primary" }> = {
  pending: { label: "待审批", type: "primary" },
  approved: { label: "已通过", type: "success" },
  rejected: { label: "已驳回", type: "danger" },
  transferred: { label: "已转办", type: "warning" },
  expired: { label: "已过期", type: "info" },
};

const recordTitle = computed(() => {
  return props.task.record?.title || `记录 ${props.task.record?.id || ""}`;
});

const recordFields = computed(() => {
  const values = props.task.record?.values || {};
  return Object.entries(values).map(([key, value]) => ({
    key,
    value:
      value === null || value === undefined
        ? "-"
        : typeof value === "object"
          ? JSON.stringify(value)
          : String(value),
  }));
});

const creatorName = computed(() => {
  const createdBy = props.task.record?.created_by;
  if (typeof createdBy === "object" && createdBy) {
    return createdBy.name || createdBy.id || "未知";
  }
  return createdBy || "未知";
});

const createdAt = computed(() => {
  return props.task.record?.created_at
    ? formatDateTime(props.task.record.created_at)
    : "-";
});

const nodeName = computed(() => {
  return props.task.node?.name || "未知节点";
});

const workflowName = computed(() => {
  return props.task.workflow?.name || "未知工作流";
});

const startedAt = computed(() => {
  return props.task.instance?.started_at
    ? formatDateTime(props.task.instance.started_at)
    : "-";
});

const assigneeName = computed(() => {
  return props.task.assignee?.name || props.task.assignee_id || "未分配";
});

function handleClose() {
  dialogVisible.value = false;
}

function resetForm() {
  comment.value = "";
  newAssigneeIds.value = [];
  currentAction.value = null;
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetForm();
    }
  }
);

async function fetchUserNames(userIds: string[]) {
  if (userIds.length > 0) {
    await userCacheStore.fetchUsers(userIds);
  }
}

async function loadHistoryUsers() {
  const ids: string[] = [];
  if (props.task.assignee_id) ids.push(props.task.assignee_id);
  if (props.task.transferred_from_id) ids.push(props.task.transferred_from_id);
  const createdBy = props.task.record?.created_by;
  if (typeof createdBy === "string" && createdBy) ids.push(createdBy);
  await fetchUserNames(ids);
}

watch(
  () => props.task,
  () => {
    loadHistoryUsers();
  },
  { immediate: true }
);

function resolveUserName(userIdOrUser: string | { id: string; name?: string } | null | undefined) {
  if (!userIdOrUser) return "未知";
  if (typeof userIdOrUser === "object") {
    return userIdOrUser.name || userIdOrUser.id;
  }
  const cached = userCacheStore.getCachedUser(userIdOrUser);
  return cached?.name || userIdOrUser;
}

async function handleAction(action: ActionType) {
  if (!comment.value.trim()) {
    ElMessage.warning("请输入审批意见");
    return;
  }

  if (action === "transfer" && newAssigneeIds.value.length === 0) {
    if (currentAction.value !== "transfer") {
      currentAction.value = "transfer";
      return;
    }
    ElMessage.warning("请选择转办对象");
    return;
  }

  if (action === "transfer") {
    currentAction.value = "transfer";
  }

  actionLoading.value = true;
  currentAction.value = action;

  try {
    if (action === "approve") {
      await workflowStore.approveTask(props.task.id, comment.value);
    } else if (action === "reject") {
      await workflowStore.rejectTask(props.task.id, comment.value);
    } else if (action === "transfer") {
      await workflowStore.transferTask(
        props.task.id,
        newAssigneeIds.value[0],
        comment.value
      );
    }
    ElMessage.success("操作成功");
    emit("success");
    handleClose();
  } catch (error) {
    console.error("[ApprovalDetailDialog] 审批操作失败:", error);
  } finally {
    actionLoading.value = false;
    currentAction.value = null;
  }
}

async function loadApprovalHistory() {
  if (!props.task.record?.id) {
    ElMessage.warning("暂无关联记录");
    return;
  }
  historyVisible.value = true;
}

const historyPreview = computed(() => {
  const items: {
    id: string;
    status: TaskStatus;
    title: string;
    comment?: string | null;
    time?: string | null;
  }[] = [];

  items.push({
    id: `${props.task.id}-current`,
    status: props.task.status,
    title: `${nodeName.value} · ${resolveUserName(props.task.assignee_id)}`,
    comment: props.task.comment,
    time: props.task.acted_at,
  });

  return items;
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="审批详情"
    width="680px"
    :close-on-click-modal="false"
    destroy-on-close
    @closed="resetForm">
    <div v-loading="actionLoading" class="approval-detail">
      <!-- 记录信息 -->
      <div class="detail-section">
        <div class="section-header">
          <h3 class="section-title">{{ recordTitle }}</h3>
          <el-tag :type="statusMap[task.status].type" effect="light">
            {{ statusMap[task.status].label }}
          </el-tag>
        </div>

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="工作流">
            {{ workflowName }}
          </el-descriptions-item>
          <el-descriptions-item label="审批节点">
            {{ nodeName }}
          </el-descriptions-item>
          <el-descriptions-item label="发起人">
            {{ creatorName }}
          </el-descriptions-item>
          <el-descriptions-item label="发起时间">
            {{ createdAt }}
          </el-descriptions-item>
          <el-descriptions-item label="当前审批人">
            {{ assigneeName }}
          </el-descriptions-item>
          <el-descriptions-item label="实例启动时间">
            {{ startedAt }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 字段值 -->
      <div class="detail-section">
        <h4 class="subsection-title">记录字段</h4>
        <div class="field-list">
          <div
            v-for="field in recordFields"
            :key="field.key"
            class="field-item">
            <span class="field-label">{{ field.key }}</span>
            <span class="field-value">{{ field.value }}</span>
          </div>
          <el-empty
            v-if="recordFields.length === 0"
            description="暂无字段数据"
            :image-size="60" />
        </div>
      </div>

      <!-- 审批历史 -->
      <div class="detail-section">
        <div class="section-header">
          <h4 class="subsection-title">审批历史</h4>
          <el-button link type="primary" @click="loadApprovalHistory">
            查看完整历史
          </el-button>
        </div>
        <el-timeline>
          <el-timeline-item
            v-for="item in historyPreview"
            :key="item.id"
            :type="statusMap[item.status].type"
            :timestamp="item.time ? formatDateTime(item.time) : '进行中'">
            <div class="timeline-title">{{ item.title }}</div>
            <div v-if="item.comment" class="timeline-comment">
              {{ item.comment }}
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- 操作区 -->
      <div v-if="isPending" class="detail-section action-section">
        <h4 class="subsection-title">审批意见</h4>
        <el-input
          v-model="comment"
          type="textarea"
          :rows="3"
          placeholder="请输入审批意见（必填）" />

        <div v-if="currentAction === 'transfer'" class="transfer-row">
          <span class="transfer-label">转办给</span>
          <MemberSelect
            v-model="newAssigneeIds"
            placeholder="选择新审批人"
            :allow-multiple="false" />
        </div>

        <div class="action-buttons">
          <el-button
            type="success"
            :loading="actionLoading && currentAction === 'approve'"
            @click="handleAction('approve')">
            同意
          </el-button>
          <el-button
            type="danger"
            :loading="actionLoading && currentAction === 'reject'"
            @click="handleAction('reject')">
            驳回
          </el-button>
          <el-button
            type="warning"
            :loading="actionLoading && currentAction === 'transfer'"
            @click="handleAction('transfer')">
            转办
          </el-button>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>

    <ApprovalHistoryDrawer
      v-model:visible="historyVisible"
      :record-id="task.record?.id || ''" />
  </el-dialog>
</template>

<style lang="scss" scoped>
.approval-detail {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

.detail-section {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
}

.section-title {
  margin: 0;
  font-size: $font-size-lg;
  font-weight: 600;
  color: $text-primary;
}

.subsection-title {
  margin: 0 0 12px;
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
}

.field-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background-color: $gray-50;
  border-radius: $border-radius-md;
  border: 1px solid $border-color;
}

.field-label {
  font-size: $font-size-xs;
  color: $text-secondary;
  font-weight: 500;
}

.field-value {
  font-size: $font-size-sm;
  color: $text-primary;
  word-break: break-all;
}

.timeline-title {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
}

.timeline-comment {
  margin-top: 4px;
  font-size: $font-size-sm;
  color: $text-secondary;
}

.action-section {
  padding-top: 16px;
  border-top: 1px solid $border-color;
}

.transfer-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;

  .transfer-label {
    flex-shrink: 0;
    font-size: $font-size-sm;
    color: $text-secondary;
  }

  .member-select {
    flex: 1;
  }
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
</style>
