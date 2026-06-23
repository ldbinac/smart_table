/**
 * memberStore 字段权限测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useMemberStore } from '../memberStore';
import type { FieldPermissionResponse } from '@/api/types';

// mock apiClient，避免真实网络请求
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

// mock shareApiService，避免 memberStore 初始化时引入真实服务
vi.mock('@/services/api/shareApiService', () => ({
  shareApiService: {
    getMembers: vi.fn(),
    addMember: vi.fn(),
    batchAddMembers: vi.fn(),
    updateMemberRole: vi.fn(),
    removeMember: vi.fn(),
    getShares: vi.fn(),
    createShare: vi.fn(),
    deleteShare: vi.fn(),
    updateShare: vi.fn(),
    getSharedWithMe: vi.fn(),
    getSharedByMe: vi.fn(),
    accessShare: vi.fn(),
  },
}));

// mock authStore，避免依赖真实认证状态
vi.mock('../authStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: 'user-1' },
    token: 'fake-token',
  })),
}));

// 在导入 store 之后再引入 apiClient，确保 mock 已生效
import { apiClient } from '@/api/client';

describe('memberStore - 字段权限', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('getFieldPermission', () => {
    it('缓存命中时返回缓存值', async () => {
      const store = useMemberStore();
      const mockResponse: FieldPermissionResponse = {
        'field-1': 'read',
        'field-2': 'none',
        'field-3': 'write',
      };
      (apiClient.get as any).mockResolvedValue(mockResponse);

      await store.loadFieldPermissions('table-1');

      expect(store.getFieldPermission('field-1')).toBe('read');
      expect(store.getFieldPermission('field-2')).toBe('none');
      expect(store.getFieldPermission('field-3')).toBe('write');
    });

    it('缓存未命中时返回 write（乐观默认值）', () => {
      const store = useMemberStore();
      // 未调用 loadFieldPermissions，缓存为空
      expect(store.getFieldPermission('non-existent-field')).toBe('write');
    });
  });

  describe('canEditField', () => {
    it('权限为 write 时返回 true', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'write' });

      await store.loadFieldPermissions('table-1');

      expect(store.canEditField('field-1')).toBe(true);
    });

    it('权限为 read 时返回 false', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'read' });

      await store.loadFieldPermissions('table-1');

      expect(store.canEditField('field-1')).toBe(false);
    });

    it('权限为 none 时返回 false', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'none' });

      await store.loadFieldPermissions('table-1');

      expect(store.canEditField('field-1')).toBe(false);
    });

    it('缓存未命中时返回 true（乐观默认 write）', () => {
      const store = useMemberStore();
      expect(store.canEditField('unknown-field')).toBe(true);
    });
  });

  describe('canReadField', () => {
    it('权限为 write 时返回 true', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'write' });

      await store.loadFieldPermissions('table-1');

      expect(store.canReadField('field-1')).toBe(true);
    });

    it('权限为 read 时返回 true', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'read' });

      await store.loadFieldPermissions('table-1');

      expect(store.canReadField('field-1')).toBe(true);
    });

    it('权限为 none 时返回 false', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'none' });

      await store.loadFieldPermissions('table-1');

      expect(store.canReadField('field-1')).toBe(false);
    });

    it('缓存未命中时返回 true（乐观默认 write）', () => {
      const store = useMemberStore();
      expect(store.canReadField('unknown-field')).toBe(true);
    });
  });

  describe('clearFieldPermissions', () => {
    it('清空缓存后 getFieldPermission 返回默认值', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'none' });

      await store.loadFieldPermissions('table-1');
      expect(store.getFieldPermission('field-1')).toBe('none');

      store.clearFieldPermissions();

      expect(store.getFieldPermission('field-1')).toBe('write');
      expect(store.currentPermissionsTableId).toBeNull();
    });
  });

  describe('updateFieldPermission', () => {
    it('更新单个字段权限后立即生效', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'read' });

      await store.loadFieldPermissions('table-1');
      expect(store.getFieldPermission('field-1')).toBe('read');

      store.updateFieldPermission('field-1', 'none');
      expect(store.getFieldPermission('field-1')).toBe('none');
      expect(store.canEditField('field-1')).toBe(false);
      expect(store.canReadField('field-1')).toBe(false);
    });

    it('新增字段权限（缓存中不存在）', () => {
      const store = useMemberStore();

      store.updateFieldPermission('new-field', 'read');
      expect(store.getFieldPermission('new-field')).toBe('read');
      expect(store.canReadField('new-field')).toBe(true);
      expect(store.canEditField('new-field')).toBe(false);
    });
  });

  describe('loadFieldPermissions', () => {
    it('调用正确的 API 端点', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'write' });

      await store.loadFieldPermissions('table-abc');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/tables/table-abc/field-permissions'
      );
    });

    it('加载成功后更新 currentPermissionsTableId', async () => {
      const store = useMemberStore();
      (apiClient.get as any).mockResolvedValue({ 'field-1': 'write' });

      await store.loadFieldPermissions('table-xyz');

      expect(store.currentPermissionsTableId).toBe('table-xyz');
    });

    it('tableId 为空时不发起请求', async () => {
      const store = useMemberStore();

      await store.loadFieldPermissions('');

      expect(apiClient.get).not.toHaveBeenCalled();
    });

    it('请求失败时清空缓存并记录日志', async () => {
      const store = useMemberStore();
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const apiError = new Error('网络错误');
      (apiClient.get as any).mockRejectedValue(apiError);

      await store.loadFieldPermissions('table-err');

      expect(errorSpy).toHaveBeenCalled();
      expect(store.fieldPermissions).toEqual({});
      errorSpy.mockRestore();
    });
  });
});
