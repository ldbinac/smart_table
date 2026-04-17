<script setup lang="ts">
import { computed } from "vue";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { ElTooltip, ElAvatar } from "element-plus";

const collaborationStore = useCollaborationStore();

const lockedCellsList = computed(() => {
  return Array.from(collaborationStore.lockedCells.entries()).map(
    ([key, info]) => ({
      key,
      ...info,
    }),
  );
});

const avatarColors = [
  "#3B82F6",
  "#EF4444",
  "#10B981",
  "#F59E0B",
  "#8B5CF6",
  "#EC4899",
];

function getColor(userId: string): string {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = userId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
}
</script>

<template>
  <div class="cell-editing-indicators">
    <div
      v-for="cell in lockedCellsList"
      :key="cell.key"
      class="cell-indicator"
      :style="{ borderColor: getColor(cell.user_id) }">
      <ElTooltip
        :content="`${cell.nickname || cell.name} 正在编辑`"
        placement="top"
        :show-after="300">
        <ElAvatar
          :size="16"
          :src="cell.avatar"
          :style="{ backgroundColor: getColor(cell.user_id) }"
          class="indicator-avatar">
          {{ (cell.nickname || cell.name) ? (cell.nickname || cell.name).charAt(0) : "?" }}
        </ElAvatar>
      </ElTooltip>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.cell-editing-indicators {
  position: relative;
  pointer-events: none;
}

.cell-indicator {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 2px solid;
  border-radius: 2px;
  pointer-events: none;
  z-index: 5;
}

.indicator-avatar {
  position: absolute;
  top: -8px;
  right: -8px;
  font-size: 10px;
  pointer-events: auto;
  cursor: default;
}
</style>
