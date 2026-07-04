<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import { workflowApiService } from "@/services/api/workflowApiService";
import { useUserCacheStore } from "@/stores/userCacheStore";
import { formatDateTime } from "@/utils/timezone";
import type { ApprovalTask } from "./types";
import type { TaskStatus } from "@/types/workflow";

const props = defineProps<{
  recordId: string;
  visible: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const userCacheStore = useUserCacheStore();

const tasks = ref<ApprovalTask[]>([]);
const loading = ref(false);

const drawerVisible = computed({
  get: () => props.visible,
  set: (value) => emit("update:visible", value),
});

const statusMap: Record<TaskStatus, { label: string; type: "success" | "danger" | "warning" | "info" | "primary" }> = {
  pending: { label: "待审批", type: "primary" },
  approved: { label: "已通过", type: "success" },
  rejected: { label: "已驳回", type: "danger" },
  transferred: { label: "已转办", type: "warning" },
  expired: { label: "已过期", type: "info" },
};

async function loadHistory() {
  if (!props.recordId) return;

  loading.value = true;
  try {
    const data = await workflowApiService.getRecordApprovalHistory(props.recordId);
    tasks.value = (data as ApprovalTask[]).sort((a, b) => {
      const timeA = a.acted_at || a.instance?.started_at || "";
      const timeB = b.acted_at || b.instance?.started_at || "";
      return new Date(timeB).getTime() - new Date(timeA).getTime();
    });
    await loadUserNames();
  } catch (error) {
    console.error("[ApprovalHistoryDrawer] 加载审批历史失败:", error);
    ElMessage.error("加载审批历史失败");
  } finally {
    loading.value = false;
  }
}

async function loadUserNames() {
  const ids = new Set<string>();
  tasks.value.forEach((task) => {
    if (task.assignee_id) ids.add(task.assignee_id);
    if (task.transferred_from_id) ids.add(task.transferred_from_id);
    const createdBy = task.record?.created_by;
    if (typeof createdBy === "string" && createdBy) ids.add(createdBy);
    if (task.actor?.id) ids.add(task.actor.id);
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

function getTimelineTitle(task: ApprovalTask): string {
  const nodeName = task.node?.name || "审批节点";
  const operator = resolveUserName(task.actor || task.assignee_id);
  return `${nodeName} · ${operator}`;
}

function getTimelineContent(task: ApprovalTask): string {
  const parts: string[] = [];
  if (task.comment) {
    parts.push(task.comment);
  }
  if (task.transferred_from_id) {
    parts.push(`来自 ${resolveUserName(task.transferred_from_id)} 的转办`);
  }
  return parts.join(" · ");
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      loadHistory();
    }
  },
  { immediate: true }
);

function handleClose() {
  drawerVisible.value = false;
}
</script>

<template>
  <el-drawer
    v-model="drawerVisible"
    title="审批历史"
    direction="rtl"
    size="420px"
    destroy-on-close
    :close-on-click-modal="true">
    <div v-loading="loading" class="approval-history">
      <el-empty
        v-if="!loading && tasks.length === 0"
        description="暂无审批记录"
        :image-size="80" />

      <el-timeline v-else>
        <el-timeline-item
          v-for="task in tasks"
          :key="task.id"
          :type="statusMap[task.status].type"
          :timestamp="
            task.acted_at
              ? formatDateTime(task.acted_at)
              : task.instance?.started_at
                ? formatDateTime(task.instance.started_at)
                : '-'
          ">
          <div class="history-card">
            <div class="history-header">
              <span class="history-title">{{ getTimelineTitle(task) }}</span>
              <el-tag :type="statusMap[task.status].type" size="small" effect="light">
                {{ statusMap[task.status].label }}
              </el-tag>
            </div>
            <div v-if="getTimelineContent(task)" class="history-content">
              {{ getTimelineContent(task) }}
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-drawer>
</template>

<style lang="scss" scoped>
.approval-history {
  padding: 8px;
}

.history-card {
  padding: 12px;
  background-color: $gray-50;
  border-radius: $border-radius-md;
  border: 1px solid $border-color;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.history-title {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
}

.history-content {
  font-size: $font-size-sm;
  color: $text-secondary;
  word-break: break-all;
  line-height: 1.5;
}
</style>
