<script setup lang="ts">
/** 插件类型标签（ui / script） */
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { PluginType } from "@/plugins/types";

const props = withDefaults(defineProps<{ type: PluginType }>(), {
  type: "ui",
});

const { t } = useI18n();

const tagType = computed(() => (props.type === "script" ? "warning" : "primary"));
const label = computed(() => t(`plugin.type.${props.type}`));
</script>

<template>
  <el-tag :type="tagType" size="small" effect="plain">{{ label }}</el-tag>
</template>
