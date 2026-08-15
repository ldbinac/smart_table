<template>
  <el-dialog
    v-model="visible"
    :title="t('recordHistory.table.title')"
    :width="dialogWidth"
    class="table-history-dialog"
    append-to-body
    destroy-on-close>
    <div v-loading="loading" class="table-history-content">
      <!-- 搜索条件 -->
      <el-form :inline="true" class="search-form" @submit.prevent>
        <div class="search-row">
          <el-form-item :label="t('recordHistory.table.timeRange')">
            <el-date-picker
              v-model="timeRange"
              type="datetimerange"
              :range-separator="'-'"
              :start-placeholder="t('recordHistory.table.timeRange')"
              :end-placeholder="t('recordHistory.table.timeRange')"
              value-format="YYYY-MM-DDTHH:mm:ss"
              :shortcuts="pickerShortcuts"
              style="width: 360px" />
          </el-form-item>
          <el-form-item :label="t('recordHistory.table.changedBy')">
            <MemberSelect
              v-model="searchUserId"
              :placeholder="t('recordHistory.table.changedBy')"
              style="width: 220px; height: 28px;" />
          </el-form-item>
        </div>
        <div class="search-row">
          <el-form-item :label="t('recordHistory.table.action')">
            <el-select
              v-model="searchAction"
              :placeholder="t('recordHistory.table.actionPlaceholder')"
              clearable
              style="width: 140px">
              <el-option :label="t('recordHistory.table.all')" value="" />
              <el-option :label="t('recordHistory.create')" value="CREATE" />
              <el-option :label="t('recordHistory.update')" value="UPDATE" />
              <el-option :label="t('recordHistory.delete')" value="DELETE" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleSearch">
              {{ t('recordHistory.table.search') }}
            </el-button>
            <el-button :icon="RefreshLeft" @click="handleReset">
              {{ t('recordHistory.table.reset') }}
            </el-button>
          </el-form-item>
        </div>
      </el-form>

      <!-- 列表 -->
      <el-table
        :data="historyList"
        style="width: 100%"
        :empty-text="t('recordHistory.table.empty')"
        header-cell-class-name="history-table-header">
        <el-table-column :label="t('recordHistory.table.action')" width="100">
          <template #default="{ row }">
            <span class="action-badge" :class="getActionClass(row.action)">
              {{ getActionText(row.action) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="t('recordHistory.table.changedBy')" min-width="160">
          <template #default="{ row }">
            <div class="changer-cell">
              <el-avatar
                :size="24"
                :src="row.changed_by?.avatar"
                :icon="UserFilled" />
              <span class="changer-name">{{
                row.changed_by?.name || t('recordHistory.unknownUser')
              }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('recordHistory.table.changedAt')" min-width="180">
          <template #default="{ row }">
            <span class="time-cell">{{ formatTime(row.changed_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('recordHistory.table.recordId')" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="record-id-cell">{{ row.record_id }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('recordHistory.table.detail')" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetail(row)">
              {{ t('recordHistory.table.detail') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="total > 0" class="pagination-wrapper">
        <span class="total-text">{{ t('recordHistory.table.total', { total }) }}</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange" />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="t('recordHistory.table.changeDetail')"
      :width="detailWidth"
      append-to-body
      class="history-detail-dialog">
      <div v-if="currentDetail" class="detail-content">
        <div class="detail-meta">
          <span class="action-badge" :class="getActionClass(currentDetail.action)">
            {{ getActionText(currentDetail.action) }}
          </span>
          <span class="meta-text">{{
            currentDetail.changed_by?.name || t('recordHistory.unknownUser')
          }}</span>
          <span class="meta-text">{{ formatTime(currentDetail.changed_at) }}</span>
        </div>

        <!-- 变更内容（默认展示） -->
        <div class="changes-block">
          <div class="changes-title">{{ t('recordHistory.fieldChanges') }}</div>
          <template
            v-if="currentDetail.changes && currentDetail.changes.length > 0">
            <div
              v-for="(change, idx) in currentDetail.changes"
              :key="idx"
              class="change-item">
              <div class="field-name">{{ getFieldName(change.field_id) }}</div>
              <div class="value-change">
                <span
                  class="old-value"
                  :title="String(change.old_value ?? '-')">
                  {{ formatValue(change.old_value) }}
                </span>
                <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                <span
                  class="new-value"
                  :title="String(change.new_value ?? '-')">
                  {{ formatValue(change.new_value) }}
                </span>
              </div>
            </div>
          </template>
          <div
            v-else-if="currentDetail.action === 'CREATE'"
            class="snapshot-hint create-hint">
            {{ t('recordHistory.createdSnapshot') }}
          </div>
          <div
            v-else-if="currentDetail.action === 'DELETE'"
            class="snapshot-hint delete-hint">
            {{ t('recordHistory.deletedSnapshot') }}
          </div>
        </div>

        <!-- 历史快照（默认收起） -->
        <el-collapse v-model="snapshotCollapse" class="snapshot-collapse">
          <el-collapse-item
            :title="t('recordHistory.table.snapshot')"
            name="snapshot">
            <div v-if="snapshotEntries.length" class="snapshot-block">
              <div class="snapshot-tip">
                {{ t('recordHistory.table.snapshotTip') }}
              </div>
              <div class="snapshot-grid">
                <div
                  v-for="entry in snapshotEntries"
                  :key="entry.key"
                  class="snapshot-item">
                  <div class="snapshot-field">{{ entry.label }}</div>
                  <div class="snapshot-value">{{ entry.value }}</div>
                </div>
              </div>
            </div>
            <div v-else class="empty-snapshot">
              {{ t('recordHistory.table.emptySnapshot') }}
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { Search, RefreshLeft, UserFilled, ArrowRight } from "@element-plus/icons-vue";
import { formatDateTime } from "@/utils/timezone";
import {
  getTableHistory,
  type RecordHistory,
} from "@/services/api/recordHistoryApiService";
import type { FieldEntity } from "@/db/schema";
import MemberSelect from "@/components/common/MemberSelect.vue";

interface Props {
  modelValue: boolean;
  tableId?: string;
  fields?: FieldEntity[];
}

interface SnapshotEntry {
  key: string;
  label: string;
  value: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
}>();

const { t } = useI18n();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const dialogWidth = computed(() => (window.innerWidth < 768 ? "100%" : "900px"));
const detailWidth = computed(() => (window.innerWidth < 768 ? "100%" : "640px"));

const loading = ref(false);
const historyList = ref<RecordHistory[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);

// 搜索条件
const timeRange = ref<[string, string] | null>(null);
const searchUserId = ref<string[]>([]);
const searchAction = ref<"CREATE" | "UPDATE" | "DELETE" | "">("");

// 日期快捷选项
const pickerShortcuts = [
  {
    text: "近7天",
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 7);
      return [start, end] as [Date, Date];
    },
  },
  {
    text: "近30天",
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 30);
      return [start, end] as [Date, Date];
    },
  },
];

// 详情
const detailVisible = ref(false);
const currentDetail = ref<RecordHistory | null>(null);
const snapshotEntries = ref<SnapshotEntry[]>([]);
const snapshotCollapse = ref<string[]>([]);

const getFieldName = (fieldId: string): string => {
  const field = props.fields?.find((f) => f.id === fieldId);
  return field?.name || fieldId;
};

const formatValue = (value: any): string => {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") {
    return value ? t("recordHistory.yes") : t("recordHistory.no");
  }
  if (Array.isArray(value)) return value.join(", ") || "-";
  return String(value);
};

const getActionText = (action: string): string => {
  const map: Record<string, string> = {
    CREATE: t("recordHistory.create"),
    UPDATE: t("recordHistory.update"),
    DELETE: t("recordHistory.delete"),
  };
  return map[action] || action;
};

const getActionClass = (action: string): string => {
  const map: Record<string, string> = {
    CREATE: "action-create",
    UPDATE: "action-update",
    DELETE: "action-delete",
  };
  return map[action] || "";
};

const formatTime = (time: string): string => formatDateTime(time);

const loadHistory = async () => {
  if (!props.tableId) return;
  loading.value = true;
  try {
    const response = await getTableHistory(props.tableId, {
      page: currentPage.value,
      size: pageSize.value,
      startTime: timeRange.value?.[0] || undefined,
      endTime: timeRange.value?.[1] || undefined,
      changedBy: searchUserId.value.length ? searchUserId.value[0] : undefined,
      action: searchAction.value || undefined,
    });
    historyList.value = response.items || [];
    total.value = response.total || 0;
  } catch (error) {
    console.error("加载表格历史变更失败:", error);
    historyList.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  currentPage.value = 1;
  loadHistory();
};

const handleReset = () => {
  timeRange.value = null;
  searchUserId.value = [];
  searchAction.value = "";
  currentPage.value = 1;
  loadHistory();
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  loadHistory();
};

const handlePageChange = (page: number) => {
  currentPage.value = page;
  loadHistory();
};

const openDetail = (row: RecordHistory) => {
  currentDetail.value = row;
  const snapshot = row.snapshot || {};
  snapshotEntries.value = Object.keys(snapshot).map((key) => ({
    key,
    label: getFieldName(key),
    value: formatValue(snapshot[key]),
  }));
  detailVisible.value = true;
};

watch(
  () => props.modelValue,
  (val) => {
    if (val && props.tableId) {
      currentPage.value = 1;
      loadHistory();
    }
  },
);
</script>

<style lang="scss" scoped>
.table-history-dialog {
  :deep(.el-dialog__body) {
    padding: 12px 20px 20px;
  }
}

.table-history-content {
  min-height: 200px;
}

.search-form {
  margin-bottom: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;

  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 16px;
  }

  .search-row {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;

    & + .search-row {
      margin-top: 16px;
    }
  }
}

.history-table-header {
  background: #f5f7fa !important;
  color: #303133;
  font-weight: 600;
}

.changer-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  .changer-name {
    font-size: 13px;
    color: #606266;
  }
}

.time-cell {
  font-size: 13px;
  color: #606266;
}

.record-id-cell {
  font-size: 13px;
  color: #909399;
  font-family: monospace;
}

.action-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;

  &.action-create {
    background: #f0f9eb;
    color: #67c23a;
  }

  &.action-update {
    background: #ecf5ff;
    color: #409eff;
  }

  &.action-delete {
    background: #fef0f0;
    color: #f56c6c;
  }
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 16px;

  .total-text {
    font-size: 13px;
    color: #909399;
  }
}

.detail-content {
  .detail-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;

    .meta-text {
      font-size: 13px;
      color: #606266;
    }
  }
}

.changes-block {
  padding: 12px 0 4px;
  border-top: 1px dashed #dcdfe6;

  .changes-title {
    font-size: 13px;
    color: #909399;
    margin-bottom: 8px;
  }

  .change-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 12px;
    background: #f5f7fa;
    border-radius: 4px;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .field-name {
    font-size: 13px;
    font-weight: 500;
    color: #303133;
  }

  .value-change {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  .old-value {
    flex: 1;
    padding: 4px 8px;
    background: #fef0f0;
    color: #f56c6c;
    border-radius: 4px;
    text-decoration: line-through;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .new-value {
    flex: 1;
    padding: 4px 8px;
    background: #f0f9eb;
    color: #67c23a;
    border-radius: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .arrow-icon {
    color: #909399;
    font-size: 14px;
  }
}

.snapshot-collapse {
  margin-top: 16px;

  :deep(.el-collapse-item__header) {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }
}

.empty-snapshot {
  font-size: 13px;
  color: #909399;
  text-align: center;
  padding: 12px 0;
}

.snapshot-block {
  .snapshot-tip {
    font-size: 13px;
    color: #909399;
    margin-bottom: 12px;
  }
}

.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.snapshot-item {
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  border-left: 3px solid #409eff;

  .snapshot-field {
    font-size: 13px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 4px;
  }

  .snapshot-value {
    font-size: 13px;
    color: #606266;
    word-break: break-all;
  }
}

.snapshot-hint {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f0f9eb;
  color: #67c23a;
  border-radius: 4px;
  font-size: 13px;
  text-align: center;

  &.delete-hint {
    background: #fef0f0;
    color: #f56c6c;
  }
}
</style>
