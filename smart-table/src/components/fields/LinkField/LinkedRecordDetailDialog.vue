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
            <!-- 关联字段 -->
            <template v-if="field.type === 'link'">
              <template v-if="getLinkFieldValue(field.id)">
                <el-tag
                  v-for="(item, index) in getLinkFieldValue(field.id)"
                  :key="index"
                  size="small"
                  class="value-tag"
                  type="primary"
                >
                  {{ item }}
                </el-tag>
              </template>
              <span v-else class="empty-value">-</span>
            </template>
            <!-- 附件字段 -->
            <template v-else-if="field.type === 'attachment'">
              <template v-if="getAttachmentFieldValue(field.id).length > 0">
                <el-tag
                  v-for="(file, index) in getAttachmentFieldValue(field.id).slice(0, 3)"
                  :key="index"
                  size="small"
                  class="value-tag"
                  type="info"
                >
                  {{ file.name || file.filename || '附件' }}
                </el-tag>
                <span v-if="getAttachmentFieldValue(field.id).length > 3" class="more-count">
                  +{{ getAttachmentFieldValue(field.id).length - 3 }}
                </span>
              </template>
              <span v-else class="empty-value">-</span>
            </template>
            <!-- 多选字段 -->
            <template v-else-if="field.type === 'multi_select' && isArrayValue(recordDetail.values[field.id])">
              <el-tag
                v-for="(item, index) in recordDetail.values[field.id]"
                :key="index"
                size="small"
                class="value-tag"
              >
                {{ getSelectOptionName(field, item) }}
              </el-tag>
            </template>
            <!-- 单选字段 -->
            <template v-else-if="field.type === 'single_select' && recordDetail.values[field.id]">
              <el-tag size="small" class="value-tag">
                {{ getSelectOptionName(field, recordDetail.values[field.id]) }}
              </el-tag>
            </template>
            <!-- 复选框字段 -->
            <template v-else-if="field.type === 'checkbox'">
              <el-tag size="small" :type="recordDetail.values[field.id] ? 'success' : 'info'">
                {{ recordDetail.values[field.id] ? '是' : '否' }}
              </el-tag>
            </template>
            <!-- 日期/日期时间字段 -->
            <template v-else-if="field.type === 'date' || field.type === 'date_time'">
              {{ formatDateTime(recordDetail.values[field.id]) }}
            </template>
            <!-- 评分字段 -->
            <template v-else-if="field.type === 'rating'">
              <el-rate
                :model-value="Number(recordDetail.values[field.id]) || 0"
                :max="field.options?.maxRating || 5"
                disabled
                size="small"
              />
            </template>
            <!-- 进度/百分比字段 -->
            <template v-else-if="field.type === 'progress' || field.type === 'percent'">
              <div class="progress-value">
                <el-progress
                  :percentage="Number(recordDetail.values[field.id]) || 0"
                  :stroke-width="8"
                  style="width: 100px"
                />
              </div>
            </template>
            <!-- 公式字段 -->
            <template v-else-if="field.type === 'formula'">
              <span class="formula-value">{{ recordDetail.values[field.id] || '-' }}</span>
            </template>
            <!-- 成员字段 -->
            <template v-else-if="field.type === 'member'">
              <template v-if="recordDetail.values[field.id]">
                <el-tag size="small" type="info">
                  {{ getMemberDisplayName(recordDetail.values[field.id]) }}
                </el-tag>
              </template>
              <span v-else class="empty-value">-</span>
            </template>
            <!-- 其他字段类型 -->
            <template v-else-if="recordDetail.values[field.id] !== null && recordDetail.values[field.id] !== undefined && recordDetail.values[field.id] !== ''">
              {{ formatFieldValue(recordDetail.values[field.id], field) }}
            </template>
            <!-- 空值 -->
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
        <el-button type="primary" @click="showFullRecordDetail">
          查看完整记录
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- 完整记录详情抽屉 -->
  <RecordDetailDrawer
    v-model:visible="detailDrawerVisible"
    :record="fullRecordData"
    :fields="fields"
    :readonly="true"
    size="50%"
    @save="handleDetailSave"
  />
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import {
  ElMessage,
  ElTag,
  ElRate,
  ElProgress,
} from "element-plus";
import dayjs from "dayjs";
import { recordApiService } from "@/services/api/recordApiService";
import { fieldService } from "@/db/services";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import RecordDetailDrawer from "@/components/dialogs/RecordDetailDrawer.vue";

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

// 显示的字段（仅显示可视字段，隐藏非可视字段和系统字段）
const displayFields = computed(() => {
  return fields.value.filter((f) => {
    // 排除系统字段
    if (f.isSystem) return false;
    
    // 排除主键类型字段（主键已在记录头部显示）
    if (f.type === "primaryKey") return false;
    
    // 只显示可视字段（isVisible 为 undefined 或 true 时显示，false 时隐藏）
    return f.isVisible !== false;
  });
});

// 完整记录详情抽屉状态
const detailDrawerVisible = ref(false);

// 完整记录数据
const fullRecordData = computed(() => recordDetail.value);

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

// 获取关联字段的显示值
const getLinkFieldValue = (fieldId: string): string[] => {
  if (!recordDetail.value) return [];
  const value = recordDetail.value.values[fieldId];
  if (!value) return [];
  
  // 关联字段值可能是数组或单个值
  if (Array.isArray(value)) {
    return value.map((v) => {
      if (typeof v === "object" && v !== null && "display_value" in v) {
        return (v as { display_value: string }).display_value;
      }
      return String(v);
    });
  }
  if (typeof value === "object" && value !== null && "display_value" in value) {
    return [(value as { display_value: string }).display_value];
  }
  return [String(value)];
};

// 获取附件字段的文件列表
const getAttachmentFieldValue = (fieldId: string): Array<{ name?: string; filename?: string }> => {
  if (!recordDetail.value) return [];
  const value = recordDetail.value.values[fieldId];
  if (!value) return [];
  
  if (Array.isArray(value)) {
    return value.map((v) => {
      if (typeof v === "object" && v !== null) {
        return v as { name?: string; filename?: string };
      }
      return { name: String(v) };
    });
  }
  return [];
};

// 获取选择字段选项的名称
const getSelectOptionName = (field: FieldEntity, optionId: unknown): string => {
  if (!optionId) return "-";
  
  const choices = field.options?.choices as Array<{ id: string; name: string }> | undefined;
  if (!choices) return String(optionId);
  
  const option = choices.find((c) => c.id === optionId);
  return option?.name || String(optionId);
};

// 获取成员的显示名称
const getMemberDisplayName = (value: unknown): string => {
  if (!value) return "-";
  
  if (typeof value === "object" && value !== null) {
    const member = value as { name?: string; displayName?: string; email?: string };
    return member.name || member.displayName || member.email || "未知成员";
  }
  return String(value);
};

// 显示完整记录详情弹窗
const showFullRecordDetail = () => {
  if (!recordDetail.value) {
    ElMessage.warning("记录数据未加载");
    return;
  }
  detailDrawerVisible.value = true;
};

// 处理详情保存（只读模式下不会触发，但需要处理）
const handleDetailSave = (recordId: string, values: Record<string, unknown>) => {
  console.log("[LinkedRecordDetailDialog] 详情保存:", recordId, values);
};

// 跳转到目标表（保留原功能，可通过其他方式触发）
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

.progress-value {
  display: flex;
  align-items: center;
  width: 100%;
}

.formula-value {
  font-family: "SF Mono", Monaco, monospace;
  font-size: 13px;
  color: var(--el-text-color-primary);
  background-color: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
}

.more-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: 4px;
}
</style>
