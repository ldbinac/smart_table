<script setup lang="ts">
import { computed } from "vue";

type LoadingSize = "small" | "medium" | "large";

const props = withDefaults(
  defineProps<{
    size?: LoadingSize;
    text?: string;
    fullscreen?: boolean;
    overlay?: boolean;
    showProgress?: boolean;
    absolute?: boolean;
  }>(),
  {
    size: "medium",
    text: "加载中...",
    fullscreen: false,
    overlay: true,
    showProgress: true,
    absolute: false,
  },
);

const sizeMap = {
  small: 16,
  medium: 40,
  large: 50,
};

const spinnerSize = computed(() => sizeMap[props.size]);
</script>

<template>
  <div
    :class="[
      'loading-wrapper',
      {
        'loading-fullscreen': fullscreen,
        'loading-absolute': absolute,
        'loading-overlay': overlay,
      },
    ]">
    <div class="loading-content">
      <div
        class="loading-spinner"
        :style="{ width: `${spinnerSize}px`, height: `${spinnerSize}px` }" />
      <span v-if="text" class="loading-text">{{ text }}</span>
      <div v-if="showProgress" class="loading-progress">
        <div class="loading-bar"></div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.loading-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.loading-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9998;
}

.loading-absolute {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
}

.loading-overlay {
  background: rgba(255, 255, 255, 0.96);

  :root.dark & {
    background-color: rgba(26, 26, 26, 0.96);
  }
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.loading-spinner {
  border: 4px solid #f0f0f0;
  border-top: 4px solid var(--el-color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  font-size: 16px;
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.loading-progress {
  width: 200px;
  height: 4px;
  background: #f0f0f0;
  border-radius: 2px;
  overflow: hidden;
}

.loading-bar {
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, var(--el-color-primary), var(--el-color-primary-light-3), var(--el-color-primary));
  background-size: 200% 100%;
  animation: progress 1.5s ease-in-out infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes progress {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(300%);
  }
}
</style>
