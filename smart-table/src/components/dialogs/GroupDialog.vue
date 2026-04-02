<script setup lang="ts">
import { ref, watch, computed } from "vue";
import {
  ElDialog,
  ElButton,
  ElSelect,
  ElOption,
  ElTag,
  ElMessage,
} from "element-plus";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";

const props = defineProps<{
  visible: boolean;
  fields: FieldEntity[];
  initialGroupBy?: string[];
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  apply: [groupBy: string[]];
  clear: [];
}>();

// 最大分组层级数
const MAX_GROUP_LEVELS = 3;

const groupBy = ref<string[]>([]);

// 可分组字段类型
const groupableFieldTypes = [
  FieldType.SINGLE_SELECT,
  FieldType.MULTI_SELECT,
  FieldType.CHECKBOX,
  FieldType.DATE,
  FieldType.CREATED_TIME,
  FieldType.UPDATED_TIME,
  FieldType.MEMBER,
  FieldType.TEXT,
  FieldType.NUMBER,
];

// 可分组字段列表
const groupableFields = computed(() => {
  return props.fields.filter((f) =>
    groupableFieldTypes.includes(f.type as any),
  );
});

// 是否已达到最大分组层级
const isMaxLevelReached = computed(() => {
  return groupBy.value.length >= MAX_GROUP_LEVELS;
});

// 获取字段图标
function getFieldIcon(field: FieldEntity) {
  switch (field.type) {
    case FieldType.SINGLE_SELECT:
    case FieldType.MULTI_SELECT:
      return "CollectionTag";
    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return "Calendar";
    case FieldType.CHECKBOX:
      return "Check";
    case FieldType.MEMBER:
      return "User";
    case FieldType.NUMBER:
      return "Sort";
    default:
      return "Document";
  }
}

// 获取字段名称
function getFieldName(fieldId: string) {
  const field = props.fields.find((f) => f.id === fieldId);
  return field?.name || fieldId;
}

// 添加分组字段
function addGroupField() {
  if (isMaxLevelReached.value) {
    ElMessage.warning(`最多支持 ${MAX_GROUP_LEVELS} 级分组`);
    return;
  }

  const availableField = groupableFields.value.find(
    (f) => !groupBy.value.includes(f.id),
  );
  if (!availableField) return;

  groupBy.value.push(availableField.id);
}

// 移除分组字段
function removeGroupField(index: number) {
  groupBy.value.splice(index, 1);
}

// 移动分组字段顺序
function moveGroupField(index: number, direction: "up" | "down") {
  if (direction === "up" && index > 0) {
    const temp = groupBy.value[index];
    groupBy.value[index] = groupBy.value[index - 1];
    groupBy.value[index - 1] = temp;
  } else if (direction === "down" && index < groupBy.value.length - 1) {
    const temp = groupBy.value[index];
    groupBy.value[index] = groupBy.value[index + 1];
    groupBy.value[index + 1] = temp;
  }
}

// 获取可用字段（排除已选择的）
function getAvailableFields(currentIndex: number) {
  const usedFieldIds = groupBy.value.filter(
    (_, index) => index !== currentIndex,
  );
  return groupableFields.value.filter((f) => !usedFieldIds.includes(f.id));
}

// 应用分组配置
function applyGroups() {
  emit("apply", [...groupBy.value]);
  emit("update:visible", false);
}

// 清除分组配置
function clearGroups() {
  groupBy.value = [];
  emit("clear");
  emit("update:visible", false);
}

// 监听弹窗显示状态和初始值变化
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      groupBy.value = props.initialGroupBy ? [...props.initialGroupBy] : [];
    }
  },
);

// 监听 initialGroupBy 变化，确保切换数据表时配置正确更新
watch(
  () => props.initialGroupBy,
  (newGroupBy) => {
    // 只有在弹窗打开时才更新，避免关闭时覆盖用户输入
    if (props.visible) {
      groupBy.value = newGroupBy ? [...newGroupBy] : [];
    }
  },
  { deep: true },
);
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="分组"
    width="500px"
    :close-on-click-modal="false">
    <div class="group-dialog">
      <!-- 分组字段列表 -->
      <div class="groups-list">
        <div v-for="(fieldId, index) in groupBy" :key="index" class="group-row">
          <span class="group-priority">{{ index + 1 }}</span>

          <!-- 字段选择 -->
          <ElSelect
            v-model="groupBy[index]"
            placeholder="选择字段"
            style="width: 200px">
            <ElOption
              v-for="field in getAvailableFields(index)"
              :key="field.id"
              :label="field.name"
              :value="field.id">
              <el-icon style="margin-right: 8px">
                <component :is="getFieldIcon(field)" />
              </el-icon>
              {{ field.name }}
            </ElOption>
            <ElOption
              v-if="props.fields.find((f) => f.id === fieldId)"
              :key="fieldId"
              :label="getFieldName(fieldId)"
              :value="fieldId" />
          </ElSelect>

          <!-- 层级指示 -->
          <span class="level-indicator">
            {{
              index === 0 ? "一级分组" : index === 1 ? "二级分组" : "三级分组"
            }}
          </span>

          <!-- 操作按钮 -->
          <div class="group-actions">
            <ElButton
              link
              :disabled="index === 0"
              @click="moveGroupField(index, 'up')">
              ↑
            </ElButton>
            <ElButton
              link
              :disabled="index === groupBy.length - 1"
              @click="moveGroupField(index, 'down')">
              ↓
            </ElButton>
            <ElButton link type="danger" @click="removeGroupField(index)">
              删除
            </ElButton>
          </div>
        </div>
      </div>

      <!-- 添加分组按钮 -->
      <ElButton
        v-if="!isMaxLevelReached && groupableFields.length > groupBy.length"
        link
        type="primary"
        class="add-group-btn"
        @click="addGroupField">
        + 添加分组字段
      </ElButton>
      <div v-else-if="isMaxLevelReached" class="limit-hint">
        已达到最大分组层级（{{ MAX_GROUP_LEVELS }}级）
      </div>

      <!-- 已选字段预览 -->
      <div v-if="groupBy.length > 0" class="group-preview">
        <div class="preview-label">当前分组：</div>
        <div class="preview-tags">
          <ElTag
            v-for="(fieldId, index) in groupBy"
            :key="index"
            size="small"
            closable
            @close="removeGroupField(index)">
            {{ index + 1 }}. {{ getFieldName(fieldId) }}
          </ElTag>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="groupBy.length === 0" class="empty-group">
        <p>暂无分组配置</p>
        <p class="hint">点击上方按钮添加分组字段，最多支持3级分组</p>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <ElButton @click="$emit('update:visible', false)">取消</ElButton>
        <ElButton link type="danger" @click="clearGroups">清除分组</ElButton>
        <ElButton type="primary" @click="applyGroups">应用分组</ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.group-dialog {
  .groups-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
  }

  .group-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    background-color: $bg-color;
    border-radius: $border-radius-md;

    .group-priority {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: $primary-color;
      color: white;
      border-radius: 50%;
      font-size: 12px;
      font-weight: 500;
    }

    .level-indicator {
      font-size: $font-size-xs;
      color: $text-secondary;
      white-space: nowrap;
    }

    .group-actions {
      display: flex;
      gap: 4px;
      margin-left: auto;
    }
  }

  .add-group-btn {
    margin-bottom: 16px;
  }

  .limit-hint {
    font-size: $font-size-sm;
    color: $warning-color;
    margin-bottom: 16px;
  }

  .group-preview {
    padding-top: 12px;
    border-top: 1px solid $border-color;

    .preview-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-bottom: 8px;
    }

    .preview-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
  }

  .empty-group {
    text-align: center;
    padding: 32px;
    color: $text-secondary;

    p {
      margin: 0;
    }

    .hint {
      font-size: $font-size-sm;
      margin-top: 8px;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
