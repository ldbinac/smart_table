<script setup lang="ts">
import { computed, ref } from "vue";
import type {
  WorkflowInstance,
  WorkflowExecutionLog as ExecutionLog,
  WebhookDeliveryLog,
} from "@/types/workflow";
import { formatDateTime } from "@/utils/timezone";
import { getNodeLabel } from "@/utils/workflowNodeType";
import { getInstanceWebhookDeliveries } from "@/services/api/workflowApiService";
import {
  CircleCheck,
  CircleClose,
  Timer,
  Remove,
  Loading,
  Document,
} from "@element-plus/icons-vue";

interface Props {
  instance: WorkflowInstance;
  logs: ExecutionLog[];
  workflowId: string;
}

const props = defineProps<Props>();

const allWebhookDeliveries = ref<WebhookDeliveryLog[] | null>(null);
const loadingAllDeliveries = ref(false);
const showAllDeliveriesDialog = ref(false);

const sortedLogs = computed(() => {
  return [...props.logs].sort(
    (a, b) =>
      new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
  );
});

function getNodeTypeLabel(nodeType: string | null | undefined): string {
  if (!nodeType) return "未知节点";
  return getNodeLabel(nodeType);
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

function isWebhookNode(nodeType: string | null | undefined): boolean {
  return nodeType === 'trigger_webhook' || nodeType === 'webhook';
}

async function loadAllWebhookDeliveries(): Promise<void> {
  if (allWebhookDeliveries.value !== null || loadingAllDeliveries.value) {
    return;
  }

  loadingAllDeliveries.value = true;
  try {
    const deliveries = await getInstanceWebhookDeliveries(
      props.workflowId,
      props.instance.id,
    );
    allWebhookDeliveries.value = deliveries;
  } catch (error) {
    console.error('加载 Webhook 投递日志失败:', error);
    allWebhookDeliveries.value = [];
  } finally {
    loadingAllDeliveries.value = false;
  }
}

async function openAllDeliveriesDialog(): Promise<void> {
  showAllDeliveriesDialog.value = true;
  await loadAllWebhookDeliveries();
}

function getDeliveriesForLog(log: ExecutionLog): WebhookDeliveryLog[] {
  if (!allWebhookDeliveries.value) return [];

  const logStarted = new Date(log.started_at).getTime();
  const logCompleted = log.completed_at ? new Date(log.completed_at).getTime() : Date.now();

  return allWebhookDeliveries.value.filter((delivery) => {
    const deliveryTime = new Date(delivery.created_at).getTime();
    return deliveryTime >= logStarted && deliveryTime <= logCompleted;
  });
}

async function ensureDeliveriesLoaded(): Promise<void> {
  await loadAllWebhookDeliveries();
}

function getDeliveryStatusType(status: string): "success" | "danger" | "warning" | "info" {
  const lower = status.toLowerCase();
  if (lower === 'success') return 'success';
  if (lower === 'failed' || lower === 'error') return 'danger';
  if (lower === 'pending' || lower === 'retrying') return 'warning';
  return 'info';
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
      <div class="summary-item">
        <el-button
          size="small"
          :icon="Document"
          @click="openAllDeliveriesDialog"
          :loading="loadingAllDeliveries"
        >
          查看 Webhook 投递日志
        </el-button>
      </div>
    </div>

    <el-dialog
      v-model="showAllDeliveriesDialog"
      title="全部 Webhook 投递日志"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="loadingAllDeliveries" class="dialog-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="!allWebhookDeliveries || allWebhookDeliveries.length === 0" class="dialog-empty">
        暂无投递记录
      </div>
      <div v-else class="all-deliveries-list">
        <div
          v-for="delivery in allWebhookDeliveries"
          :key="delivery.id"
          class="delivery-item"
        >
          <div class="delivery-header">
            <el-tag size="small" :type="getDeliveryStatusType(delivery.status)">
              {{ delivery.status }}
            </el-tag>
            <span class="delivery-time">{{ formatTime(delivery.created_at) }}</span>
          </div>
          <div class="delivery-detail">
            <div v-if="delivery.payload" class="detail-row">
              <span class="detail-label">请求体:</span>
              <pre class="detail-value payload-pre">{{ delivery.payload }}</pre>
            </div>
            <div v-if="delivery.response_status" class="detail-row">
              <span class="detail-label">响应状态:</span>
              <span class="detail-value">{{ delivery.response_status }}</span>
            </div>
            <div v-if="delivery.delivered_at" class="detail-row">
              <span class="detail-label">投递时间:</span>
              <span class="detail-value">{{ formatTime(delivery.delivered_at) }}</span>
            </div>
            <div v-if="delivery.retry_count > 0" class="detail-row">
              <span class="detail-label">重试次数:</span>
              <span class="detail-value">{{ delivery.retry_count }}</span>
            </div>
          </div>
          <el-collapse v-if="delivery.response_body" class="response-collapse">
            <el-collapse-item title="响应内容">
              <pre class="response-pre">{{ delivery.response_body }}</pre>
            </el-collapse-item>
          </el-collapse>
          <el-alert
            v-if="delivery.error_message"
            :title="delivery.error_message"
            type="error"
            :closable="false"
            show-icon
            class="delivery-error"
          />
        </div>
      </div>
    </el-dialog>

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
              <span
                v-if="log.node_name"
                class="node-name"
                :title="log.node_name"
              >{{ log.node_name }}</span>
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
            <el-collapse-item
              v-if="isWebhookNode(log.node_type)"
              title="Webhook 投递详情"
              @click="ensureDeliveriesLoaded"
            >
              <div v-if="loadingAllDeliveries" class="delivery-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>加载中...</span>
              </div>
              <div v-else-if="getDeliveriesForLog(log).length === 0" class="delivery-empty">
                暂无投递记录
              </div>
              <div v-else class="delivery-list">
                <div
                  v-for="delivery in getDeliveriesForLog(log)"
                  :key="delivery.id"
                  class="delivery-item"
                >
                  <div class="delivery-header">
                    <el-tag size="small" :type="getDeliveryStatusType(delivery.status)">
                      {{ delivery.status }}
                    </el-tag>
                    <span class="delivery-time">{{ formatTime(delivery.created_at) }}</span>
                  </div>
                  <div class="delivery-detail">
                    <div v-if="delivery.payload" class="detail-row">
                      <span class="detail-label">请求体:</span>
                      <pre class="detail-value payload-pre">{{ delivery.payload }}</pre>
                    </div>
                    <div v-if="delivery.response_status" class="detail-row">
                      <span class="detail-label">响应状态:</span>
                      <span class="detail-value">{{ delivery.response_status }}</span>
                    </div>
                    <div v-if="delivery.delivered_at" class="detail-row">
                      <span class="detail-label">投递时间:</span>
                      <span class="detail-value">{{ formatTime(delivery.delivered_at) }}</span>
                    </div>
                    <div v-if="delivery.retry_count > 0" class="detail-row">
                      <span class="detail-label">重试次数:</span>
                      <span class="detail-value">{{ delivery.retry_count }}</span>
                    </div>
                  </div>
                  <el-collapse v-if="delivery.response_body" class="response-collapse">
                    <el-collapse-item title="响应内容">
                      <pre class="response-pre">{{ delivery.response_body }}</pre>
                    </el-collapse-item>
                  </el-collapse>
                  <el-alert
                    v-if="delivery.error_message"
                    :title="delivery.error_message"
                    type="error"
                    :closable="false"
                    show-icon
                    class="delivery-error"
                  />
                </div>
              </div>
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

.node-name {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: $font-size-sm;
  color: $text-secondary;
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

.delivery-loading {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-md;
  color: $text-secondary;
}

.delivery-empty {
  padding: $spacing-md;
  text-align: center;
  color: $text-secondary;
}

.delivery-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.delivery-item {
  padding: $spacing-sm;
  background-color: rgba($color: #000000, $alpha: 0.02);
  border-radius: $border-radius-sm;
  border: 1px solid $border-color;
}

.delivery-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-xs;
}

.delivery-time {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.delivery-detail {
  font-size: $font-size-sm;
}

.detail-row {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-xs;
}

.detail-label {
  color: $text-secondary;
  min-width: 80px;
}

.detail-value {
  color: $text-primary;
  word-break: break-all;
}

.payload-pre {
  margin: 0;
  padding: $spacing-sm;
  background-color: #1e1e1e;
  color: #d4d4d4;
  border-radius: $border-radius-sm;
  font-size: 12px;
  overflow-x: auto;
  max-height: 150px;
  flex: 1;
}

.response-collapse {
  margin-top: $spacing-xs;
}

.response-pre {
  margin: 0;
  padding: $spacing-sm;
  background-color: #1e1e1e;
  color: #d4d4d4;
  border-radius: $border-radius-sm;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
}

.delivery-error {
  margin-top: $spacing-xs;
}

.dialog-loading,
.dialog-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  padding: $spacing-xl;
  color: $text-secondary;
}

.all-deliveries-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
