import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { shareApiService } from "@/services/api/shareApiService";
import { useAuthStore } from "./authStore";

export interface BaseMember {
  id: string;
  base_id: string;
  user_id: string;
  role: "owner" | "admin" | "editor" | "commenter" | "viewer";
  invited_by: string | null;
  joined_at: string;
  user?: {
    id: string;
    name: string;
    avatar?: string;
    email?: string;
  };
}

export const useMemberStore = defineStore("member", () => {
  const members = ref<BaseMember[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const currentBaseOwnerId = ref<string | null>(null);

  const currentUserRole = computed(() => {
    const authStore = useAuthStore();
    const currentUserId = authStore.user?.id;
    if (!currentUserId) return null;

    if (currentBaseOwnerId.value === currentUserId) {
      return "owner";
    }

    const member = members.value.find((m) => m.user_id === currentUserId);
    return member?.role || null;
  });

  const canEdit = computed(() => {
    const role = currentUserRole.value;
    return role === "owner" || role === "admin" || role === "editor";
  });

  const canView = computed(() => {
    const role = currentUserRole.value;
    return ["owner", "admin", "editor", "commenter", "viewer"].includes(role || "");
  });

  const canManage = computed(() => {
    const role = currentUserRole.value;
    return role === "owner" || role === "admin";
  });

  const isOwner = computed(() => {
    return currentUserRole.value === "owner";
  });

  function setCurrentBaseOwner(ownerId: string | null) {
    currentBaseOwnerId.value = ownerId;
  }

  async function fetchMembers(baseId: string) {
    loading.value = true;
    error.value = null;
    try {
      const data = await shareApiService.getMembers(baseId);
      members.value = data;
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "获取成员列表失败";
      error.value = msg;
      console.error("[memberStore] fetchMembers failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function addMember(baseId: string, email: string, role: string) {
    loading.value = true;
    try {
      const data = await shareApiService.addMember(baseId, email, role);
      members.value.push(data);
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "添加成员失败";
      error.value = msg;
      console.error("[memberStore] addMember failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function batchAddMembers(
    baseId: string,
    membersData: Array<{ email: string; role: string }>
  ) {
    loading.value = true;
    try {
      const result = await shareApiService.batchAddMembers(baseId, membersData);
      result.successful.forEach((member) => {
        members.value.push(member);
      });
      return result;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "批量添加成员失败";
      error.value = msg;
      console.error("[memberStore] batchAddMembers failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateMemberRole(baseId: string, userId: string, role: string) {
    loading.value = true;
    try {
      const data = await shareApiService.updateMemberRole(baseId, userId, role);
      const idx = members.value.findIndex((m) => m.user_id === userId);
      if (idx !== -1) {
        members.value[idx] = data;
      }
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "更新成员角色失败";
      error.value = msg;
      console.error("[memberStore] updateMemberRole failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function removeMember(baseId: string, userId: string) {
    loading.value = true;
    try {
      await shareApiService.removeMember(baseId, userId);
      members.value = members.value.filter((m) => m.user_id !== userId);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "移除成员失败";
      error.value = msg;
      console.error("[memberStore] removeMember failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function clearMembers() {
    members.value = [];
    currentBaseOwnerId.value = null;
  }

  function clearError() {
    error.value = null;
  }

  function $reset() {
    members.value = [];
    loading.value = false;
    error.value = null;
    currentBaseOwnerId.value = null;
  }

  return {
    members,
    loading,
    error,
    currentUserRole,
    canEdit,
    canView,
    canManage,
    isOwner,
    setCurrentBaseOwner,
    fetchMembers,
    addMember,
    batchAddMembers,
    updateMemberRole,
    removeMember,
    clearMembers,
    clearError,
    $reset,
  };
});
