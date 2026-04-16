<script setup lang="ts">
import { ref, computed } from "vue";
import { ElDialog, ElButton, ElDescriptions, ElDescriptionsItem, ElTag } from "element-plus";

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
  if (val === null || val === undefined) return "(空)";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}
</script>

<template>
  <ElDialog
    v-model="dialogVisible"
    title="编辑冲突"
    width="480px"
    :close-on-click-modal="false"
    :close-on-press-escape="false">
    <div class="conflict-content" v-if="conflict">
      <p class="conflict-description">
        {{ conflict.otherUserName }} 同时编辑了此字段，请选择保留哪个版本：
      </p>
      <ElDescriptions :column="1" border>
        <ElDescriptionsItem label="字段">
          <ElTag>{{ conflict.fieldName }}</ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="我的修改">
          <span class="value-mine">{{ formatValue(conflict.myValue) }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="对方的修改">
          <span class="value-theirs">{{ formatValue(conflict.otherValue) }}</span>
        </ElDescriptionsItem>
      </ElDescriptions>
    </div>
    <template #footer>
      <div class="conflict-actions">
        <ElButton @click="handleResolve('history')">查看历史版本</ElButton>
        <ElButton @click="handleResolve('theirs')">接受对方的修改</ElButton>
        <ElButton type="primary" @click="handleResolve('mine')">保留我的修改</ElButton>
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
