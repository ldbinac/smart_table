<script setup lang="ts">
withDefaults(defineProps<{
  width?: string
  height?: string
  circle?: boolean
  rows?: number
  animated?: boolean
}>(), {
  width: '100%',
  height: '16px',
  circle: false,
  rows: 1,
  animated: true
})
</script>

<template>
  <div class="skeleton-wrapper">
    <div
      v-for="i in rows"
      :key="i"
      class="skeleton"
      :class="{ 'skeleton-animated': animated, 'skeleton-circle': circle }"
      :style="{
        width: circle ? height : width,
        height: height,
        borderRadius: circle ? '50%' : undefined
      }"
    />
  </div>
</template>

<style lang="scss" scoped>
.skeleton-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton {
  background: linear-gradient(
    90deg,
    var(--border-color) 25%,
    var(--surface-color) 50%,
    var(--border-color) 75%
  );
  background-size: 200% 100%;
}

.skeleton-animated {
  animation: skeleton-loading 1.5s ease-in-out infinite;
}

.skeleton-circle {
  border-radius: 50%;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
