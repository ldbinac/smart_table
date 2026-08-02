<template>
  <div class="sub-table-toolbar">
    <div class="toolbar-left">
      <!-- 多 LINK 字段时显示切换下拉 -->
      <el-select
        v-if="hasMultipleLinkFields"
        :model-value="currentFieldId"
        size="small"
        class="field-switcher"
        @change="handleSwitchField"
      >
        <el-option
          v-for="field in linkFields"
          :key="field.fieldId"
          :label="field.fieldName"
          :value="field.fieldId"
        />
      </el-select>
      <span v-else class="field-label">
        {{ currentFieldName }}
      </span>
    </div>

    <div class="toolbar-right">
      <el-tooltip
        :content="addDisabledReason || '添加关联记录'"
        :disabled="!readonly && !disabledAdd"
      >
        <el-button
          size="small"
          type="primary"
          :icon="Plus"
          :disabled="readonly || disabledAdd"
          @click="handleAddLink"
        >
          添加关联
        </el-button>
      </el-tooltip>

      <el-button
        size="small"
        :icon="Refresh"
        :disabled="readonly"
        @click="handleRefresh"
      >
        刷新
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ElButton, ElSelect, ElOption, ElTooltip } from 'element-plus';
import { Plus, Refresh } from '@element-plus/icons-vue';

interface Props {
  linkFields: Array<{
    fieldId: string;
    fieldName: string;
    targetTableId: string;
    relationshipType: string;
  }>;
  currentFieldId: string | null;
  readonly: boolean;
  hasMultipleLinkFields: boolean;
  disabledAdd?: boolean;
  addDisabledReason?: string;
}

const props = withDefaults(defineProps<Props>(), {
  disabledAdd: false,
  addDisabledReason: '',
});

const emit = defineEmits<{
  (e: 'switch-field', fieldId: string): void;
  (e: 'add-link'): void;
  (e: 'refresh'): void;
}>();

const currentFieldName = computed(() => {
  const field = props.linkFields.find(f => f.fieldId === props.currentFieldId);
  return field?.fieldName || '';
});

function handleSwitchField(fieldId: string): void {
  emit('switch-field', fieldId);
}

function handleAddLink(): void {
  emit('add-link');
}

function handleRefresh(): void {
  emit('refresh');
}
</script>

<style scoped lang="scss">
.sub-table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background-color: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
  min-height: 36px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.field-switcher {
  width: 160px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
</style>
