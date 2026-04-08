import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Base } from '@/api/types';

import { baseApiService } from '@/services/api/baseApiService';
import { baseService as baseDexieService } from '@/db/services/baseService';
import { shareApiService } from '@/services/api/shareApiService';

export interface BaseMember {
  id: string;
  base_id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'editor' | 'commenter' | 'viewer';
  invited_by: string | null;
  joined_at: string;
  user?: {
    id: string;
    name: string;
    avatar?: string;
    email?: string;
  };
}

export interface BaseShare {
  id: string;
  base_id: string;
  share_token: string;
  created_by: string;
  permission: 'view' | 'edit';
  expires_at?: number;
  access_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_accessed_at?: string;
  base?: Base;
}

export const useBaseStore = defineStore('base', () => {
  const currentBaseId = ref<string | null>(null);
  const currentBase = ref<Base | null>(null);
  const bases = ref<Base[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // 成员管理相关 state
  const members = ref<BaseMember[]>([]);
  const shares = ref<BaseShare[]>([]);
  const sharedWithMe = ref<Base[]>([]);
  const sharedByMe = ref<BaseShare[]>([]);

  const sortedBases = computed(() => {
    return [...bases.value].sort((a, b) => {
      if (a.is_starred && !b.is_starred) return -1;
      if (!a.is_starred && b.is_starred) return 1;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  });

  const starredBases = computed(() => {
    return sortedBases.value.filter(b => b.is_starred);
  });

  async function fetchBases() {
    loading.value = true;
    error.value = null;
    try {
      const data = await baseApiService.getBases();
      bases.value = data;
      for (const base of data) {
        await baseDexieService.updateBase(base.id, base as Record<string, unknown>).catch(() => {});
      }
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取 Base 列表失败';
      error.value = msg;
      console.error('[baseStore] fetchBases failed:', e);
      try {
        const cached = await baseDexieService.getAllBases();
        if (cached.length > 0) {
          bases.value = cached.map(b => ({
            id: b.id,
            name: b.name,
            description: b.description,
            owner_id: '',
            icon: b.icon,
            color: b.color,
            is_personal: false,
            is_starred: !!b.isStarred,
            created_at: new Date(b.createdAt).toISOString(),
            updated_at: new Date(b.updatedAt).toISOString()
          }));
          return bases.value;
        }
      } catch {}
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchBase(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const data = await baseApiService.getBase(id);
      currentBase.value = data;
      currentBaseId.value = id;
      await baseDexieService.updateBase(id, data as Record<string, unknown>).catch(() => {});
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取 Base 详情失败';
      error.value = msg;
      console.error('[baseStore] fetchBase failed:', e);
      try {
        const cached = await baseDexieService.getBase(id);
        if (cached) {
          const mapped: Base = {
            id: cached.id,
            name: cached.name,
            description: cached.description,
            owner_id: '',
            icon: cached.icon,
            color: cached.color,
            is_personal: false,
            is_starred: !!cached.isStarred,
            created_at: new Date(cached.createdAt).toISOString(),
            updated_at: new Date(cached.updatedAt).toISOString()
          };
          currentBase.value = mapped;
          currentBaseId.value = id;
          return mapped;
        }
      } catch {}
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createBase(baseData: Omit<Base, 'id' | 'created_at' | 'updated_at'>): Promise<Base> {
    loading.value = true;
    try {
      const newBase = await baseApiService.createBase(baseData);
      bases.value.push(newBase);
      await baseDexieService.createBase({
        name: newBase.name,
        description: newBase.description,
        icon: newBase.icon,
        color: newBase.color
      }).catch(() => {});
      return newBase;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '创建 Base 失败';
      error.value = msg;
      console.error('[baseStore] createBase failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateBase(
    id: string,
    updates: Partial<Pick<Base, 'name' | 'description' | 'icon' | 'color' | 'is_personal'>>
  ): Promise<Base> {
    loading.value = true;
    try {
      const updated = await baseApiService.updateBase(id, updates);
      const idx = bases.value.findIndex(b => b.id === id);
      if (idx !== -1) {
        bases.value[idx] = updated;
      }
      if (currentBase.value?.id === id) {
        currentBase.value = updated;
      }
      await baseDexieService.updateBase(id, updates as Record<string, unknown>);
      return updated;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '更新 Base 失败';
      error.value = msg;
      console.error('[baseStore] updateBase failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteBase(id: string): Promise<void> {
    loading.value = true;
    try {
      await baseApiService.deleteBase(id);
      bases.value = bases.value.filter(b => b.id !== id);
      if (currentBase.value?.id === id) {
        currentBase.value = null;
        currentBaseId.value = null;
      }
      await baseDexieService.deleteBase(id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '删除 Base 失败';
      error.value = msg;
      console.error('[baseStore] deleteBase failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function toggleStar(id: string): Promise<void> {
    const base = bases.value.find(b => b.id === id);
    if (!base) return;

    try {
      if (base.is_starred) {
        await baseApiService.unstarBase(id);
        base.is_starred = false;
      } else {
        await baseApiService.starBase(id);
        base.is_starred = true;
      }
      if (currentBase.value?.id === id) {
        currentBase.value.is_starred = base.is_starred;
      }
      await baseDexieService.toggleStar(id);
    } catch (e: unknown) {
      console.error('[baseStore] toggleStar failed:', e);
    }
  }

  function setCurrentBase(base: Base | null) {
    currentBase.value = base;
    currentBaseId.value = base?.id ?? null;
  }

  function clearError() {
    error.value = null;
  }

  function $reset() {
    currentBaseId.value = null;
    currentBase.value = null;
    bases.value = [];
    loading.value = false;
    error.value = null;
    members.value = [];
    shares.value = [];
    sharedWithMe.value = [];
    sharedByMe.value = [];
  }

  // ==================== 成员管理相关 methods ====================

  async function fetchMembers(baseId: string) {
    loading.value = true;
    error.value = null;
    try {
      const data = await shareApiService.getMembers(baseId);
      members.value = data;
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取成员列表失败';
      error.value = msg;
      console.error('[baseStore] fetchMembers failed:', e);
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
      const msg = e instanceof Error ? e.message : '添加成员失败';
      error.value = msg;
      console.error('[baseStore] addMember failed:', e);
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
      // 添加成功的成员到列表
      result.successful.forEach(member => {
        members.value.push(member);
      });
      return result;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '批量添加成员失败';
      error.value = msg;
      console.error('[baseStore] batchAddMembers failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateMemberRole(baseId: string, userId: string, role: string) {
    loading.value = true;
    try {
      const data = await shareApiService.updateMemberRole(baseId, userId, role);
      const idx = members.value.findIndex(m => m.user_id === userId);
      if (idx !== -1) {
        members.value[idx] = data;
      }
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '更新成员角色失败';
      error.value = msg;
      console.error('[baseStore] updateMemberRole failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function removeMember(baseId: string, userId: string) {
    loading.value = true;
    try {
      await shareApiService.removeMember(baseId, userId);
      members.value = members.value.filter(m => m.user_id !== userId);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '移除成员失败';
      error.value = msg;
      console.error('[baseStore] removeMember failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  // ==================== 分享管理相关 methods ====================

  async function fetchShares(baseId: string) {
    loading.value = true;
    error.value = null;
    try {
      const data = await shareApiService.getShares(baseId);
      shares.value = data;
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取分享列表失败';
      error.value = msg;
      console.error('[baseStore] fetchShares failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createShare(baseId: string, permission: 'view' | 'edit', expiresAt?: number) {
    loading.value = true;
    try {
      const data = await shareApiService.createShare(baseId, permission, expiresAt);
      shares.value.unshift(data);
      return data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '创建分享链接失败';
      error.value = msg;
      console.error('[baseStore] createShare failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteShare(shareId: string) {
    loading.value = true;
    try {
      await shareApiService.deleteShare(shareId);
      shares.value = shares.value.filter(s => s.id !== shareId);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '删除分享链接失败';
      error.value = msg;
      console.error('[baseStore] deleteShare failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateShare(shareId: string, data: Partial<BaseShare>) {
    loading.value = true;
    try {
      const updated = await shareApiService.updateShare(shareId, data);
      const idx = shares.value.findIndex(s => s.id === shareId);
      if (idx !== -1) {
        shares.value[idx] = updated;
      }
      return updated;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '更新分享链接失败';
      error.value = msg;
      console.error('[baseStore] updateShare failed:', e);
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
      const msg = e instanceof Error ? e.message : '获取分享给我的 Base 失败';
      error.value = msg;
      console.error('[baseStore] fetchSharedWithMe failed:', e);
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
      const msg = e instanceof Error ? e.message : '获取我创建的分享失败';
      error.value = msg;
      console.error('[baseStore] fetchSharedByMe failed:', e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  return {
    currentBaseId,
    currentBase,
    bases,
    loading,
    error,
    sortedBases,
    starredBases,
    // 成员管理和分享相关 state
    members,
    shares,
    sharedWithMe,
    sharedByMe,
    // Base 相关 methods
    fetchBases,
    fetchBase,
    createBase,
    updateBase,
    deleteBase,
    toggleStar,
    setCurrentBase,
    clearError,
    $reset,
    // 成员管理相关 methods
    fetchMembers,
    addMember,
    batchAddMembers,
    updateMemberRole,
    removeMember,
    // 分享管理相关 methods
    fetchShares,
    createShare,
    deleteShare,
    updateShare,
    fetchSharedWithMe,
    fetchSharedByMe
  };
});
