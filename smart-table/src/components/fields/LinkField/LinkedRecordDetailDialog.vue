<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="600px"
    :close-on-click-modal="true"
    :close-on-press-escape="true"
    destroy-on-close
    class="linked-record-detail-dialog"
    @close="handleClose"
  >
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-container">
      <el-empty description="加载失败">
        <template #description>
          <p>{{ error }}</p>
        </template>
        <el-button type="primary" @click="loadRecordDetail">重新加载</el-button>
      </el-empty>
    </div>

    <!-- 记录详情内容 -->
    <div v-else-if="recordDetail" class="record-detail-content">
      <!-- 记录基本信息 -->
      <div class="record-header">
        <div class="record-id">
          <span class="label">记录ID:</span>
          <span class="value">{{ recordDetail.id }}</span>
        </div>
        <div class="record-time" v-if="recordDetail.created_at">
          <span class="label">创建时间:</span>
          <span class="value">{{ formatDateTime(recordDetail.created_at) }}</span>
        </div>
      </div>

      <el-divider />

      <!-- 字段值列表 -->
      <div class="fields-list">
        <div
          v-for="field in displayFields"
          :key="field.id"
          class="field-item"
        >
          <div class="field-label">{{ field.name }}</div>
          <div class="field-value">
            <template v-if="field.type === 'link'">
              <!-- 关联字段特殊处理 -->
              <el-tag size="small" type="info">关联字段</el-tag>
            </template>
            <template v-else-if="field.type === 'attachment'">
              <!-- 附件字段 -->
              <el-tag size="small" type="info">附件</el-tag>
            </template>
            <template v-else-if="isArrayValue(recordDetail.values[field.id])">
              <!-- 数组值（如多选） -->
              <el-tag
                v-for="(item, index) in recordDetail.values[field.id]"
                :key="index"
                size="small"
                class="value-tag"
              >
                {{ item }}
              </el-tag>
            </template>
            <template v-else-if="recordDetail.values[field.id] !== null && recordDetail.values[field.id] !== undefined">
              {{ formatFieldValue(recordDetail.values[field.id], field) }}
            </template>
            <span v-else class="empty-value">-</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-else description="暂无记录详情" />

    <!-- 底部按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button type="primary" @click="navigateToTable">
          查看完整记录
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";
import { recordApiService } from "@/services/api/recordApiService";
import { fieldService } from "@/db/services";
import type { FieldEntity, RecordEntity } from "@/db/schema";

interface Props {
  visible: boolean;
  recordId: string;
  tableId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "close"): void;
}>();

const router = useRouter();

// 弹窗可见性
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit("update:visible", value),
});

// 弹窗标题
const dialogTitle = computed(() => {
  return "关联记录详情";
});

// 加载状态
const loading = ref(false);

// 错误信息
const error = ref<string | null>(null);

// 记录详情
const recordDetail = ref<RecordEntity | null>(null);

// 字段列表
const fields = ref<FieldEntity[]>([]);

// 显示的字段（排除系统字段和隐藏字段）
const displayFields = computed(() => {
  return fields.value.filter(
    (f) => !f.isSystem && f.isVisible && f.type !== "primaryKey"
  );
});

// 监听弹窗显示状态
watch(
  () => props.visible,
  (visible) => {
    if (visible && props.recordId && props.tableId) {
      loadRecordDetail();
      loadFields();
    }
  },
  { immediate: true }
);

// 加载记录详情
const loadRecordDetail = async () => {
  if (!props.recordId) return;

  loading.value = true;
  error.value = null;

  try {
    const record = await recordApiService.getRecord(props.recordId);
    recordDetail.value = record;
  } catch (err) {
    console.error("[LinkedRecordDetailDialog] 加载记录详情失败:", err);
    error.value = "加载记录详情失败，请稍后重试";
    ElMessage.error("加载记录详情失败");
  } finally {
    loading.value = false;
  }
};

// 加载字段列表
const loadFields = async () => {
  if (!props.tableId) return;

  try {
    const fieldList = await fieldService.getFieldsByTable(props.tableId);
    fields.value = fieldList;
  } catch (err) {
    console.error("[LinkedRecordDetailDialog] 加载字段列表失败:", err);
  }
};

// 格式化日期时间
const formatDateTime = (value: string | number | Date): string => {
  if (!value) return "-";
  return dayjs(value).format("YYYY-MM-DD HH:mm:ss");
};

// 格式化字段值
const formatFieldValue = (value: unknown, field: FieldEntity): string => {
  if (value === null || value === undefined) return "-";

  switch (field.type) {
    case "date":
      return formatDateTime(value as string);
    case "checkbox":
      return value ? "是" : "否";
    case "singleSelect":
    case "multiSelect":
      if (Array.isArray(value)) {
        return value.join(", ");
      }
      return String(value);
    default:
      return String(value);
  }
};

// 检查是否为数组值
const isArrayValue = (value: unknown): boolean => {
  return Array.isArray(value) && value.length > 0;
};

// 跳转到目标表
const navigateToTable = () => {
  if (props.tableId && props.recordId) {
    const route = router.resolve({
      name: "Base",
      params: { tableId: props.tableId },
      query: { recordId: props.recordId },
    });
    window.open(route.href, "_blank");
  }
  handleClose();
};

// 关闭弹窗
const handleClose = () => {
  dialogVisible.value = false;
  emit("close");
  // 重置状态
  recordDetail.value = null;
  error.value = null;
};
</script>

<style scoped lang="scss">
.linked-record-detail-dialog {
  :deep(.el-dialog__body) {
    max-height: 60vh;
    overflow-y: auto;
    padding: 20px;
  }
}

.loading-container {
  padding: 20px;
}

.error-container {
  padding: 40px 20px;
  text-align: center;
}

.record-detail-content {
  .record-header {
    margin-bottom: 16px;

    .record-id,
    .record-time {
      display: flex;
      align-items: center;
      margin-bottom: 8px;

      .label {
        color: var(--el-text-color-secondary);
        font-size: 14px;
        margin-right: 8px;
        min-width: 70px;
      }

      .value {
        color: var(--el-text-color-primary);
        font-size: 14px;
        font-family: monospace;
      }
    }
  }

  .fields-list {
    .field-item {
      display: flex;
      align-items: flex-start;
      padding: 12px 0;
      border-bottom: 1px solid var(--el-border-color-lighter);

      &:last-child {
        border-bottom: none;
      }

      .field-label {
        width: 120px;
        flex-shrink: 0;
        color: var(--el-text-color-secondary);
        font-size: 14px;
        font-weight: 500;
      }

      .field-value {
        flex: 1;
        color: var(--el-text-color-primary);
        font-size: 14px;
        word-break: break-all;

        .value-tag {
          margin-right: 4px;
          margin-bottom: 4px;
        }

        .empty-value {
          color: var(--el-text-color-placeholder);
        }
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
