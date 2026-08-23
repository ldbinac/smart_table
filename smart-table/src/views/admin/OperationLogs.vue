<template>
  <div class="operation-logs-page">
    <div class="page-header">
      <h1 class="page-title">{{ t('logs.title') }}</h1>
      <el-button type="success" @click="handleExport">
        <el-icon><Download /></el-icon>
        {{ t('logs.export') }}
      </el-button>
    </div>

    <div class="page-content">
      <el-card>
        <div class="filter-bar">
          <div class="filter-row">
            <el-input
              v-model="filters.user_id"
              :placeholder="t('logs.userIdPlaceholder')"
              clearable
              style="width: 200px"
              @clear="handleFilter" />

            <el-select
              v-model="filters.action"
              :placeholder="t('logs.action')"
              clearable
              style="width: 150px; margin-left: 12px"
              @change="handleFilter">
              <el-option :label="t('logs.create')" value="create" />
              <el-option :label="t('logs.update')" value="update" />
              <el-option :label="t('logs.delete')" value="delete" />
              <el-option :label="t('logs.suspend')" value="suspend" />
              <el-option :label="t('logs.activate')" value="activate" />
              <el-option :label="t('logs.resetPassword')" value="reset_password" />
            </el-select>

            <el-select
              v-model="filters.entity_type"
              :placeholder="t('logs.target')"
              clearable
              style="width: 150px; margin-left: 12px"
              @change="handleFilter">
              <el-option :label="t('logs.entityUser')" value="user" />
              <el-option :label="t('logs.entityConfig')" value="config" />
              <el-option :label="t('logs.entityBase')" value="base" />
              <el-option :label="t('logs.entityTable')" value="table" />
              <el-option :label="t('logs.entityField')" value="field" />
              <el-option :label="t('logs.entityRecord')" value="record" />
            </el-select>

            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="~"
              :start-placeholder="t('logs.startDate')"
              :end-placeholder="t('logs.endDate')"
              style="margin-left: 12px"
              @change="handleFilter" />
          </div>
        </div>

        <div class="table-container">
          <el-table
            v-loading="loading"
            :data="logs"
            style="width: 100%"
            :default-sort="{ prop: 'created_at', order: 'descending' }"
            max-height="600px">
            <el-table-column prop="user_id" :label="t('logs.userId')" width="280" />
            <el-table-column prop="action" :label="t('logs.action')" width="120">
              <template #default="{ row }">
                <el-tag :type="getActionTagType(row.action)">
                  {{ getActionLabel(row.action) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="entity_type" :label="t('logs.target')" width="100">
              <template #default="{ row }">
                {{ getEntityTypeLabel(row.entity_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="entity_id" :label="t('logs.entityId')" width="280" />
            <el-table-column prop="ip_address" :label="t('logs.ip')" width="150" />
            <el-table-column
              prop="created_at"
              :label="t('logs.time')"
              width="180"
              sortable>
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('logs.actions')" width="100" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="showDetail(row)">
                  {{ t('logs.detail') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange" />
        </div>
      </el-card>
    </div>

    <!-- 日志详情对话框 -->
    <el-dialog v-model="detailVisible" :title="t('logs.detailTitle')" width="800px" append-to-body>
      <el-descriptions :column="2" border v-if="selectedLog">
        <el-descriptions-item :label="t('logs.userId')">{{
          selectedLog.user_id
        }}</el-descriptions-item>
        <el-descriptions-item :label="t('logs.action')">
          <el-tag :type="getActionTagType(selectedLog.action)">
            {{ getActionLabel(selectedLog.action) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="t('logs.target')">
          {{ getEntityTypeLabel(selectedLog.entity_type) }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('logs.entityId')">{{
          selectedLog.entity_id
        }}</el-descriptions-item>
        <el-descriptions-item :label="t('logs.ip')">{{
          selectedLog.ip_address
        }}</el-descriptions-item>
        <el-descriptions-item :label="t('logs.time')">
          {{ formatDate(selectedLog.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="User Agent" :span="2">
          {{ selectedLog.user_agent }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('logs.oldValue')" :span="2">
          <pre v-if="selectedLog.old_value" class="json-viewer">{{
            JSON.stringify(selectedLog.old_value, null, 2)
          }}</pre>
          <span v-else class="text-muted">{{ t('logs.none') }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="t('logs.newValue')" :span="2">
          <pre v-if="selectedLog.new_value" class="json-viewer">{{
            JSON.stringify(selectedLog.new_value, null, 2)
          }}</pre>
          <span v-else class="text-muted">{{ t('logs.none') }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { Download } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useAdminStore } from "@/stores/adminStore";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const adminStore = useAdminStore();

const logs = computed(() => adminStore.operationLogs);
const loading = computed(() => adminStore.logLoading);
const logPagination = computed(() => adminStore.logPagination);

const currentPage = ref(1);
const pageSize = ref(10);
const total = computed(() => logPagination.value.total);

const detailVisible = ref(false);
const selectedLog = ref<any>(null);

const filters = reactive({
  user_id: "",
  action: "",
  entity_type: "",
  start_date: "",
  end_date: "",
});

const dateRange = ref<[Date, Date] | null>(null);

const actionLabelMap: Record<string, string> = {
  create: t("logs.create"),
  update: t("logs.update"),
  delete: t("logs.delete"),
  suspend: t("logs.suspend"),
  activate: t("logs.activate"),
  reset_password: t("logs.resetPassword"),
};

const getActionLabel = (action: string): string => {
  return actionLabelMap[action] || action;
};

const getActionTagType = (
  action: string,
): "success" | "warning" | "info" | "danger" | undefined => {
  const typeMap: Record<
    string,
    "success" | "warning" | "info" | "danger" | undefined
  > = {
    create: "success",
    update: "warning",
    delete: "danger",
    suspend: "warning",
    activate: "success",
    reset_password: "info",
  };
  return typeMap[action] || undefined;
};

const getEntityTypeLabel = (entityType: string): string => {
  const typeMap: Record<string, string> = {
    user: t("logs.entityUser"),
    config: t("logs.entityConfig"),
    base: t("logs.entityBase"),
    table: t("logs.entityTable"),
    field: t("logs.entityField"),
    record: t("logs.entityRecord"),
    view: t("logs.entityView"),
    dashboard: t("logs.entityDashboard"),
  };
  return typeMap[entityType] || entityType;
};

import { formatDateTime } from "@/utils/timezone";

const formatDate = (dateString: string): string => {
  if (!dateString) return "";
  return formatDateTime(dateString, "YYYY-MM-DD HH:mm:ss");
};

const fetchLogs = async () => {
  try {
    await adminStore.fetchOperationLogs({
      page: currentPage.value,
      pageSize: pageSize.value,
      ...filters,
    });
  } catch (error) {
    ElMessage.error(t("logs.fetchFailed"));
  }
};

const handleFilter = () => {
  if (dateRange.value && dateRange.value.length === 2) {
    filters.start_date = dateRange.value[0].toISOString();
    filters.end_date = dateRange.value[1].toISOString();
  } else {
    filters.start_date = "";
    filters.end_date = "";
  }
  currentPage.value = 1;
  fetchLogs();
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchLogs();
};

const handlePageChange = (page: number) => {
  currentPage.value = page;
  fetchLogs();
};

const showDetail = (log: any) => {
  selectedLog.value = log;
  detailVisible.value = true;
};

const handleExport = async () => {
  try {
    await adminStore.exportOperationLogs({
      ...filters,
    });
    ElMessage.success(t('admin.logExportSuccess'));
  } catch (error) {
    ElMessage.error(t('admin.logExportFailed'));
  }
};

onMounted(() => {
  fetchLogs();
});
</script>

<style scoped lang="scss">
.operation-logs-page {
  padding: 24px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0;
    }
  }

  .page-content {
    .el-card {
      border-radius: 8px;
    }

    .filter-bar {
      .filter-row {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
      }
    }

    .pagination-container {
      display: flex;
      justify-content: flex-end;
      margin-top: 24px;
    }

    .table-container {
      max-height: 600px;
      overflow-y: auto;

      &::-webkit-scrollbar {
        width: 8px;
      }

      &::-webkit-scrollbar-thumb {
        background-color: #c0c4cc;
        border-radius: 4px;

        &:hover {
          background-color: #909399;
        }
      }

      &::-webkit-scrollbar-track {
        background-color: #f5f7fa;
      }
    }
  }

  .json-viewer {
    background-color: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
    max-height: 300px;
    overflow-y: auto;
    font-family: "Courier New", monospace;
    font-size: 12px;
    margin: 0;
  }

  .text-muted {
    color: #909399;
  }
}
</style>
