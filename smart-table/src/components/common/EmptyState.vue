<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";

type EmptyType = "default" | "search" | "error" | "no-data" | "no-permission";

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    type?: EmptyType;
    title?: string;
    description?: string;
    icon?: string;
    actionText?: string;
  }>(),
  {
    type: "default",
  },
);

const emit = defineEmits<{
  action: [];
}>();

const defaultConfig: Record<
  EmptyType,
  { icon: string; titleKey: string; descKey: string }
> = {
  default: {
    icon: "📭",
    titleKey: "common.noData",
    descKey: "common.emptyDefaultDesc",
  },
  search: {
    icon: "🔍",
    titleKey: "common.emptySearchTitle",
    descKey: "common.emptySearchDesc",
  },
  error: {
    icon: "❌",
    titleKey: "common.emptyErrorTitle",
    descKey: "common.emptyErrorDesc",
  },
  "no-data": {
    icon: "📊",
    titleKey: "common.noData",
    descKey: "common.emptyNoDataDesc",
  },
  "no-permission": {
    icon: "🔒",
    titleKey: "common.emptyNoPermissionTitle",
    descKey: "common.emptyNoPermissionDesc",
  },
};

const config = computed(() => ({
  icon: props.icon || defaultConfig[props.type].icon,
  title: props.title || t(defaultConfig[props.type].titleKey),
  description: props.description || t(defaultConfig[props.type].descKey),
}));
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">{{ config.icon }}</div>
    <h3 class="empty-title">{{ config.title }}</h3>
    <p class="empty-description">{{ config.description }}</p>
    <button v-if="actionText" class="empty-action" @click="emit('action')">
      {{ actionText }}
    </button>
    <slot name="action" />
  </div>
</template>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  animation: float 3s ease-in-out infinite;
}

.empty-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-description {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 300px;
  margin-bottom: 16px;
}

.empty-action {
  padding: 8px 24px;
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background-color: color-mix(in srgb, var(--primary-color) 90%, black);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}
</style>
