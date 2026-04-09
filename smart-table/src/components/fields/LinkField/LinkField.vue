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
          @click.stop="navigateToRecord(record.record_id)"
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
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElTag } from "element-plus";
import LinkRecordSelector from "./LinkRecordSelector.vue";
import type { LinkedRecord } from "@/types/link";

interface Props {
  value?: string[]; // 关联记录 ID 数组
  linkedRecords?: LinkedRecord[]; // 关联记录详情
  targetTableId?: string; // 目标表 ID
  displayFieldId?: string; // 显示字段 ID
  relationshipType?: "one_to_one" | "one_to_many"; // 关联类型
  isEditing?: boolean; // 是否处于编辑模式
  maxDisplayCount?: number; // 最大显示数量
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

const router = useRouter();

// 选中的记录 ID 列表
const selectedRecordIds = computed(() => props.value || []);

// 是否允许多选
const allowMultiple = computed(() => props.relationshipType === "one_to_many");

// 显示的记录列表
const displayedRecords = computed(() => {
  return props.linkedRecords.slice(0, props.maxDisplayCount);
});

// 是否有更多记录
const hasMoreRecords = computed(() => {
  return props.linkedRecords.length > props.maxDisplayCount;
});

// 处理点击事件
const handleClick = () => {
  if (!props.isEditing) {
    emit("edit-start");
  }
};

// 跳转到关联记录
const navigateToRecord = (recordId: string) => {
  if (props.targetTableId) {
    // 在新标签页打开关联记录
    const route = router.resolve({
      name: "Base",
      params: { tableId: props.targetTableId },
      query: { recordId },
    });
    window.open(route.href, "_blank");
  }
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
