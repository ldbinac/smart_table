import { apiClient } from '@/api/client';
import type { BaseMember, BaseShare } from '@/stores/baseStore';
import type { Base } from '@/api/types';

export const shareApiService = {
  async getMembers(baseId: string): Promise<BaseMember[]> {
    const data = await apiClient.get<BaseMember[]>(`/bases/${baseId}/members`);
    return (data as unknown as BaseMember[]) || [];
  },

  async addMember(baseId: string, email: string, role: string): Promise<BaseMember> {
    const data = await apiClient.post<BaseMember>(`/bases/${baseId}/members`, { email, role });
    return (data as unknown as BaseMember) || {};
  },

  async batchAddMembers(
    baseId: string,
    members: Array<{ email: string; role: string }>
  ): Promise<{
    success_count: number;
    failed_count: number;
    successful: BaseMember[];
    failed: Array<{ index: number; email: string; error: string }>;
  }> {
    const data = await apiClient.post<{
      success_count: number;
      failed_count: number;
      successful: BaseMember[];
      failed: Array<{ index: number; email: string; error: string }>;
    }>(`/bases/${baseId}/members/batch`, { members });
    return (data as unknown as typeof data) || {};
  },

  async updateMemberRole(baseId: string, userId: string, role: string): Promise<BaseMember> {
    const data = await apiClient.put<BaseMember>(`/bases/${baseId}/members/${userId}`, { role });
    return (data as unknown as BaseMember) || {};
  },

  async removeMember(baseId: string, userId: string): Promise<void> {
    await apiClient.delete(`/bases/${baseId}/members/${userId}`);
  },

  async getShares(baseId: string): Promise<BaseShare[]> {
    const data = await apiClient.get<BaseShare[]>(`/bases/${baseId}/shares`);
    return (data as unknown as BaseShare[]) || [];
  },

  async createShare(
    baseId: string,
    permission: 'view' | 'edit',
    expiresAt?: number
  ): Promise<BaseShare> {
    const data = await apiClient.post<BaseShare>(`/bases/${baseId}/shares`, {
      permission,
      expires_at: expiresAt
    });
    return (data as unknown as BaseShare) || {};
  },

  async deleteShare(shareId: string): Promise<void> {
    await apiClient.delete(`/shares/${shareId}`);
  },

  async updateShare(
    shareId: string,
    updateData: {
      is_active?: boolean;
      permission?: 'view' | 'edit';
      expires_at?: number;
    }
  ): Promise<BaseShare> {
    const data = await apiClient.put<BaseShare>(`/shares/${shareId}`, updateData);
    return (data as unknown as BaseShare) || {};
  },

  async getSharedWithMe(): Promise<Base[]> {
    const data = await apiClient.get<Base[]>('/bases/shared-with-me');
    return (data as unknown as Base[]) || [];
  },

  async getSharedByMe(): Promise<BaseShare[]> {
    const data = await apiClient.get<BaseShare[]>('/bases/shared-by-me');
    return (data as unknown as BaseShare[]) || [];
  },

  async accessShare(shareToken: string): Promise<{
    base: Base;
    permission: 'view' | 'edit';
    share_token: string;
  }> {
    const data = await apiClient.get<{
      base: Base;
      permission: 'view' | 'edit';
      share_token: string;
    }>(`/share/${shareToken}`);
    return (data as unknown as typeof data) || {};
  }
};
