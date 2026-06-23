import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { shareApiService } from "@/services/api/shareApiService";
import { apiClient } from "@/api/client";
import { useAuthStore } from "./authStore";
import type { FieldPermission } from "@/types/fields";
import type { FieldPermissionResponse } from "@/api/types";

export interface BaseMember {
  id: string;
  base_id: string;
  user_id: string;
  role: "owner" | "admin" | "editor" | "commenter" | "viewer";
  invited_by: string | null | undefined;
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

  // ==================== 字段权限状态 ====================
  // 字段权限缓存：{ [fieldId]: 'read' | 'write' | 'none' }
  const fieldPermissions = ref<Record<string, FieldPermission>>({});
  // 当前已加载权限的表 ID（用于判断缓存是否对应当前表）
  const currentPermissionsTableId = ref<string | null>(null);

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
      members.value = data as any;
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
      members.value.push(data as any);
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
        members.value.push(member as any);
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
        members.value[idx] = data as any;
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

  // ==================== 字段权限方法 ====================

  /**
   * 加载指定表的字段权限
   * 调用 GET /tables/{tableId}/field-permissions 获取权限映射
   * 成功时更新缓存，失败时清空缓存并记录日志
   */
  async function loadFieldPermissions(tableId: string) {
    if (!tableId) return;
    try {
      const data = await apiClient.get<FieldPermissionResponse>(
        `/tables/${tableId}/field-permissions`
      );
      fieldPermissions.value = { ...(data || {}) };
      currentPermissionsTableId.value = tableId;
    } catch (e: unknown) {
      console.error("[memberStore] loadFieldPermissions failed:", e);
      fieldPermissions.value = {};
      currentPermissionsTableId.value = null;
    }
  }

  /**
   * 获取单个字段的权限
   * 缓存命中返回缓存值；缓存未命中返回 'write'（乐观默认，避免阻塞渲染）
   */
  function getFieldPermission(fieldId: string): FieldPermission {
    return fieldPermissions.value[fieldId] ?? "write";
  }

  /**
   * 判断字段是否可编辑（权限为 write）
   */
  function canEditField(fieldId: string): boolean {
    return getFieldPermission(fieldId) === "write";
  }

  /**
   * 判断字段是否可读（权限为 read 或 write）
   */
  function canReadField(fieldId: string): boolean {
    const perm = getFieldPermission(fieldId);
    return perm === "read" || perm === "write";
  }

  /**
   * 清空字段权限缓存（Base/表切换时调用）
   */
  function clearFieldPermissions() {
    fieldPermissions.value = {};
    currentPermissionsTableId.value = null;
  }

  /**
   * 更新单个字段权限（本地缓存，用于配置后立即生效）
   */
  function updateFieldPermission(fieldId: string, permission: FieldPermission) {
    fieldPermissions.value = { ...fieldPermissions.value, [fieldId]: permission };
  }

  function clearError() {
    error.value = null;
  }

  function $reset() {
    members.value = [];
    loading.value = false;
    error.value = null;
    currentBaseOwnerId.value = null;
    fieldPermissions.value = {};
    currentPermissionsTableId.value = null;
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
    // 字段权限
    fieldPermissions,
    currentPermissionsTableId,
    loadFieldPermissions,
    getFieldPermission,
    canEditField,
    canReadField,
    clearFieldPermissions,
    updateFieldPermission,
    // 通用
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
