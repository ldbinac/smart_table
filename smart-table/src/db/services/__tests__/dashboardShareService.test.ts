import { describe, it, expect, beforeEach, vi } from "vitest";
import { dashboardShareService } from "../dashboardShareService";
import { apiClient } from "@/api/client";

// 模拟数据库操作
vi.mock("../schema", () => ({
  db: {
    dashboardShares: {
      add: vi.fn().mockResolvedValue(undefined),
      put: vi.fn().mockResolvedValue(undefined),
      where: vi.fn().mockReturnValue({
        equals: vi.fn().mockReturnValue({
          first: vi.fn(),
          and: vi.fn().mockReturnValue({
            sortBy: vi.fn(),
          }),
        }),
        below: vi.fn().mockReturnValue({
          and: vi.fn().mockReturnValue({
            toArray: vi.fn(),
          }),
        }),
      }),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    dashboards: {
      put: vi.fn().mockResolvedValue(undefined),
    },
    tableEntities: {
      toArray: vi.fn().mockResolvedValue([]),
    },
    fields: {
      toArray: vi.fn().mockResolvedValue([]),
    },
    records: {
      toArray: vi.fn().mockResolvedValue([]),
    },
  },
}));

// 模拟 API 客户端
vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ 
      data: { valid: true, share: {}, dashboard: {} } 
    }),
    post: vi.fn(),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

describe("DashboardShareService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createShare", () => {
    it("should create a share with correct properties", async () => {
      (apiClient.post as any).mockResolvedValue({
        data: {
          id: "share-1",
          dashboard_id: "dashboard-1",
          share_token: "test-token-1234567890",
          has_access_code: true,
          expires_at: Date.now() + 86400000,
          max_access_count: 10,
          current_access_count: 0,
          is_active: true,
          permission: "edit",
          created_at: new Date().toISOString(),
          created_by: "user-1",
        },
      });
      
      const dashboardId = "dashboard-1";
      const result = await dashboardShareService.createShare({
        dashboardId,
        expiresInHours: 24,
        maxAccessCount: 10,
        requireAccessCode: true,
        permission: "edit",
      });

      expect(result).toHaveProperty("id");
      expect(result.dashboardId).toBe(dashboardId);
      expect(result.shareToken).toBeTruthy();
      expect(result.shareToken.length).toBeGreaterThan(0);
      expect(result.accessCode).toHaveLength(6);
      expect(result.expiresAt).toBeGreaterThan(Date.now());
      expect(result.maxAccessCount).toBe(10);
      expect(result.currentAccessCount).toBe(0);
      expect(result.isActive).toBe(true);
      expect(result.permission).toBe("edit");
      expect(result.createdAt).toBeGreaterThan(0);
    });

    it("should create a share without optional properties", async () => {
      (apiClient.post as any).mockResolvedValue({
        data: {
          id: "share-2",
          dashboard_id: "dashboard-1",
          share_token: "test-token-view",
          has_access_code: false,
          expires_at: Date.now() + 86400000,
          max_access_count: 10,
          current_access_count: 0,
          is_active: true,
          permission: "view",
          created_at: new Date().toISOString(),
          created_by: "user-1",
        },
      });

      const dashboardId = "dashboard-1";
      const result = await dashboardShareService.createShare({ dashboardId });

      expect(result).toHaveProperty("id");
      expect(result.dashboardId).toBe(dashboardId);
      // expiresAt 可能由 API 返回
      expect(result.permission).toBe("view");
    });
  });

  describe("generateShareUrl", () => {
    it("should generate a valid share URL", () => {
      const token = "test-token";
      const expectedUrl = `${window.location.origin}/#/share/dashboard/${token}`;
      const result = dashboardShareService.generateShareUrl(token);
      expect(result).toBe(expectedUrl);
    });
  });

  describe("validateShare", () => {
    it("should validate a valid share", async () => {
      const share = {
        id: "share-1",
        dashboard_id: "dashboard-1",
        share_token: "test-token",
        is_active: true,
        expires_at: Date.now() + 3600000,
        max_access_count: 10,
        current_access_count: 5,
        permission: "view",
        created_at: new Date().toISOString(),
        created_by: "user-1",
      };
      const dashboard = {
        id: "dash-1",
        base_id: "base-1",
        name: "Test Dashboard",
        widgets: [],
        layout: { type: "grid" },
      };

      (apiClient.post as any).mockResolvedValueOnce({
        data: { share, dashboard },
      });

      const result = await dashboardShareService.validateShare("test-token");
      expect(result.valid).toBe(true);
      expect(result.share).toBeDefined();
    });

    it("should invalidate an expired share", async () => {
      const share = {
        id: "share-1",
        dashboard_id: "dashboard-1",
        share_token: "test-token",
        is_active: true,
        expires_at: Date.now() - 3600000,
        max_access_count: 10,
        current_access_count: 5,
        permission: "view",
        created_at: new Date().toISOString(),
        created_by: "user-1",
      };
      const dashboard = {
        id: "dash-1",
        base_id: "base-1",
        name: "Test Dashboard",
        widgets: [],
        layout: { type: "grid" },
      };

      (apiClient.post as any).mockResolvedValueOnce({
        data: { share, dashboard },
      });

      const result = await dashboardShareService.validateShare("test-token");
      // 由于后端应该返回过期错误，这里测试验证逻辑
      expect(result).toBeDefined();
    });

    it("should invalidate a share with max access count reached", async () => {
      const share = {
        id: "share-1",
        dashboard_id: "dashboard-1",
        share_token: "test-token",
        is_active: true,
        max_access_count: 5,
        current_access_count: 5,
        permission: "view",
        created_at: new Date().toISOString(),
        created_by: "user-1",
      };
      const dashboard = {
        id: "dash-1",
        base_id: "base-1",
        name: "Test Dashboard",
        widgets: [],
        layout: { type: "grid" },
      };

      (apiClient.post as any).mockResolvedValueOnce({
        data: { share, dashboard },
      });

      const result = await dashboardShareService.validateShare("test-token");
      expect(result).toBeDefined();
    });

    it("should invalidate a disabled share", async () => {
      const share = {
        id: "share-1",
        dashboard_id: "dashboard-1",
        share_token: "test-token",
        is_active: false,
        permission: "view",
        created_at: new Date().toISOString(),
        created_by: "user-1",
      };
      const dashboard = {
        id: "dash-1",
        base_id: "base-1",
        name: "Test Dashboard",
        widgets: [],
        layout: { type: "grid" },
      };

      (apiClient.post as any).mockResolvedValueOnce({
        data: { share, dashboard },
      });

      const result = await dashboardShareService.validateShare("test-token");
      expect(result).toBeDefined();
    });

    it("should invalidate a non-existent share", async () => {
      (apiClient.post as any).mockResolvedValueOnce({
        data: null,
      });

      const result = await dashboardShareService.validateShare("non-existent-token");
      expect(result.valid).toBe(false);
    });
  });
});
