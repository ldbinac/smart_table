<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";
import KanbanColumn from "./KanbanColumn.vue";

interface Props {
  fields: FieldEntity[];
  records: RecordEntity[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "updateRecord", recordId: string, values: Record<string, unknown>): void;
  (
    e: "addRecord",
    values: Record<string, unknown>,
    groupInfo?: { groupFieldId?: string; groupId?: string; groupName?: string },
  ): void;
  (e: "deleteRecord", recordId: string): void;
  (e: "editRecord", recordId: string): void;
}>();

const groupFieldId = ref<string>("");
const cardFields = ref<string[]>([]);
const columnRefs = ref<InstanceType<typeof KanbanColumn>[]>([]);

const groupField = computed(() => {
  return props.fields.find((f) => f.id === groupFieldId.value);
});

const selectFields = computed(() => {
  return props.fields.filter(
    (f) =>
      f.type === FieldType.SINGLE_SELECT || f.type === FieldType.MULTI_SELECT,
  );
});

const groups = computed(() => {
  if (!groupField.value) {
    return [{ id: "default", name: "全部", records: props.records }];
  }

  const options =
    (groupField.value.options?.options as Array<{
      id: string;
      name: string;
      color?: string;
    }>) || [];
  const grouped: Record<string, RecordEntity[]> = {};

  options.forEach((opt) => {
    grouped[opt.id] = [];
  });
  grouped["uncategorized"] = [];

  props.records.forEach((record) => {
    const value = record.values[groupFieldId.value];
    if (value && grouped[value as string]) {
      grouped[value as string].push(record);
    } else {
      grouped["uncategorized"].push(record);
    }
  });

  return [
    ...options.map((opt) => ({
      id: opt.id,
      name: opt.name,
      color: opt.color,
      records: grouped[opt.id],
    })),
    { id: "uncategorized", name: "未分组", records: grouped["uncategorized"] },
  ];
});

function handleAddRecord(groupId: string, groupName: string) {
  // 构建初始值，包含分组信息
  const values: Record<string, unknown> = {};
  if (groupFieldId.value && groupId !== "uncategorized") {
    values[groupFieldId.value] = groupId;
  }
  // 传递分组信息用于对话框显示
  const groupInfo = {
    groupFieldId: groupFieldId.value,
    groupId: groupId,
    groupName: groupName,
  };
  emit("addRecord", values, groupInfo);
}

function handleUpdateRecord(recordId: string, values: Record<string, unknown>) {
  emit("updateRecord", recordId, values);
}

function handleDeleteRecord(recordId: string) {
  emit("deleteRecord", recordId);
}

function handleEditRecord(recordId: string) {
  emit("editRecord", recordId);
}

function handleMoveRecord(recordId: string, targetGroupId: string) {
  if (groupFieldId.value) {
    const newGroupId = targetGroupId === "uncategorized" ? null : targetGroupId;
    emit("updateRecord", recordId, { [groupFieldId.value]: newGroupId });
  }
}

// 初始化拖拽
async function initSortable() {
  await nextTick();
  columnRefs.value.forEach((column) => {
    column?.initSortable();
  });
}

// 销毁拖拽
function destroySortable() {
  columnRefs.value.forEach((column) => {
    column?.destroySortable();
  });
}

// 监听分组变化，重新初始化拖拽
watch(groups, async () => {
  destroySortable();
  await nextTick();
  initSortable();
}, { deep: true });

onMounted(() => {
  if (selectFields.value.length > 0) {
    groupFieldId.value = selectFields.value[0].id;
  }
  if (props.fields.length > 0) {
    cardFields.value = props.fields.slice(0, 3).map((f) => f.id);
  }
  initSortable();
});
</script>

<template>
  <div class="kanban-view">
    <div class="kanban-toolbar">
      <div class="toolbar-left">
        <label class="toolbar-label">分组字段</label>
        <el-select
          v-model="groupFieldId"
          placeholder="选择分组字段"
          class="group-select">
          <el-option
            v-for="field in selectFields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <label class="toolbar-label">显示字段</label>
        <el-select
          v-model="cardFields"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择卡片显示字段"
          class="card-fields-select">
          <el-option
            v-for="field in fields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
      </div>
    </div>

    <div class="kanban-container">
      <KanbanColumn
        v-for="group in groups"
        :key="group.id"
        ref="columnRefs"
        :group="group"
        :records="group.records"
        :fields="fields"
        :card-fields="cardFields"
        @add-record="handleAddRecord(group.id, group.name)"
        @edit-record="handleEditRecord"
        @update-record="handleUpdateRecord"
        @delete-record="handleDeleteRecord"
        @move-record="(recordId) => handleMoveRecord(recordId, group.id)" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.kanban-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-color;
}

.kanban-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-lg;
  padding: $spacing-md $spacing-lg;
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  box-shadow: $shadow-sm;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.toolbar-label {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-secondary;
  white-space: nowrap;
}

.group-select {
  width: 180px;
}

.card-fields-select {
  width: 280px;
}

.kanban-container {
  display: flex;
  flex: 1;
  gap: $spacing-lg;
  padding: $spacing-lg;
  overflow-x: auto;
  overflow-y: hidden;

  // 平滑滚动
  scroll-behavior: smooth;

  // 拖拽时的容器样式
  &:global(.dragging) {
    cursor: grabbing;
  }
}

// 滚动条样式
.kanban-container::-webkit-scrollbar {
  height: 8px;
}

.kanban-container::-webkit-scrollbar-track {
  background: transparent;
  border-radius: $border-radius-full;
}

.kanban-container::-webkit-scrollbar-thumb {
  background: $gray-300;
  border-radius: $border-radius-full;
}

.kanban-container::-webkit-scrollbar-thumb:hover {
  background: $gray-400;
}
</style>
