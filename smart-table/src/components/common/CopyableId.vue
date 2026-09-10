<script setup lang="ts">
import { computed } from "vue";
import { ElMessage } from "element-plus";
import { DocumentCopy } from "@element-plus/icons-vue";
import { useI18n } from "vue-i18n";
import { copyToClipboard } from "@/utils/feedback";

/**
 * 可点击复制的 ID / 变量引用展示。
 *
 * 工作流模板变量（如 {{node_outputs.<node_id>.result}}、{{record.<field_id>}}）
 * 依赖节点 ID 与字段 ID，但这些 ID 此前在界面上不可见。该组件统一以等宽小字展示 ID，
 * 并支持点击一键复制，避免在配置工作流时靠抓包或查看 DOM 获取 ID。
 */
interface Props {
  /** 点击时写入剪贴板的文本（节点 ID / 字段 ID / 完整变量引用语法） */
  text: string;
  /** 展示文本，默认与 text 一致 */
  display?: string;
  /** 紧凑模式：不显示复制图标，hover 时才出现（用于节点卡片等窄容器） */
  compact?: boolean;
  /** 自定义 tooltip，默认使用「点击复制：xxx」 */
  tooltip?: string;
}

const props = withDefaults(defineProps<Props>(), {
  display: undefined,
  compact: false,
  tooltip: undefined,
});

const { t } = useI18n();

const displayText = computed(() => props.display ?? props.text);
const titleText = computed(() => props.tooltip ?? t("common.clickToCopy", { value: props.text }));

async function handleCopy() {
  const ok = await copyToClipboard(props.text);
  if (ok) {
    ElMessage.success(t("common.copied", { value: props.text }));
  } else {
    ElMessage.warning(t("common.copyFailed"));
  }
}
</script>

<template>
  <span
    class="copyable-id"
    :class="{ 'is-compact': compact }"
    :title="titleText"
    @click.stop="handleCopy">
    <code class="copyable-id-text">{{ displayText }}</code>
    <el-icon class="copyable-id-icon"><DocumentCopy /></el-icon>
  </span>
</template>

<style lang="scss" scoped>
.copyable-id {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  max-width: 100%;
  cursor: pointer;
  border-radius: $border-radius-sm;
  transition: background-color 0.15s, color 0.15s;

  &:hover {
    background-color: rgba($primary-color, 0.08);

    .copyable-id-text {
      color: $primary-color;
    }

    .copyable-id-icon {
      opacity: 1;
    }
  }
}

.copyable-id-text {
  min-width: 0;
  overflow: hidden;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: $font-size-xs;
  line-height: 1.4;
  color: $text-secondary;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.copyable-id-icon {
  flex-shrink: 0;
  font-size: 12px;
  color: $text-secondary;
  opacity: 0;
  transition: opacity 0.15s;
}

/* 紧凑模式（节点卡片等窄容器）：图标常驻，避免 hover 才能发现可复制 */
.is-compact {
  .copyable-id-icon {
    opacity: 0.45;
  }
}
</style>
