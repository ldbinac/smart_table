<template>
  <div class="parent-field-config">
    <div class="config-item">
      <label class="config-label">{{ t("view.parentRecordField") }}</label>
      <el-select
        v-model="selectedFieldId"
        :placeholder="t('view.selectParentField')"
        clearable
        @change="handleChange"
        style="width: 100%">
        <el-option
          v-for="field in selfLinkFields"
          :key="field.id"
          :label="field.name"
          :value="field.id" />
      </el-select>
      <div class="config-hint" v-if="!selectedFieldId">
        {{ t("view.parentFieldHintEmpty") }}
      </div>
      <div class="config-hint" v-else>
        {{ t("view.parentFieldHintActive") }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useTableStore } from "@/stores/tableStore";
import { useViewStore } from "@/stores/viewStore";
import { FieldType } from "@/types/fields";

const props = defineProps<{
  viewId: string;
  tableId: string;
  currentParentFieldId?: string | null;
}>();

const tableStore = useTableStore();
const viewStore = useViewStore();
const { t } = useI18n();

const selectedFieldId = ref<string | null>(props.currentParentFieldId || null);

// Find all self-referencing LINK_TO_RECORD fields in the current table
const selfLinkFields = computed(() => {
  return tableStore.fields.filter((field) => {
    if (field.type !== FieldType.LINK) return false;
    // Check if the field links to the current table (self-referencing)
    const config = field.config || field.options || {};
    const linkedTableId = config.linkedTableId || config.linked_table_id;
    return linkedTableId === props.tableId;
  });
});

watch(() => props.currentParentFieldId, (val) => {
  selectedFieldId.value = val || null;
});

const handleChange = async (val: string | null) => {
  await viewStore.updateParentField(props.viewId, val);
};
</script>

<style scoped>
.parent-field-config {
  padding: 12px 0;
}
.config-item {
  margin-bottom: 12px;
}
.config-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--el-text-color-primary);
}
.config-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}
</style>