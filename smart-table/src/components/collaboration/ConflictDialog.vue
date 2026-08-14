<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { ElDialog, ElButton, ElDescriptions, ElDescriptionsItem, ElTag } from "element-plus";

const { t } = useI18n();

export interface ConflictInfo {
  fieldName: string;
  fieldId: string;
  recordId: string;
  myValue: unknown;
  otherValue: unknown;
  otherUserName: string;
}

const props = defineProps<{
  visible: boolean;
  conflict: ConflictInfo | null;
}>();

const emit = defineEmits<{
  (e: "resolve", choice: "mine" | "theirs" | "history"): void;
  (e: "update:visible", value: boolean): void;
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit("update:visible", val),
});

function handleResolve(choice: "mine" | "theirs" | "history") {
  emit("resolve", choice);
  dialogVisible.value = false;
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return t("collaboration.conflictEmpty");
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}
</script>

<template>
  <ElDialog
    v-model="dialogVisible"
    :title="t('collaboration.conflictDialogTitle')"
    width="480px"
    :close-on-click-modal="false"
    :close-on-press-escape="false">
    <div class="conflict-content" v-if="conflict">
      <p class="conflict-description">
        {{ t('collaboration.conflictEditedDesc', { user: conflict.otherUserName }) }}
      </p>
      <ElDescriptions :column="1" border>
        <ElDescriptionsItem :label="t('collaboration.conflictField')">
          <ElTag>{{ conflict.fieldName }}</ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem :label="t('collaboration.conflictMyChanges')">
          <span class="value-mine">{{ formatValue(conflict.myValue) }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem :label="t('collaboration.conflictOtherChanges')">
          <span class="value-theirs">{{ formatValue(conflict.otherValue) }}</span>
        </ElDescriptionsItem>
      </ElDescriptions>
    </div>
    <template #footer>
      <div class="conflict-actions">
        <ElButton @click="handleResolve('history')">{{ t('collaboration.conflictViewHistory') }}</ElButton>
        <ElButton @click="handleResolve('theirs')">{{ t('collaboration.conflictAcceptTheirs') }}</ElButton>
        <ElButton type="primary" @click="handleResolve('mine')">{{ t('collaboration.conflictKeepMine') }}</ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style lang="scss" scoped>
.conflict-description {
  margin-bottom: 16px;
  color: #6b7280;
  font-size: 14px;
}

.value-mine {
  color: #3b82f6;
  font-weight: 500;
}

.value-theirs {
  color: #ef4444;
  font-weight: 500;
}

.conflict-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
