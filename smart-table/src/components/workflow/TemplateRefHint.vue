<script setup lang="ts">
import { useI18n } from "vue-i18n";
import CopyableId from "@/components/common/CopyableId.vue";

/**
 * 模板变量引用提示行。
 *
 * 工作流模板（字段映射值、邮件正文、Webhook body 等）使用 {{record.<field_id>}}、
 * {{node_outputs.<node_id>.result}} 这类语法引用数据。此前界面只给出占位说明，
 * 用户必须自己去找 ID，这里直接列出当前上下文可用的引用语法，点击即可复制。
 */
interface Props {
  /** 可复制的变量引用语法列表 */
  refs: string[];
}

defineProps<Props>();

const { t } = useI18n();
</script>

<template>
  <div v-if="refs.length" class="template-ref-hint">
    <span class="ref-hint-label">{{ t('workflow.nodeConfig.templateRefHint') }}</span>
    <CopyableId
      v-for="ref in refs"
      :key="ref"
      :text="ref"
      class="ref-hint-item" />
  </div>
</template>

<style lang="scss" scoped>
.template-ref-hint {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $spacing-xs $spacing-sm;
  margin-top: $spacing-xs;
  padding: 4px 6px;
  background-color: $bg-color;
  border-radius: $border-radius-sm;
}

.ref-hint-label {
  flex-shrink: 0;
  font-size: $font-size-xs;
  color: $text-secondary;
}

.ref-hint-item {
  max-width: 100%;
}
</style>
