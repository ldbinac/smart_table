import { defineStore } from "pinia";
import { ref } from "vue";
import type { Base } from "@/api/types";
import { shareApiService } from "@/services/api/shareApiService";

export interface BaseShare {
  id: string;
  base_id: string;
  share_token: string;
  created_by: string;
  permission: "view" | "edit";
  expires_at?: number;
  access_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_accessed_at?: string;
  base?: Base;
}

export const useShareStore = defineStore("share", () => {
  const shares = ref<BaseShare[]>([]);
  const sharedWithMe = ref<Base[]>([]);
  const sharedByMe = ref<BaseShare[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchShares(baseId: string) {
    loading.value = true;
    error.value = null;
    try {
      const data = await shareApiService.getShares(baseId);
      shares.value = data;
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "获取分享列表失败";
      error.value = msg;
      console.error("[shareStore] fetchShares failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createShare(
    baseId: string,
    permission: "view" | "edit",
    expiresAt?: number
  ) {
    loading.value = true;
    try {
      const data = await shareApiService.createShare(baseId, permission, expiresAt);
      shares.value.unshift(data);
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "创建分享链接失败";
      error.value = msg;
      console.error("[shareStore] createShare failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteShare(shareId: string) {
    loading.value = true;
    try {
      await shareApiService.deleteShare(shareId);
      shares.value = shares.value.filter((s) => s.id !== shareId);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "删除分享链接失败";
      error.value = msg;
      console.error("[shareStore] deleteShare failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateShare(shareId: string, data: Partial<BaseShare>) {
    loading.value = true;
    try {
      const updated = await shareApiService.updateShare(shareId, data);
      const idx = shares.value.findIndex((s) => s.id === shareId);
      if (idx !== -1) {
        shares.value[idx] = updated;
      }
      return updated;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "更新分享链接失败";
      error.value = msg;
      console.error("[shareStore] updateShare failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchSharedWithMe() {
    loading.value = true;
    error.value = null;
    try {
      const data = await shareApiService.getSharedWithMe();
      sharedWithMe.value = data;
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "获取分享给我的 Base 失败";
      error.value = msg;
      console.error("[shareStore] fetchSharedWithMe failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchSharedByMe() {
    loading.value = true;
    error.value = null;
    try {
      const data = await shareApiService.getSharedByMe();
      sharedByMe.value = data;
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "获取我创建的分享失败";
      error.value = msg;
      console.error("[shareStore] fetchSharedByMe failed:", e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function clearShares() {
    shares.value = [];
  }

  function clearError() {
    error.value = null;
  }

  function $reset() {
    shares.value = [];
    sharedWithMe.value = [];
    sharedByMe.value = [];
    loading.value = false;
    error.value = null;
  }

  return {
    shares,
    sharedWithMe,
    sharedByMe,
    loading,
    error,
    fetchShares,
    createShare,
    deleteShare,
    updateShare,
    fetchSharedWithMe,
    fetchSharedByMe,
    clearShares,
    clearError,
    $reset,
  };
});
