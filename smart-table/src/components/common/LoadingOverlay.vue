<script setup lang="ts">
interface Props {
  visible: boolean
  recordCount: number
  actionText?: string
}

withDefaults(defineProps<Props>(), {
  actionText: '删除',
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="loading-overlay">
        <div class="loading-card">
          <div class="spinner">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="50" stroke-dashoffset="0" />
            </svg>
          </div>
          <p class="loading-text">正在{{ actionText }} {{ recordCount }} 条记录，请稍候...</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.loading-overlay {
  position: fixed;
  inset: 0;
  z-index: $z-index-modal;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.45);
}

.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-xl;
  padding: $spacing-4xl $spacing-4xl;
  background-color: $surface-color;
  border-radius: 12px;
  box-shadow: $shadow-lg;
}

.spinner {
  width: 48px;
  height: 48px;
  color: $primary-color;
  animation: spin 0.8s linear infinite;

  svg {
    width: 100%;
    height: 100%;
  }
}

.loading-text {
  font-size: $font-size-lg;
  color: $text-primary;
  margin: 0;
  white-space: nowrap;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>