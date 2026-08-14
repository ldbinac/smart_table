<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { ElMessage } from "element-plus";

const { t } = useI18n();
const collaborationStore = useCollaborationStore();

const statusConfig = computed(() => {
  switch (collaborationStore.connectionStatus) {
    case "connected":
      return { dotClass: "status-dot connected", label: t("collaboration.connected") };
    case "connecting":
      return { dotClass: "status-dot connecting", label: t("collaboration.connecting") };
    case "reconnecting":
      return { dotClass: "status-dot reconnecting", label: t("collaboration.reconnecting") };
    case "disconnected":
      return { dotClass: "status-dot disconnected", label: t("collaboration.disconnected") };
    default:
      return { dotClass: "status-dot disconnected", label: t("collaboration.notConnected") };
  }
});

const showDisconnectedBanner = computed(
  () =>
    collaborationStore.connectionStatus === "disconnected" ||
    collaborationStore.connectionStatus === "reconnecting",
);

const previousStatus = ref(collaborationStore.connectionStatus);

watch(
  () => collaborationStore.connectionStatus,
  (newStatus, oldStatus) => {
    if (oldStatus === "reconnecting" && newStatus === "connected") {
      ElMessage.success(t("collaboration.reconnected"));
    }
    previousStatus.value = newStatus;
  },
);
</script>

<template>
  <div class="connection-status-bar">
    <div class="status-indicator" :class="{ 'has-banner': showDisconnectedBanner }">
      <span :class="statusConfig.dotClass"></span>
      <span class="status-label">{{ statusConfig.label }}</span>
    </div>
    <div v-if="showDisconnectedBanner" class="disconnected-banner">
      <span class="banner-icon">⚠</span>
      <span>{{ t('collaboration.connectionLostRetrying') }}</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.connection-status-bar {
  display: flex;
  flex-direction: column;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.8);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;

  &.connected {
    background-color: #10b981;
    box-shadow: 0 0 4px rgba(16, 185, 129, 0.5);
  }

  &.connecting {
    background-color: #f59e0b;
    animation: pulse 1.5s ease-in-out infinite;
  }

  &.reconnecting {
    background-color: #f59e0b;
    animation: pulse 1s ease-in-out infinite;
  }

  &.disconnected {
    background-color: #ef4444;
  }
}

.status-label {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.disconnected-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #fef3c7;
  border-bottom: 1px solid #f59e0b;
  font-size: 13px;
  color: #92400e;
}

.banner-icon {
  font-size: 14px;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
</style>
