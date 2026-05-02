<template>
  <div class="link-field">
    <!-- 显示模式 -->
    <div v-if="!isEditing" class="link-field-display" @click="handleClick">
      <template v-if="linkedRecords.length > 0">
        <el-tag
          v-for="record in displayedRecords"
          :key="record.record_id"
          size="small"
          class="link-tag"
          @click.stop="showRecordDetail(record.record_id)"
        >
          {{ record.display_value }}
        </el-tag>
        <el-tag
          v-if="hasMoreRecords"
          size="small"
          type="info"
          class="link-tag more-tag"
        >
          +{{ linkedRecords.length - maxDisplayCount }}
        </el-tag>
      </template>
      <span v-else class="empty-text">-</span>
    </div>

    <!-- 编辑模式 -->
    <div v-else class="link-field-editor">
      <LinkRecordSelector
        :visible="isEditing"
        :target-table-id="targetTableId"
        :display-field-id="displayFieldId"
        :selected-ids="selectedRecordIds"
        :allow-multiple="allowMultiple"
        @confirm="handleConfirm"
        @cancel="handleCancel"
      />
    </div>

    <!-- 完整记录详情抽屉 -->
    <RecordDetailDrawer
      v-model:visible="detailDrawerVisible"
      :record="selectedRecord"
      :fields="targetTableFields"
      :readonly="true"
      size="50%"
      @save="handleDetailSave"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElTag, ElMessage } from "element-plus";
import LinkRecordSelector from "./LinkRecordSelector.vue";
import RecordDetailDrawer from "@/components/dialogs/RecordDetailDrawer.vue";
import { recordApiService } from "@/services/api/recordApiService";
import { fieldService } from "@/db/services/fieldService";
import type { LinkedRecord, RelationshipType } from "@/types/link";
import type { FieldEntity, RecordEntity } from "@/db/schema";

interface Props {
  value?: string[];
  linkedRecords?: LinkedRecord[];
  targetTableId?: string;
  displayFieldId?: string;
  relationshipType?: RelationshipType;
  isEditing?: boolean;
  maxDisplayCount?: number;
}

const props = withDefaults(defineProps<Props>(), {
  value: () => [],
  linkedRecords: () => [],
  relationshipType: "one_to_many",
  isEditing: false,
  maxDisplayCount: 3,
});

const emit = defineEmits<{
  (e: "update:value", value: string[]): void;
  (e: "change", value: string[], records: LinkedRecord[]): void;
  (e: "edit-start"): void;
  (e: "edit-end"): void;
}>();

const selectedRecordIds = computed(() => props.value || []);

const allowMultiple = computed(() => 
  props.relationshipType === "one_to_many" || 
  props.relationshipType === "many_to_many"
);

// 显示的记录列表
const displayedRecords = computed(() => {
  return props.linkedRecords.slice(0, props.maxDisplayCount);
});

// 是否有更多记录
const hasMoreRecords = computed(() => {
  return props.linkedRecords.length > props.maxDisplayCount;
});

// 详情抽屉状态
const detailDrawerVisible = ref(false);
const selectedRecord = ref<RecordEntity | null>(null);
const targetTableFields = ref<FieldEntity[]>([]);
const loadingRecord = ref(false);

// 加载目标表的字段
const loadTargetTableFields = async () => {
  if (!props.targetTableId) return;
  
  try {
    const fields = await fieldService.getFieldsByTable(props.targetTableId);
    targetTableFields.value = fields;
  } catch (error) {
    console.error("[LinkField] 加载字段失败:", error);
    targetTableFields.value = [];
  }
};

// 监听 targetTableId 变化，预加载字段
watch(
  () => props.targetTableId,
  (tableId) => {
    if (tableId) {
      loadTargetTableFields();
    }
  },
  { immediate: true }
);

// 处理点击事件
const handleClick = () => {
  if (!props.isEditing) {
    emit("edit-start");
  }
};

// 显示记录详情抽屉
const showRecordDetail = async (recordId: string) => {
  if (!props.targetTableId) return;
  
  loadingRecord.value = true;
  
  try {
    // 加载记录详情
    const record = await recordApiService.getRecord(recordId);
    selectedRecord.value = record;
    
    // 确保字段已加载
    if (targetTableFields.value.length === 0) {
      await loadTargetTableFields();
    }
    
    // 打开详情抽屉
    detailDrawerVisible.value = true;
  } catch (error) {
    console.error("[LinkField] 加载记录详情失败:", error);
    ElMessage.error("加载记录详情失败");
  } finally {
    loadingRecord.value = false;
  }
};

// 处理详情保存（只读模式下不会触发）
const handleDetailSave = (recordId: string, values: Record<string, unknown>) => {
  console.log("[LinkField] 详情保存:", recordId, values);
};

// 处理确认选择
const handleConfirm = (selectedIds: string[], records: LinkedRecord[]) => {
  emit("update:value", selectedIds);
  emit("change", selectedIds, records);
  emit("edit-end");
};

// 处理取消
const handleCancel = () => {
  // 取消编辑，通知父组件关闭编辑状态
  emit("edit-end");
};
</script>

<style scoped lang="scss">
.link-field {
  width: 100%;
  min-height: 32px;
}

.link-field-display {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  min-height: 32px;
  padding: 4px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--el-fill-color-light);
  }
}

.link-tag {
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
}

.more-tag {
  cursor: default;

  &:hover {
    transform: none;
    box-shadow: none;
  }
}

.empty-text {
  color: var(--el-text-color-placeholder);
  font-size: 14px;
}

.link-field-editor {
  width: 100%;
}
</style>
