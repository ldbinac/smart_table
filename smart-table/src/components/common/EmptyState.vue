<script setup lang="ts">
import { computed } from "vue";

type EmptyType = "default" | "search" | "error" | "no-data" | "no-permission";

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
  { icon: string; title: string; description: string }
> = {
  default: {
    icon: "📭",
    title: "暂无数据",
    description: "这里还没有任何内容",
  },
  search: {
    icon: "🔍",
    title: "未找到结果",
    description: "尝试使用不同的关键词搜索",
  },
  error: {
    icon: "❌",
    title: "加载失败",
    description: "数据加载出错，请稍后重试",
  },
  "no-data": {
    icon: "📊",
    title: "暂无数据",
    description: "点击下方按钮添加新数据",
  },
  "no-permission": {
    icon: "🔒",
    title: "无访问权限",
    description: "您没有权限查看此内容",
  },
};

const config = computed(() => ({
  icon: props.icon || defaultConfig[props.type].icon,
  title: props.title || defaultConfig[props.type].title,
  description: props.description || defaultConfig[props.type].description,
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
