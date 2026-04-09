<template>
  <div class="operation-logs-page">
    <div class="page-header">
      <h1 class="page-title">操作日志</h1>
      <el-button type="success" @click="handleExport">
        <el-icon><Download /></el-icon>
        导出日志
      </el-button>
    </div>

    <div class="page-content">
      <el-card>
        <div class="filter-bar">
          <div class="filter-row">
            <el-input
              v-model="filters.user_id"
              placeholder="操作人 ID"
              clearable
              style="width: 200px"
              @clear="handleFilter" />

            <el-select
              v-model="filters.action"
              placeholder="操作类型"
              clearable
              style="width: 150px; margin-left: 12px"
              @change="handleFilter">
              <el-option label="创建" value="create" />
              <el-option label="更新" value="update" />
              <el-option label="删除" value="delete" />
              <el-option label="暂停" value="suspend" />
              <el-option label="激活" value="activate" />
              <el-option label="重置密码" value="reset_password" />
            </el-select>

            <el-select
              v-model="filters.entity_type"
              placeholder="实体类型"
              clearable
              style="width: 150px; margin-left: 12px"
              @change="handleFilter">
              <el-option label="用户" value="user" />
              <el-option label="配置" value="config" />
              <el-option label="多维表" value="base" />
              <el-option label="数据表" value="table" />
              <el-option label="字段" value="field" />
              <el-option label="记录" value="record" />
            </el-select>

            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
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
            <el-table-column prop="user_id" label="操作人 ID" width="280" />
            <el-table-column prop="action" label="操作类型" width="120">
              <template #default="{ row }">
                <el-tag :type="getActionTagType(row.action)">
                  {{ getActionLabel(row.action) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="entity_type" label="实体类型" width="100">
              <template #default="{ row }">
                {{ getEntityTypeLabel(row.entity_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="entity_id" label="实体 ID" width="280" />
            <el-table-column prop="ip_address" label="IP 地址" width="150" />
            <el-table-column
              prop="created_at"
              label="操作时间"
              width="180"
              sortable>
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="showDetail(row)">
                  详情
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
    <el-dialog v-model="detailVisible" title="日志详情" width="800px">
      <el-descriptions :column="2" border v-if="selectedLog">
        <el-descriptions-item label="操作人 ID">{{
          selectedLog.user_id
        }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">
          <el-tag :type="getActionTagType(selectedLog.action)">
            {{ getActionLabel(selectedLog.action) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="实体类型">
          {{ getEntityTypeLabel(selectedLog.entity_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="实体 ID">{{
          selectedLog.entity_id
        }}</el-descriptions-item>
        <el-descriptions-item label="IP 地址">{{
          selectedLog.ip_address
        }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">
          {{ formatDate(selectedLog.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="User Agent" :span="2">
          {{ selectedLog.user_agent }}
        </el-descriptions-item>
        <el-descriptions-item label="旧值" :span="2">
          <pre v-if="selectedLog.old_value" class="json-viewer">{{
            JSON.stringify(selectedLog.old_value, null, 2)
          }}</pre>
          <span v-else class="text-muted">无</span>
        </el-descriptions-item>
        <el-descriptions-item label="新值" :span="2">
          <pre v-if="selectedLog.new_value" class="json-viewer">{{
            JSON.stringify(selectedLog.new_value, null, 2)
          }}</pre>
          <span v-else class="text-muted">无</span>
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
  create: "创建",
  update: "更新",
  delete: "删除",
  suspend: "暂停",
  activate: "激活",
  reset_password: "重置密码",
};

const getActionLabel = (action: string): string => {
  return actionLabelMap[action] || action;
};

const getActionTagType = (
  action: string,
): "success" | "warning" | "info" | "danger" | "" => {
  const typeMap: Record<
    string,
    "success" | "warning" | "info" | "danger" | ""
  > = {
    create: "success",
    update: "warning",
    delete: "danger",
    suspend: "warning",
    activate: "success",
    reset_password: "info",
  };
  return typeMap[action] || "";
};

const getEntityTypeLabel = (entityType: string): string => {
  const typeMap: Record<string, string> = {
    user: "用户",
    config: "配置",
    base: "多维表",
    table: "数据表",
    field: "字段",
    record: "记录",
    view: "视图",
    dashboard: "仪表盘",
  };
  return typeMap[entityType] || entityType;
};

const formatDate = (dateString: string): string => {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const fetchLogs = async () => {
  try {
    await adminStore.fetchOperationLogs({
      page: currentPage.value,
      pageSize: pageSize.value,
      ...filters,
    });
  } catch (error) {
    ElMessage.error("获取日志失败");
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
    ElMessage.success("导出成功");
  } catch (error) {
    ElMessage.error("导出失败");
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
