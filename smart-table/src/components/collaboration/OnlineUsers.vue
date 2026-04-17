<script setup lang="ts">
import { computed } from "vue";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { ElTooltip, ElAvatar } from "element-plus";

const collaborationStore = useCollaborationStore();

const displayUsers = computed(() => {
  const users = Array.from(collaborationStore.onlineUsers.values());
  return users.slice(0, 5);
});

const overflowCount = computed(() => {
  const total = collaborationStore.onlineUsers.size;
  return total > 5 ? total - 5 : 0;
});

function getInitials(nickname: string): string {
  return nickname ? nickname.charAt(0).toUpperCase() : "?";
}

const avatarColors = [
  "#3B82F6",
  "#EF4444",
  "#10B981",
  "#F59E0B",
  "#8B5CF6",
  "#EC4899",
  "#06B6D4",
  "#84CC16",
];

function getAvatarColor(index: number): string {
  return avatarColors[index % avatarColors.length];
}
</script>

<template>
  <div class="online-users" v-if="collaborationStore.onlineUsers.size > 0">
    <div class="users-avatars">
      <ElTooltip
        v-for="(user, index) in displayUsers"
        :key="user.user_id"
        :content="`${user.nickname || user.name}${user.current_view ? ' - ' + user.current_view.view_type : ''}`"
        placement="bottom">
        <ElAvatar
          :size="28"
          :src="user.avatar"
          :style="{
            backgroundColor: user.avatar ? undefined : getAvatarColor(index),
            marginLeft: index > 0 ? '-6px' : '0',
            border: '2px solid #fff',
            zIndex: displayUsers.length - index,
          }">
          {{ getInitials(user.nickname || user.name) }}
        </ElAvatar>
      </ElTooltip>
      <div
        v-if="overflowCount > 0"
        class="overflow-badge"
        :style="{ marginLeft: displayUsers.length > 0 ? '-6px' : '0' }">
        +{{ overflowCount }}
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.online-users {
  display: flex;
  align-items: center;
}

.users-avatars {
  display: flex;
  align-items: center;
}

.overflow-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
  border: 2px solid #fff;
  position: relative;
  z-index: 0;
}
</style>
