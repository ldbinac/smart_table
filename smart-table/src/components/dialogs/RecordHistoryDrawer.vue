<template>
  <el-drawer
    v-model="visible"
    title="变更历史"
    :size="drawerSize"
    :close-on-click-modal="false"
    class="record-history-drawer">
    <div v-loading="loading" class="history-content">
      <!-- 空状态 -->
      <el-empty
        v-if="!loading && historyList.length === 0"
        description="暂无变更历史" />

      <!-- 历史列表 -->
      <div v-else class="history-list">
        <div v-for="item in historyList" :key="item.id" class="history-item">
          <!-- 头部：操作类型和时间 -->
          <div class="history-header">
            <div class="action-badge" :class="getActionClass(item.action)">
              {{ getActionText(item.action) }}
            </div>
            <span class="history-time">{{ formatTime(item.changed_at) }}</span>
          </div>

          <!-- 变更人信息 -->
          <div class="changer-info">
            <el-avatar
              :size="24"
              :src="item.changed_by?.avatar"
              :icon="UserFilled"
              class="changer-avatar" />
            <span class="changer-name">{{
              item.changed_by?.name || "未知用户"
            }}</span>
          </div>

          <!-- 变更详情 -->
          <div
            v-if="item.changes && item.changes.length > 0"
            class="changes-detail">
            <div class="changes-title">字段变更：</div>
            <div
              v-for="(change, index) in item.changes"
              :key="index"
              class="change-item">
              <span class="field-name">{{
                getFieldName(change.field_id)
              }}</span>
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
          </div>

          <!-- 创建/删除时的快照提示 -->
          <div v-else-if="item.action === 'CREATE'" class="snapshot-hint">
            创建了这条记录
          </div>
          <div
            v-else-if="item.action === 'DELETE'"
            class="snapshot-hint delete-hint">
            删除了这条记录（已保存数据快照）
          </div>
        </div>
      </div>

      <!-- 分页器 -->
      <div v-if="total > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange" />
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { UserFilled, ArrowRight } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import type { Field } from "@/api/types";
import {
  recordHistoryApiService,
  type RecordHistory,
} from "@/services/api/recordHistoryApiService";

interface Props {
  modelValue: boolean;
  recordId?: string;
  fields?: Field[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
}>();

// 可见性
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

// 抽屉尺寸
const drawerSize = computed(() => {
  return window.innerWidth < 768 ? "100%" : "500px";
});

// 加载状态
const loading = ref(false);

// 历史列表
const historyList = ref<RecordHistory[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);

// 获取字段名称
const getFieldName = (fieldId: string): string => {
  const field = props.fields?.find((f) => f.id === fieldId);
  return field?.name || fieldId;
};

// 格式化值
const formatValue = (value: any): string => {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (Array.isArray(value)) {
    return value.join(", ") || "-";
  }
  return String(value);
};

// 获取操作类型文本
const getActionText = (action: string): string => {
  const actionMap: Record<string, string> = {
    CREATE: "创建",
    UPDATE: "更新",
    DELETE: "删除",
  };
  return actionMap[action] || action;
};

// 获取操作类型样式类
const getActionClass = (action: string): string => {
  const classMap: Record<string, string> = {
    CREATE: "action-create",
    UPDATE: "action-update",
    DELETE: "action-delete",
  };
  return classMap[action] || "";
};

// 格式化时间
const formatTime = (time: string): string => {
  return dayjs(time).format("YYYY-MM-DD HH:mm:ss");
};

// 加载历史数据
const loadHistory = async () => {
  if (!props.recordId) return;

  loading.value = true;
  try {
    const response = await recordHistoryApiService.getRecordHistory(
      props.recordId,
      currentPage.value,
      pageSize.value,
    );
    historyList.value = response.items || [];
    total.value = response.total || 0;
  } catch (error) {
    console.error("加载变更历史失败:", error);
    historyList.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

// 分页大小变化
const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  loadHistory();
};

// 页码变化
const handlePageChange = (page: number) => {
  currentPage.value = page;
  loadHistory();
};

// 监听可见性变化
watch(
  () => props.modelValue,
  (val) => {
    if (val && props.recordId) {
      currentPage.value = 1;
      loadHistory();
    }
  },
);

// 监听记录ID变化
watch(
  () => props.recordId,
  () => {
    if (visible.value && props.recordId) {
      currentPage.value = 1;
      loadHistory();
    }
  },
);
</script>

<style lang="scss" scoped>
.record-history-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 16px 20px;
    border-bottom: 1px solid #e4e7ed;

    .el-drawer__title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }

  :deep(.el-drawer__body) {
    padding: 0;
  }
}

.history-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.history-item {
  padding: 16px;
  margin-bottom: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  border-left: 4px solid #dcdfe6;

  &:last-child {
    margin-bottom: 0;
  }

  &.action-create {
    border-left-color: #67c23a;
  }

  &.action-update {
    border-left-color: #409eff;
  }

  &.action-delete {
    border-left-color: #f56c6c;
  }
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
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

.history-time {
  font-size: 13px;
  color: #909399;
}

.changer-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  .changer-name {
    font-size: 14px;
    color: #606266;
  }
}

.changes-detail {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #dcdfe6;
}

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
  background: #fff;
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

.pagination-wrapper {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  justify-content: center;
}
</style>
