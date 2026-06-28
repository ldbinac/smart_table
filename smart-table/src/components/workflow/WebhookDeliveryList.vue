<script setup lang="ts">
import { reactive, ref, watch, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { apiClient } from "@/api/client";
import type { PaginatedData } from "@/api/types";
import { formatDateTime } from "@/utils/timezone";
import type { WebhookDeliveryLog, WebhookDeliveryStatus } from "@/types/workflow";

interface Props {
  webhookId: string;
}

const props = defineProps<Props>();

const loading = ref(false);
const redeliveringId = ref<string | null>(null);
const deliveries = ref<WebhookDeliveryLog[]>([]);

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0,
});

interface DeliveryListResponse {
  data?: WebhookDeliveryLog[];
  meta?: {
    pagination?: PaginatedData<WebhookDeliveryLog>;
  };
}

const fetchDeliveries = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get<DeliveryListResponse>(
      `/webhooks/${props.webhookId}/deliveries`,
      {
        page: pagination.page,
        per_page: pagination.per_page,
      },
    );

    const items =
      response.meta?.pagination?.items ?? response.data ?? [];
    deliveries.value = items;
    pagination.total = response.meta?.pagination?.total ?? items.length;
  } catch (error) {
    console.error("获取 Webhook 投递日志失败:", error);
    ElMessage.error("获取 Webhook 投递日志失败");
  } finally {
    loading.value = false;
  }
};

const handleRedeliver = async (row: WebhookDeliveryLog) => {
  redeliveringId.value = row.id;
  try {
    await apiClient.post(`/webhooks/deliveries/${row.id}/redeliver`, {});
    ElMessage.success("重新投递请求已发送");
    await fetchDeliveries();
  } catch (error) {
    console.error("重新投递失败:", error);
    ElMessage.error("重新投递失败");
  } finally {
    redeliveringId.value = null;
  }
};

const handleSizeChange = (size: number) => {
  pagination.per_page = size;
  pagination.page = 1;
  fetchDeliveries();
};

const handlePageChange = (page: number) => {
  pagination.page = page;
  fetchDeliveries();
};

const formatDate = (date: string | null | undefined) => {
  if (!date) return "-";
  return formatDateTime(date, "YYYY-MM-DD HH:mm:ss");
};

const getStatusType = (status: WebhookDeliveryStatus) => {
  const typeMap: Record<WebhookDeliveryStatus, string> = {
    pending: "info",
    success: "success",
    failed: "danger",
  };
  return typeMap[status] || "info";
};

const getStatusText = (status: WebhookDeliveryStatus) => {
  const textMap: Record<WebhookDeliveryStatus, string> = {
    pending: "待投递",
    success: "成功",
    failed: "失败",
  };
  return textMap[status] || status;
};

watch(
  () => props.webhookId,
  () => {
    pagination.page = 1;
    fetchDeliveries();
  },
);

onMounted(() => {
  fetchDeliveries();
});

defineExpose({ fetchDeliveries });
</script>

<template>
  <div class="webhook-delivery-list">
    <el-table v-loading="loading" :data="deliveries" stripe style="width: 100%">
      <el-table-column prop="created_at" label="创建时间" min-width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column
        prop="response_status"
        label="响应状态码"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          {{ row.response_status ?? "-" }}
        </template>
      </el-table-column>

      <el-table-column
        prop="retry_count"
        label="重试次数"
        width="100"
        align="center"
      />

      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'failed'"
            link
            type="primary"
            :loading="redeliveringId === row.id"
            @click="handleRedeliver(row)"
          >
            重新投递
          </el-button>
        </template>
      </el-table-column>

      <el-table-column type="expand" width="30">
        <template #default="{ row }">
          <div class="delivery-detail">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="请求体">
                <pre>{{ row.payload ?? "-" }}</pre>
              </el-descriptions-item>
              <el-descriptions-item label="响应体">
                <pre>{{ row.response_body ?? "-" }}</pre>
              </el-descriptions-item>
              <el-descriptions-item
                v-if="row.error_message"
                label="错误信息"
              >
                <span style="color: #f56c6c">{{ row.error_message }}</span>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.per_page"
        :page-sizes="[10, 20, 50]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.webhook-delivery-list {
  width: 100%;
}

.delivery-detail {
  padding: $spacing-md;

  pre {
    max-height: 300px;
    overflow: auto;
    background-color: #f5f7fa;
    padding: $spacing-sm;
    border-radius: 4px;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
  }
}

.pagination-container {
  margin-top: $spacing-lg;
  display: flex;
  justify-content: flex-end;
}
</style>
