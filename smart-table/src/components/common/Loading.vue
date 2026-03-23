<script setup lang="ts">
import { computed } from 'vue'

type LoadingSize = 'small' | 'medium' | 'large'

const props = withDefaults(defineProps<{
  size?: LoadingSize
  text?: string
  fullscreen?: boolean
  overlay?: boolean
}>(), {
  size: 'medium',
  text: '加载中...',
  fullscreen: false,
  overlay: true
})

const sizeMap = {
  small: 16,
  medium: 24,
  large: 40
}

const spinnerSize = computed(() => sizeMap[props.size])
</script>

<template>
  <div
    :class="[
      'loading-wrapper',
      {
        'loading-fullscreen': fullscreen,
        'loading-overlay': overlay
      }
    ]"
  >
    <div class="loading-content">
      <div
        class="loading-spinner"
        :style="{ width: `${spinnerSize}px`, height: `${spinnerSize}px` }"
      />
      <span v-if="text" class="loading-text">{{ text }}</span>
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

.loading-overlay {
  background-color: rgba(255, 255, 255, 0.8);
  
  :root.dark & {
    background-color: rgba(26, 26, 26, 0.8);
  }
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-spinner {
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-text {
  color: var(--text-secondary);
  font-size: 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
