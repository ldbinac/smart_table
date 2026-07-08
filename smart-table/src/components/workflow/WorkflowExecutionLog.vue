<script setup lang="ts">
import { computed } from "vue";
import type {
  WorkflowInstance,
  WorkflowExecutionLog,
  WorkflowNodeType,
} from "@/types/workflow";
import { formatDateTime } from "@/utils/timezone";
import {
  CircleCheck,
  CircleClose,
  Timer,
  Remove,
} from "@element-plus/icons-vue";

interface Props {
  instance: WorkflowInstance;
  logs: WorkflowExecutionLog[];
}

const props = defineProps<Props>();

const sortedLogs = computed(() => {
  return [...props.logs].sort(
    (a, b) =>
      new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
  );
});

const nodeTypeLabels: Record<WorkflowNodeType | string, string> = {
  trigger: "触发器",
  approval: "审批节点",
  action: "动作节点",
  condition: "条件节点",
  update_record: "更新记录",
  create_record: "创建记录",
  send_email: "发送邮件",
  webhook: "Webhook",
};

function getNodeTypeLabel(nodeType: WorkflowNodeType | string | null | undefined): string {
  if (!nodeType) return "未知节点";
  return nodeTypeLabels[nodeType] ?? nodeType;
}

function getStatusType(
  status: string,
): "success" | "danger" | "warning" | "info" {
  const lower = status.toLowerCase();
  if (lower === "completed" || lower === "success") return "success";
  if (lower === "error" || lower === "failed" || lower === "rejected") {
    return "danger";
  }
  if (lower === "running" || lower === "pending") return "warning";
  return "info";
}

function getStatusIcon(status: string) {
  const lower = status.toLowerCase();
  if (lower === "completed" || lower === "success") return CircleCheck;
  if (lower === "error" || lower === "failed" || lower === "rejected") {
    return CircleClose;
  }
  if (lower === "running" || lower === "pending") return Timer;
  return Remove;
}

function formatTime(time: string | null | undefined): string {
  if (!time) return "-";
  return formatDateTime(time);
}

function formatDuration(
  startedAt: string,
  completedAt?: string | null,
): string {
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const diff = end - start;
  if (diff < 1000) return `${diff}ms`;
  if (diff < 60000) return `${Math.round(diff / 1000)}s`;
  return `${Math.round(diff / 60000)}m ${Math.round((diff % 60000) / 1000)}s`;
}

function formatContext(context: Record<string, unknown> | null | undefined): string {
  if (!context) return "{}";
  try {
    return JSON.stringify(context, null, 2);
  } catch {
    return String(context);
  }
}
</script>

<template>
  <div class="workflow-execution-log">
    <div class="instance-summary">
      <div class="summary-item">
        <span class="summary-label">实例状态</span>
        <el-tag :type="getStatusType(instance.status)">
          {{ instance.status }}
        </el-tag>
      </div>
      <div class="summary-item">
        <span class="summary-label">触发方式</span>
        <span>{{ instance.trigger_type }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">开始时间</span>
        <span>{{ formatTime(instance.started_at) }}</span>
      </div>
      <div v-if="instance.completed_at" class="summary-item">
        <span class="summary-label">结束时间</span>
        <span>{{ formatTime(instance.completed_at) }}</span>
      </div>
    </div>

    <el-divider />

    <el-timeline>
      <el-timeline-item
        v-for="log in sortedLogs"
        :key="log.id"
        :type="getStatusType(log.status)">
        <div class="log-card">
          <div class="log-header">
            <div class="log-title">
              <el-icon class="status-icon">
                <component :is="getStatusIcon(log.status)" />
              </el-icon>
              <span class="node-type">{{ getNodeTypeLabel(log.node_type) }}</span>
              <el-tag size="small" :type="getStatusType(log.status)">
                {{ log.status }}
              </el-tag>
            </div>
            <div class="log-time">
              {{ formatTime(log.started_at) }}
            </div>
          </div>

          <div class="log-meta">
            <span class="meta-item">耗时：{{ formatDuration(log.started_at, log.completed_at) }}</span>
            <span v-if="log.completed_at" class="meta-item">
              结束：{{ formatTime(log.completed_at) }}
            </span>
          </div>

          <el-alert
            v-if="log.error_message"
            :title="log.error_message"
            type="error"
            :closable="false"
            show-icon
            class="error-alert" />

          <el-collapse class="context-collapse">
            <el-collapse-item title="输入上下文">
              <pre class="context-pre">{{ formatContext(log.input_context) }}</pre>
            </el-collapse-item>
            <el-collapse-item title="输出结果">
              <pre class="context-pre">{{ formatContext(log.output_result) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-timeline-item>
    </el-timeline>

    <el-empty v-if="sortedLogs.length === 0" description="暂无执行日志" />
  </div>
</template>

<style lang="scss" scoped>
.workflow-execution-log {
  padding: $spacing-md;
}

.instance-summary {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-md;
  margin-bottom: $spacing-sm;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-size-sm;
  color: $text-secondary;
}

.summary-label {
  color: $text-primary;
  font-weight: 500;
}

.log-card {
  background-color: $bg-color;
  border-radius: $border-radius-md;
  padding: $spacing-md;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-sm;
}

.log-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.status-icon {
  font-size: 18px;
}

.node-type {
  font-weight: 600;
  color: $text-primary;
}

.log-time {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.log-meta {
  display: flex;
  gap: $spacing-md;
  margin-bottom: $spacing-sm;
  font-size: $font-size-sm;
  color: $text-secondary;
}

.error-alert {
  margin-bottom: $spacing-sm;
}

.context-collapse {
  :deep(.el-collapse-item__header) {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.context-pre {
  margin: 0;
  padding: $spacing-sm;
  background-color: #1e1e1e;
  color: #d4d4d4;
  border-radius: $border-radius-sm;
  font-size: 12px;
  overflow-x: auto;
  max-height: 240px;
}
</style>
