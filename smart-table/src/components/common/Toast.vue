<script setup lang="ts">
import { ref } from "vue";
import { TransitionGroup } from "vue";

export interface ToastMessage {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
  duration?: number;
}

const toasts = ref<ToastMessage[]>([]);

function addToast(toast: Omit<ToastMessage, "id">) {
  const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const newToast: ToastMessage = {
    ...toast,
    id,
    duration: toast.duration ?? 3000,
  };

  toasts.value.push(newToast);

  const duration = newToast.duration ?? 3000;
  if (duration > 0) {
    setTimeout(() => {
      removeToast(id);
    }, duration);
  }

  return id;
}

function removeToast(id: string) {
  const index = toasts.value.findIndex((t) => t.id === id);
  if (index !== -1) {
    toasts.value.splice(index, 1);
  }
}

function getIcon(type: ToastMessage["type"]) {
  const icons = {
    success: "✓",
    error: "✕",
    warning: "⚠",
    info: "ℹ",
  };
  return icons[type];
}

const toastMethods = {
  success: (title: string, message?: string) =>
    addToast({ type: "success", title, message }),
  error: (title: string, message?: string) =>
    addToast({ type: "error", title, message }),
  warning: (title: string, message?: string) =>
    addToast({ type: "warning", title, message }),
  info: (title: string, message?: string) =>
    addToast({ type: "info", title, message }),
};

defineExpose({
  addToast,
  removeToast,
  ...toastMethods,
});
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', `toast-${toast.type}`]">
          <span class="toast-icon">{{ getIcon(toast.type) }}</span>
          <div class="toast-content">
            <div class="toast-title">{{ toast.title }}</div>
            <div v-if="toast.message" class="toast-message">
              {{ toast.message }}
            </div>
          </div>
          <button class="toast-close" @click="removeToast(toast.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style lang="scss" scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--surface-color);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  border-left: 4px solid var(--primary-color);
}

.toast-success {
  border-left-color: var(--success-color);

  .toast-icon {
    color: var(--success-color);
  }
}

.toast-error {
  border-left-color: var(--error-color);

  .toast-icon {
    color: var(--error-color);
  }
}

.toast-warning {
  border-left-color: var(--warning-color);

  .toast-icon {
    color: var(--warning-color);
  }
}

.toast-info {
  border-left-color: var(--primary-color);

  .toast-icon {
    color: var(--primary-color);
  }
}

.toast-icon {
  font-size: 16px;
  font-weight: bold;
  flex-shrink: 0;
}

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 14px;
}

.toast-message {
  color: var(--text-secondary);
  font-size: 13px;
  margin-top: 4px;
}

.toast-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  font-size: 14px;
  line-height: 1;
  opacity: 0.6;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
}
</style>
