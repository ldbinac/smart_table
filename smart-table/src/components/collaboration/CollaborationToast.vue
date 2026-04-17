<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { realtimeEventEmitter } from "@/services/realtime/eventEmitter";
import type {
  PresenceUserJoinedBroadcast,
  PresenceUserLeftBroadcast,
} from "@/services/realtime/eventTypes";

interface ToastItem {
  id: number;
  message: string;
  type: "info" | "success" | "warning";
}

const collaborationStore = useCollaborationStore();
const toasts = ref<ToastItem[]>([]);
let toastId = 0;

function addToast(message: string, type: ToastItem["type"] = "info") {
  const id = ++toastId;
  toasts.value.push({ id, message, type });
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }, 3000);
}

function handleUserJoined(data: PresenceUserJoinedBroadcast) {
  addToast(`${data.nickname || data.name} 加入了协作`, "info");
}

function handleUserLeft(data: PresenceUserLeftBroadcast) {
  addToast(`${data.nickname || data.name} 离开了协作`, "warning");
}

onMounted(() => {
  if (collaborationStore.isRealtimeAvailable) {
    realtimeEventEmitter.on("presence:user_joined", handleUserJoined);
    realtimeEventEmitter.on("presence:user_left", handleUserLeft);
  }
});

onBeforeUnmount(() => {
  realtimeEventEmitter.off("presence:user_joined", handleUserJoined);
  realtimeEventEmitter.off("presence:user_left", handleUserLeft);
});
</script>

<template>
  <div class="collaboration-toast" v-if="toasts.length > 0">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast-item"
        :class="toast.type">
        {{ toast.message }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style lang="scss" scoped>
.collaboration-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column-reverse;
  gap: 8px;
  pointer-events: none;
}

.toast-item {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  white-space: nowrap;
  pointer-events: auto;

  &.info {
    background: #3b82f6;
  }

  &.success {
    background: #10b981;
  }

  &.warning {
    background: #f59e0b;
  }
}

.toast-enter-active {
  transition: all 0.3s ease;
}

.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
</style>
